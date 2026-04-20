"""
Downloads PDFs from arxiv for a given search query.
"""

import logging
import time
from pathlib import Path

import arxiv
import requests

logger = logging.getLogger(__name__)


def download_arxiv_papers(
    query: str,
    num_papers: int,
    output_dir: Path,
) -> list[dict]:
    """
    Search arxiv and download PDFs.

    Returns a list of metadata dicts for successfully downloaded papers.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    client = arxiv.Client(page_size=num_papers, delay_seconds=3)
    search = arxiv.Search(
        query=query,
        max_results=num_papers,
        sort_by=arxiv.SortCriterion.Relevance,
    )

    downloaded = []
    results = list(client.results(search))

    if not results:
        logger.warning("No arxiv results found for query: %s", query)
        return downloaded

    for paper in results:
        arxiv_id = paper.entry_id.split("/")[-1]
        filename = f"{arxiv_id}.pdf"
        dest = output_dir / filename

        if dest.exists():
            logger.info("Already downloaded: %s", filename)
            downloaded.append(_build_meta(paper, dest))
            continue

        try:
            pdf_url = paper.pdf_url
            logger.info("Downloading %s — %s", arxiv_id, paper.title)
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()

            dest.write_bytes(response.content)
            downloaded.append(_build_meta(paper, dest))
            logger.info("Saved: %s", dest)
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
