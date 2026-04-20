"""
Orchestrates download → parse → chunk and saves the output to JSON.
"""

import json
import logging
from pathlib import Path

from downloader import download_arxiv_papers
from parser import extract_text_from_pdf
from chunker import chunk_pages, Document

logger = logging.getLogger(__name__)


def run_pipeline(
    query: str = "exoplanet detection methods transit radial velocity",
    num_papers: int = 5,
    pdf_dir: Path = Path("data/pdfs"),
    chunks_dir: Path = Path("data/chunks"),
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[Document]:
    """
    Full RAG ingestion pipeline.

    Returns a flat list of Document objects ready for embedding.
    """
    chunks_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=== Step 1: Downloading papers (query='%s') ===", query)
    papers = download_arxiv_papers(query, num_papers, pdf_dir)
    if not papers:
        logger.error("No papers downloaded. Aborting.")
        return []

    all_documents: list[Document] = []

    for paper in papers:
        pdf_path = Path(paper["pdf_path"])
        logger.info("=== Step 2: Parsing %s ===", pdf_path.name)
        pages = extract_text_from_pdf(pdf_path)

        if not pages:
            logger.warning("No text extracted from %s — skipping.", pdf_path.name)
            continue

        logger.info("=== Step 3: Chunking %s (%d pages) ===", pdf_path.name, len(pages))
        docs = chunk_pages(pages, paper, chunk_size, chunk_overlap)
        all_documents.extend(docs)

    logger.info("=== Step 4: Saving output ===")
    output_path = chunks_dir / "chunks.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump([d.to_dict() for d in all_documents], f, ensure_ascii=False, indent=2)

    logger.info(
        "Pipeline complete. %d total chunks saved to %s",
        len(all_documents),
        output_path,
    )
    return all_documents


if __name__ == "__main__":
    _root = Path(__file__).resolve().parent.parent
    _logs_dir = _root / "logs"
    _logs_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(_logs_dir / "pipeline.log", encoding="utf-8"),
        ],
    )
    documents = run_pipeline(
        pdf_dir=_root / "data" / "pdfs",
        chunks_dir=_root / "data" / "chunks",
    )
    print(f"\nReady for embedding: {len(documents)} chunks")
