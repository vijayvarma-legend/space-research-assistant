"""
Ingestion pipeline: download → parse → chunk → save processed JSON.

Run directly:  python src/pipeline.py
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ingestion.loader import download_arxiv_papers, extract_text_from_pdf
from ingestion.processor import chunk_pages, Document

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[1]


def run_pipeline(
    query: str = "Space Sustainability & Debris Mitigation",
    num_papers: int = 5,
    raw_dir: Path = _ROOT / "data" / "raw",
    processed_dir: Path = _ROOT / "data" / "processed",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[Document]:
    processed_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=== Step 1: Downloading (query='%s') ===", query)
    papers = download_arxiv_papers(query, num_papers, raw_dir)
    if not papers:
        logger.error("No papers downloaded. Aborting.")
        return []

    all_docs: list[Document] = []

    for paper in papers:
        pdf_path = Path(paper["pdf_path"])

        logger.info("=== Step 2: Parsing %s ===", pdf_path.name)
        pages = extract_text_from_pdf(pdf_path)
        if not pages:
            logger.warning("No text extracted from %s — skipping.", pdf_path.name)
            continue

        logger.info("=== Step 3: Chunking %s (%d pages) ===", pdf_path.name, len(pages))
        docs = chunk_pages(pages, paper, chunk_size, chunk_overlap)
        all_docs.extend(docs)

    slug = "_".join(query.lower().split())[:60]
    out_path = processed_dir / f"chunks_{slug}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump([d.to_dict() for d in all_docs], f, ensure_ascii=False, indent=2)

    logger.info("Pipeline complete. %d chunks → %s", len(all_docs), out_path)
    return all_docs


if __name__ == "__main__":
    (_ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(_ROOT / "logs" / "pipeline.log", encoding="utf-8"),
        ],
    )
    docs = run_pipeline()
    print(f"\nReady for embedding: {len(docs)} chunks")
