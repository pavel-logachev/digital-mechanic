"""Гибридный поиск по физическим страницам руководств."""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import json
import logging
import math
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from threading import Lock, local
from time import monotonic
from typing import TypedDict

import httpx
import numpy as np
import pymupdf
from rank_bm25 import BM25Okapi

from . import config
from .manuals import BY_ID, MANUALS, manuals_for_engine

INDEX_VERSION = 1
POOL = ThreadPoolExecutor(max_workers=20, thread_name_prefix="jev")
JEV_URL = "https://openrouter.ai/api/alpha/decisions"
JEV_TIMEOUT = 4.0
TOP_N = int(config.env("RERANK_TOP_N", "100"))  # сколько кандидатов отдаём Jev
BATCH_SIZE = 10
RRF_K = 60
LOG = logging.getLogger(__name__)
WORD = re.compile(r"[a-zа-я]+|\d+(?:[.,]\d+)*")
WRAPPED = re.compile(r"(?<=[а-яёА-ЯЁa-zA-Z])[-\u00ad][ \t]*\r?\n[ \t]*(?=[а-яёa-z])")
ENDING = re.compile(r"(?:иями|ями|ами|ого|ому|ыми|ими|ыми|ую|юю|ых|их|ой|ый|ий|ая|яя|ое|ее|ом|ем|ов|ев|ам|ям|ах|ях|ия|ие|ии|ию|а|я|о|е|ы|и|у|ю|ь)$")


class Hit(TypedDict):
    """Страница с оценкой и цитируемым текстом."""

    manual_id: str
    page: int
    score: float
    text: str
    snippet: str


def _flat(text: str) -> str:
    return " ".join(WRAPPED.sub("", text).split())


def _tokens(text: str) -> list[str]:
    words = WORD.findall(WRAPPED.sub("", text).lower().replace("ё", "е"))
    return [ENDING.sub("", w) if len(w) >= 5 and "а" <= w[0] <= "я" else w for w in words]


def _load_encoder():
    import torch
    from sentence_transformers import SentenceTransformer

    torch.set_num_threads(min(8, os.cpu_count() or 1))
    return SentenceTransformer(config.EMBED_MODEL, device="cpu")


def _atomic_bytes(path: Path, data: bytes | memoryview) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temp = Path(handle.name)
    try:
        temp.write_bytes(data)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def _passage(text: str, terms: set[str], limit: int) -> str:
    """Берёт целую короткую страницу или наиболее релевантные окна текста."""
    flat = _flat(text)
    if len(flat) <= limit:
        return flat
    if limit < 600:
        starts = range(0, len(flat), limit // 2)
        start = max(starts, key=lambda i: len(terms.intersection(_tokens(flat[i:i + limit]))))
        if start == 0:
            return flat[:limit].rsplit(" ", 1)[0] + "…"
        end = min(start + limit, len(flat))
        start = flat.rfind(" ", 0, start) + 1
        return "… " + flat[start:end].rsplit(" ", 1)[0] + "…"
    size = limit // 3 - 50
    starts = list(range(0, len(flat), size))
    relevant = sorted(starts[1:], key=lambda i: -len(terms.intersection(_tokens(flat[i:i + size]))))[:2]
    return " … ".join(flat[i:i + size] for i in sorted([0, *relevant]))


def _jev_batch(client: httpx.Client, model: str, query: str, engine: str,
               alternatives: list[str], batch: list[tuple[int, str]], deadline: float):
    remaining = deadline - monotonic()
    if remaining < 0.05:
        raise TimeoutError
    state = {"query": query[:1200], "engine": engine,
             "rewrites": [q[:600] for q in alternatives[:4]],
             "pages": {str(idx): text for idx, text in batch}}
    questions = {
        str(idx): {
            "type": "noul",
            "instructions": (f"Does pages['{idx}'] contain direct evidence needed to answer query "
                             "for engine? Use rewrites only to clarify the query. Prefer the actual "
                             "specification, cause or procedure over a general mention or contents page."),
            "criteria": {"true": "Directly answers or contains essential evidence",
                         "false": "Tangential, about a different component or no answer"},
        }
        for idx, _ in batch
    }
    response = client.post(JEV_URL, json={"model": model, "state": state, "questions": questions},
                           timeout=httpx.Timeout(remaining))
    response.raise_for_status()
    payload = response.json()
    usage = payload.get("usage") or {}
    cost = usage.get("cost")
    try:
        scores = {idx: float(payload["answers"][str(idx)]["noul"]) for idx, _ in batch}
        if not all(0 <= score <= 1 and math.isfinite(score) for score in scores.values()):
            raise ValueError("Jev score")
    except (ValueError, KeyError, TypeError, OverflowError):
        scores = None
    return scores, float(cost) if isinstance(cost, (float, int)) else None


class Searcher:
    """Индекс страниц, изолированный по модели двигателя."""

    def __init__(self, rows, vectors, encoder):
        self._rows = rows
        self._encoder = encoder
        self._encoder_lock = Lock()
        self._client_lock = Lock()
        self._client = None
        self._local = local()
        self._by_page = {(row["manual_id"], row["page"]): row["text"] for row in rows}
        tokens = [_tokens(row["text"]) for row in rows]
        self._shards = {}
        for engine in {e for m in MANUALS for e in m.engines}:
            allowed = {manual.id for manual in manuals_for_engine(engine)}
            ids = np.array([i for i, row in enumerate(rows) if row["manual_id"] in allowed and tokens[i]],
                           dtype=np.intp)
            if len(ids):
                self._shards[engine] = (ids, BM25Okapi([tokens[i] for i in ids]), vectors[ids])

    @classmethod
    def load(cls):
        """Загружает индекс из `INDEX_DIR` и локальный E5."""
        try:
            with np.load(config.INDEX_DIR / "pages.npz", allow_pickle=False) as data:
                meta = json.loads(data["metadata"].item())
                vectors = data["vectors"]
        except FileNotFoundError as exc:
            raise FileNotFoundError("Индекс не собран: python -m app.ingest") from exc
        if meta["version"] != INDEX_VERSION or meta["embed_model"] != config.EMBED_MODEL:
            raise ValueError("Версия индекса или модель изменились: python -m app.ingest")
        if vectors.ndim != 2 or len(vectors) != len(meta["pages"]):
            raise ValueError("Индекс страниц повреждён: python -m app.ingest")
        return cls(meta["pages"], vectors, _load_encoder())

    @property
    def rerank_stats(self) -> dict:
        """Состояние Jev для последнего запроса в текущем потоке."""
        return getattr(self._local, "rerank", {}).copy()

    def _rerank(self, queries, engine, ranked, terms):
        if not config.RERANK_ENABLED:
            return ranked
        if not config.OPENROUTER_API_KEY:
            self._local.rerank["status"] = "no_key"
            return ranked
        with self._client_lock:
            if self._client is None:
                try:
                    self._client = httpx.Client(proxy=config.OPENROUTER_PROXY or None,
                                                headers={"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"},
                                                limits=httpx.Limits(max_connections=20, max_keepalive_connections=20),
                                                trust_env=False)
                except (ValueError, ImportError) as exc:
                    self._local.rerank["status"] = "client_error"
                    LOG.warning("Jev: %s; используется RRF", type(exc).__name__)
                    return ranked
        top = ranked[:TOP_N]
        pages = [(i, _passage(self._rows[i]["text"], terms, 3200)) for i, _ in top]
        deadline = monotonic() + JEV_TIMEOUT
        pending = {POOL.submit(_jev_batch, self._client, config.JEV_MODEL, queries[0], engine,
                               queries[1:], pages[offset:offset + BATCH_SIZE], deadline)
                   for offset in range(0, len(pages), BATCH_SIZE)}
        stats = self._local.rerank
        stats.update(requests=len(pending), status="applied")
        scores = {}
        while pending:
            done, pending = wait(pending, timeout=max(0, deadline - monotonic()),
                                 return_when=FIRST_COMPLETED)
            if not done:
                stats["status"] = "timeout"
                stats["unknown_cost_requests"] += sum(not future.cancel() for future in pending)
                break
            for future in done:
                try:
                    result, cost = future.result()
                    if cost is None:
                        stats["unknown_cost_requests"] += 1
                    else:
                        stats["cost_usd"] += cost
                    if result is None:
                        stats["status"] = "invalid_response"
                    else:
                        scores.update(result)
                except (httpx.HTTPError, TimeoutError, ValueError, KeyError, TypeError) as exc:
                    stats["status"] = (f"http_{exc.response.status_code}"
                                       if isinstance(exc, httpx.HTTPStatusError) else type(exc).__name__)
                    stats["unknown_cost_requests"] += 1
        if len(scores) != len(top):
            LOG.warning("Jev: %s; используется RRF", stats["status"])
            return ranked
        return sorted(((idx, scores[idx]) for idx, _ in top), key=lambda pair: -pair[1]) + ranked[len(top):]

    def search(self, query: str, engine_model: str, k: int = 5,
               rewrites: list[str] | None = None) -> list[Hit]:
        """Объединяет BM25 и E5 по RRF, опционально уточняет выдачу Jev."""
        self._local.rerank = {"status": "off", "requests": 0, "cost_usd": 0.0, "unknown_cost_requests": 0}
        shard = self._shards.get(engine_model)
        queries = list(dict.fromkeys(s for q in (query, *(rewrites or [])) if (s := q.strip())))
        if shard is None or k <= 0 or not queries:
            return []
        ids, bm25, vectors = shard
        with self._encoder_lock:
            dense = self._encoder.encode([f"query: {_flat(q)}" for q in queries], normalize_embeddings=True,
                                         show_progress_bar=False)
        scores = np.zeros(len(ids))
        depth = max(TOP_N, k)
        terms = set()
        for q, vector in zip(queries, dense):
            words = list(dict.fromkeys(_tokens(q)))
            terms.update(words)
            lexical = bm25.get_scores(words)
            semantic = vectors @ vector
            rankings = (np.argsort(-lexical, kind="stable"), np.argsort(-semantic, kind="stable"))
            for j, order in enumerate(rankings):
                order = order[:depth]
                if j == 0:
                    order = order[lexical[order] > 0]
                scores[order] += 1 / (RRF_K + np.arange(1, len(order) + 1))
        ranked = [(int(ids[i]), float(scores[i])) for i in np.argsort(-scores, kind="stable") if scores[i] > 0]
        ranked = self._rerank(queries, engine_model, ranked, terms)
        return [Hit(manual_id=row["manual_id"], page=row["page"], score=score, text=row["text"],
                    snippet=_passage(row["text"], terms, 420))
                for idx, score in ranked[:k] if (row := self._rows[idx])]

    def page_text(self, manual_id: str, page: int) -> str:
        """Возвращает текст физической страницы PDF или `KeyError`."""
        if type(page) is not int:
            raise KeyError((manual_id, page))
        return self._by_page[manual_id, page]

    def page_png(self, manual_id: str, page: int) -> Path:
        """Рендерит страницу в PNG при 120 dpi и сохраняет в кэше."""
        if type(page) is not int or (manual_id, page) not in self._by_page or manual_id not in BY_ID:
            raise KeyError((manual_id, page))
        source = config.MANUALS_DIR / BY_ID[manual_id].filename
        target = config.PAGES_DIR / manual_id / f"{page}.png"
        if not target.is_file() or target.stat().st_mtime_ns < source.stat().st_mtime_ns:
            with pymupdf.open(source) as doc:
                data = doc.load_page(page - 1).get_pixmap(dpi=120, alpha=False).tobytes("png")
            _atomic_bytes(target, data)
        return target
