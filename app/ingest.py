"""Сборка локального индекса шести PDF: `python -m app.ingest`."""
from base64 import b64encode
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
import hashlib
import io
import json
import re
from time import perf_counter

import httpx
import numpy as np
import pymupdf

from . import config
from .manuals import MANUALS
from .search import INDEX_VERSION, _atomic_bytes, _flat, _load_encoder

OCR_VERSION = 1
OCR_DPI = 150
OCR_MAX_OUTPUT = 3000
OCR_BUDGET = 0.65
OCR_WORKERS = 9
# Консервативный резерв по пиковым ставкам Flash и лимитам этого запроса.
OCR_RESERVE = (2048 * 0.30 + OCR_MAX_OUTPUT * 1.20) / 1_000_000
OCR_MARKER = "[OCR DeepSeek Vision — сверяйте числовые нормы с изображением страницы]"
LETTER = re.compile(r"[а-яёa-z]", re.I)
# Физические страницы с подтверждёнными растрами; 144 напечатана боком.
YAMZ236_RASTERS = {144, 271, 272, 273, 277, 278, 280}
OCR_PROMPT = ("Перепиши только видимый русский текст со страницы технического руководства. "
              "Сохрани названия, марки деталей, номера строк и столбцов, числа, знаки допусков, единицы. "
              "Таблицы оформи в Markdown, сохраняй шапку и связь ячеек. Для рисунка — только видимые "
              "подписи, размеры и легенда, без описаний от себя. Неразборчивое пометь [неразборчиво]; "
              "ничего не исправляй и не додумывай. Если текста нет, ответь ровно НЕТ_ТЕКСТА.")


def _json_bytes(data) -> bytes:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _ocr_candidate(page, text, manual_id) -> bool:
    """Отбирает почти пустые страницы и крупные растры без достаточного текстового слоя."""
    letters = len(LETTER.findall(text))
    if letters < 70 or (manual_id == "yamz-236_rk_2014" and page.number + 1 in YAMZ236_RASTERS):
        return True
    if letters >= 350:
        threshold = 0.60
    else:
        threshold = 0.33
    bounds = page.rect * page.derotation_matrix
    return any((pymupdf.Rect(info["bbox"]) & bounds).get_area() >= threshold * bounds.get_area()
               for info in page.get_image_info())


def _cost(usage, hour):
    """Считает оценку по токенам и консервативный итог по пиковым ставкам."""
    cached = usage.get("prompt_cache_hit_tokens", 0)
    uncached = usage.get("prompt_cache_miss_tokens", max(0, usage.get("prompt_tokens", 0) - cached))
    output = usage.get("completion_tokens", 0)
    peak = (0.006 * cached + 0.30 * uncached + 1.20 * output) / 1_000_000
    return peak if hour in {1, 2, 3, 6, 7, 8, 9} else peak / 2, peak


def _recognize(client, image, cache_path):
    """Распознаёт одну страницу и сохраняет результат вместе с usage."""
    hour = datetime.now(timezone.utc).hour
    image_url = "data:image/png;base64," + b64encode(image).decode("ascii")
    try:
        response = client.post(f"{config.LLM_BASE_URL.rstrip('/')}/chat/completions", json={
            "model": config.LLM_MODEL, "temperature": 0, "max_tokens": OCR_MAX_OUTPUT,
            "thinking": {"type": "disabled"},
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": OCR_PROMPT},
                {"type": "image_url", "image_url": {"url": image_url, "detail": "original"}},
            ]}],
        })
        response.raise_for_status()
        result = response.json()
        choice = result["choices"][0]
        text = (choice["message"]["content"] or "").strip()
        mode = choice.get("finish_reason")
        status = ("partial" if text and mode == "length" else "ok" if text and mode == "stop" else "empty")
        record = {"text": "" if text == "НЕТ_ТЕКСТА" else text, "status": status,
                  "usage": result.get("usage") or {}, "hour_utc": hour,
                  "model": result.get("model"), "finish_reason": mode}
        if status in {"ok", "partial"}:
            _atomic_bytes(cache_path, _json_bytes(record))
        return record
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        status = f"http_{exc.response.status_code}" if isinstance(exc, httpx.HTTPStatusError) else type(exc).__name__
        return {"status": status, "text": "", "usage": {}, "hour_utc": hour}


def _scan(pool, client):
    """Извлекает текст и ставит OCR-кандидатов в очередь с лимитом расходов."""
    rows, documents, pending = [], {}, {}
    stats = {"selected": 0, "submitted": 0, "cached": 0, "skipped": 0, "statuses": {},
             "cost_estimate_usd": 0.0, "cost_peak_usd": 0.0, "cost_upper_bound_usd": 0.0,
             "cached_cost_estimate_usd": 0.0}

    def collect(timeout=None):
        if not pending:
            return
        finished, _ = wait(pending, timeout=timeout, return_when=FIRST_COMPLETED)
        for done in finished:
            record = done.result()
            _join_ocr(pending.pop(done), record, stats)
            estimate, peak = _cost(record["usage"], record["hour_utc"])
            stats["cost_estimate_usd"] += estimate
            stats["cost_peak_usd"] += peak
            stats["cost_upper_bound_usd"] += peak if record["usage"] else OCR_RESERVE
    # Модель и версия распознавания входят в ключ; смена PDF не использует старый OCR.
    ocr_key = hashlib.sha256(f"{OCR_VERSION}:{config.LLM_BASE_URL}:{config.LLM_MODEL}".encode()).hexdigest()[:12]
    for manual in MANUALS:
        path = config.MANUALS_DIR / manual.filename
        with path.open("rb") as handle:
            sha = hashlib.file_digest(handle, "sha256").hexdigest()
        with pymupdf.open(path) as pdf:
            documents[manual.id] = {"pages": len(pdf), "sha256": sha}
            for page in pdf:
                text = page.get_text(sort=True).strip()
                n = page.number + 1
                row = {"manual_id": manual.id, "page": n, "text": text}
                rows.append(row)
                if not _ocr_candidate(page, text, manual.id):
                    continue
                stats["selected"] += 1
                cache = config.INDEX_DIR / "ocr" / manual.id / f"{sha[:20]}-{ocr_key}" / f"{n}.json"
                if cache.is_file():
                    record = json.loads(cache.read_text(encoding="utf-8"))
                    stats["cached"] += 1
                    _join_ocr(row, record, stats)
                    stats["cached_cost_estimate_usd"] += _cost(record["usage"], record["hour_utc"])[0]
                    continue
                if client is None:
                    stats["skipped"] += 1
                    continue
                collect(timeout=0)
                while pending and (len(pending) >= 2 * OCR_WORKERS or
                                   stats["cost_upper_bound_usd"] + (len(pending) + 1) * OCR_RESERVE > OCR_BUDGET):
                    collect()
                if stats["cost_upper_bound_usd"] + (len(pending) + 1) * OCR_RESERVE > OCR_BUDGET:
                    stats["skipped"] += 1
                    continue
                if manual.id == "yamz-236_rk_2014" and n == 144:
                    matrix = pymupdf.Matrix(OCR_DPI / 72, OCR_DPI / 72).prerotate(90)
                    pix = page.get_pixmap(matrix=matrix, alpha=False)
                else:
                    pix = page.get_pixmap(dpi=OCR_DPI, alpha=False)
                job = pool.submit(_recognize, client, pix.tobytes("png"), cache)
                pending[job] = row
                stats["submitted"] += 1
            print(f"{manual.id}: {len(pdf)} стр.", flush=True)
    while pending:
        collect()
    return rows, documents, stats


def _join_ocr(row, record, stats):
    status = record["status"]
    stats["statuses"][status] = stats["statuses"].get(status, 0) + 1
    if record["text"]:
        mark = OCR_MARKER if status == "ok" else f"{OCR_MARKER} [неполное распознавание]"
        row["text"] = f"{row['text']}\n\n{mark}\n{record['text']}".strip()
        stats["with_ocr_text"] = stats.get("with_ocr_text", 0) + 1


def _embed(encoder, rows):
    """Усредняет нормированные окна E5 в один вектор на PDF-страницу."""
    passages, spans = [], []
    for row in rows:
        words = _flat(row["text"].replace(OCR_MARKER, "")).split()
        begin = len(passages)
        for i in range(0, max(1, len(words) - 30), 175):
            passages.append("passage: " + " ".join(words[i:i + 205]))
        spans.append((begin, len(passages)))
    encoded = encoder.encode(passages, batch_size=24, normalize_embeddings=True, show_progress_bar=False)
    vectors = np.stack([np.mean(encoded[a:b], axis=0) for a, b in spans]).astype(np.float32)
    vectors /= np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12)
    return vectors


def main() -> None:
    """Собирает индекс и печатает измерения OCR и сборки."""
    start = perf_counter()
    missing = [m.filename for m in MANUALS if not (config.MANUALS_DIR / m.filename).is_file()]
    if missing:
        raise FileNotFoundError(f"Не найдены руководства в {config.MANUALS_DIR}: {', '.join(missing)}")
    with ThreadPoolExecutor(max_workers=OCR_WORKERS) as pool, httpx.Client(
        headers={"Authorization": f"Bearer {config.LLM_API_KEY}"}, timeout=55.0, trust_env=False,
    ) as http:
        rows, documents, stats = _scan(pool, http if config.LLM_API_KEY else None)
    print(json.dumps({"ocr_seconds": round(perf_counter() - start, 2), **stats}), flush=True)
    vectors = _embed(_load_encoder(), rows)
    meta = {"version": INDEX_VERSION, "embed_model": config.EMBED_MODEL, "documents": documents, "pages": rows}
    output = io.BytesIO()
    np.savez(output, metadata=json.dumps(meta, ensure_ascii=False), vectors=vectors)
    _atomic_bytes(config.INDEX_DIR / "pages.npz", output.getbuffer())
    report = {"documents": documents, "pages": len(rows), "embedding_shape": list(vectors.shape),
              "build_seconds": round(perf_counter() - start, 2), "ocr": stats}
    _atomic_bytes(config.INDEX_DIR / "build-report.json", _json_bytes(report))
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
