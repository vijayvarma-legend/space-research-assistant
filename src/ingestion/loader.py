"""
Downloads PDFs from arxiv and extracts clean text page-by-page.

Multi-column handling: blocks are sorted by quantised y-band then x0
so left-column text is never interleaved with right-column text.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import arxiv
import fitz  # PyMuPDF
import requests

logger = logging.getLogger(__name__)

_BAND_TOLERANCE = 5  # vertical tolerance (pts) for grouping blocks into a row


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download_arxiv_papers(query: str, num_papers: int, output_dir: Path) -> list[dict]:
    """Search arxiv and download PDFs. Returns metadata for each success."""
    output_dir.mkdir(parents=True, exist_ok=True)

    client = arxiv.Client(page_size=num_papers, delay_seconds=3)
    search = arxiv.Search(
        query=query,
        max_results=num_papers,
        sort_by=arxiv.SortCriterion.Relevance,
    )

    downloaded = []
    for paper in client.results(search):
        arxiv_id = paper.entry_id.split("/")[-1]
        dest = output_dir / f"{arxiv_id}.pdf"

        if dest.exists():
            logger.info("Already downloaded: %s", dest.name)
            downloaded.append(_build_meta(paper, dest))
            continue

        try:
            logger.info("Downloading %s — %s", arxiv_id, paper.title)
            resp = requests.get(paper.pdf_url, timeout=30)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            downloaded.append(_build_meta(paper, dest))
            time.sleep(1)
        except requests.RequestException as exc:
            logger.error("Failed to download %s: %s", arxiv_id, exc)

    return downloaded


def _build_meta(paper: arxiv.Result, path: Path) -> dict:
    return {
        "arxiv_id": paper.entry_id.split("/")[-1],
        "title": paper.title,
        "authors": [str(a) for a in paper.authors],
        "published": paper.published.isoformat() if paper.published else None,
        "summary": paper.summary,
        "pdf_path": str(path),
        "filename": path.name,
    }


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: Path) -> list[dict]:
    """
    Extract text page-by-page. Returns [{page_num, text}, ...].
    Skips unreadable pages rather than raising.
    """
    pages = []
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:
        logger.error("Cannot open %s: %s", pdf_path.name, exc)
        return pages

    for idx in range(len(doc)):
        try:
            text = _ordered_text(doc[idx])
            if text.strip():
                pages.append({"page_num": idx + 1, "text": text})
        except Exception as exc:
            logger.warning("Skipping page %d of %s: %s", idx + 1, pdf_path.name, exc)

    doc.close()
    return pages


def _ordered_text(page: fitz.Page) -> str:
    blocks = [b for b in page.get_text("blocks") if b[6] == 0]
    blocks.sort(key=lambda b: (round(b[1] / _BAND_TOLERANCE), b[0]))
    return "\n".join(b[4].strip() for b in blocks if b[4].strip())
