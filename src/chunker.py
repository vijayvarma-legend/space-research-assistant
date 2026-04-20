"""
Splits page text into overlapping chunks and attaches source metadata.
"""

import logging
from dataclasses import dataclass, asdict

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


@dataclass
class Document:
    content: str
    metadata: dict

    def to_dict(self) -> dict:
        return asdict(self)


def chunk_pages(
    pages: list[dict],
    paper_meta: dict,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[Document]:
    """
    Split page texts into chunks.

    Each Document carries:
      - source_filename  : PDF filename
      - arxiv_id         : arxiv identifier
      - title            : paper title
      - page_num         : originating page number
      - chunk_index      : position of this chunk within the page
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    documents: list[Document] = []

    for page in pages:
        page_num = page["page_num"]
        text = page["text"]

        if not text.strip():
            continue

        try:
            chunks = splitter.split_text(text)
        except Exception as exc:
            logger.warning(
                "Chunking failed for page %d of %s: %s",
                page_num,
                paper_meta.get("filename", "unknown"),
                exc,
            )
            continue

        for idx, chunk in enumerate(chunks):
            doc = Document(
                content=chunk,
                metadata={
                    "source_filename": paper_meta.get("filename", ""),
                    "arxiv_id": paper_meta.get("arxiv_id", ""),
                    "title": paper_meta.get("title", ""),
                    "authors": paper_meta.get("authors", []),
                    "published": paper_meta.get("published", ""),
                    "page_num": page_num,
                    "chunk_index": idx,
                },
            )
            documents.append(doc)

    logger.info(
        "Produced %d chunks from %d pages (%s)",
        len(documents),
        len(pages),
        paper_meta.get("filename", ""),
    )
    return documents
