"""Контракт поиска и физической нумерации страниц."""
from pathlib import Path

import numpy as np
import pymupdf
import pytest


def test_search_filters_engine_before_ranking_and_keeps_page(tmp_path, monkeypatch):
    from app import config
    from app.search import Searcher

    monkeypatch.setattr(config, "MANUALS_DIR", tmp_path)
    monkeypatch.setattr(config, "PAGES_DIR", tmp_path / "pages")
    monkeypatch.setattr(config, "RERANK_ENABLED", False)
    doc_id = "yamz-236_re_2010"
    with pymupdf.open() as doc:
        doc.new_page().insert_text((50, 50), "Oil pump")
        doc.save(tmp_path / f"{doc_id}.pdf")

    class Encoder:
        def encode(self, texts, **kwargs):
            assert texts == ["query: насос", "query: давление"]
            return np.ones((2, 2), dtype=np.float32)

    rows = [
        {"manual_id": "yamz-536_re_2016", "page": 1, "text": "насос давление"},
        {"manual_id": doc_id, "page": 1, "text": "Масляный насос"},
    ]
    searcher = Searcher(rows, np.ones((2, 2), dtype=np.float32), Encoder())
    hit, = searcher.search("насос", "ЯМЗ-236М2", rewrites=[" давление ", "насос"])
    assert set(hit) == {"manual_id", "page", "text", "snippet", "score"}
    assert (hit["manual_id"], hit["page"], hit["text"]) == (doc_id, 1, "Масляный насос")
    assert searcher.search("насос", "ЯМЗ-236") == []
    assert searcher.page_text(doc_id, 1) == hit["text"]
    png = searcher.page_png(doc_id, 1)
    assert png == Path(tmp_path / "pages" / doc_id / "1.png")
    assert pymupdf.Pixmap(str(png)).width > 900
    assert searcher.page_png(doc_id, 1) == png
    with pytest.raises(KeyError):
        searcher.page_png("../other", 1)
    with pytest.raises(KeyError):
        searcher.page_png(doc_id, True)


def test_metrics_count_first_matching_page_only():
    from eval.retrieval_eval import summarize

    result = summarize([1, 3, 6, None], [0.001, 0.003, 0.004, 0.006])
    assert result["hits"] == {"1": 1, "3": 2, "5": 2}
    assert result["mrr"] == pytest.approx(0.375)
    assert result["p50_ms"] == pytest.approx(3.5)


def test_rerank_uses_rrf_when_a_batch_errors(monkeypatch):
    import httpx

    from app import config, search

    class Encoder:
        def encode(self, texts, **kwargs):
            return np.array([[1.0, 0]])

    monkeypatch.setattr(config, "RERANK_ENABLED", True)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-only")
    monkeypatch.setattr(search, "BATCH_SIZE", 1)
    rows = [{"manual_id": "yamz-236_re_2010", "page": i, "text": t}
            for i, t in enumerate(["насос", "ремонт"], 1)]
    s = search.Searcher(rows, np.array([[1.0, 0], [0, 1.0]]), Encoder())

    def decide(request):
        import json
        idx, = json.loads(request.content)["questions"]
        if idx == "0":
            return httpx.Response(503)
        return httpx.Response(200, json={"answers": {idx: {"noul": 0.99}}, "usage": {"cost": 0.0001}})

    with httpx.Client(transport=httpx.MockTransport(decide)) as client:
        s._client = client
        results = s.search("насос", "ЯМЗ-236М2")
    assert [x["page"] for x in results] == [1, 2]
    assert s.rerank_stats["status"] == "http_503"
    assert s.rerank_stats["cost_usd"] == pytest.approx(0.0001)
