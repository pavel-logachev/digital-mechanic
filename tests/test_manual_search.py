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
