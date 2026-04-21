"""
Unit tests for chunking and retrieval.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingestion.processor import chunk_pages, Document


def test_chunk_pages_basic():
    pages = [{"page_num": 1, "text": "word " * 300}]
    meta = {"filename": "test.pdf", "arxiv_id": "0000.0000", "title": "Test", "authors": [], "published": ""}
    docs = chunk_pages(pages, meta, chunk_size=100, chunk_overlap=20)
    assert len(docs) > 1
    for doc in docs:
        assert isinstance(doc, Document)
        assert doc.metadata["source_filename"] == "test.pdf"
        assert doc.metadata["page_num"] == 1


def test_chunk_pages_empty_text():
    pages = [{"page_num": 1, "text": "   "}]
    meta = {"filename": "empty.pdf", "arxiv_id": "x", "title": "", "authors": [], "published": ""}
    docs = chunk_pages(pages, meta)
    assert docs == []


def test_chunk_metadata_fields():
    pages = [{"page_num": 3, "text": "Some content about exoplanets " * 50}]
    meta = {"filename": "paper.pdf", "arxiv_id": "1234.5678", "title": "Exoplanets", "authors": ["A", "B"], "published": "2024-01-01"}
    docs = chunk_pages(pages, meta, chunk_size=200, chunk_overlap=40)
    for i, doc in enumerate(docs):
        assert doc.metadata["chunk_index"] == i
        assert doc.metadata["arxiv_id"] == "1234.5678"
