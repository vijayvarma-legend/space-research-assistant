"""
Extracts clean text from PDFs using PyMuPDF.

Multi-column handling: pages are read via 'blocks' sorted top-to-bottom,
left-to-right within each horizontal band so columns are read in the
correct reading order rather than interleaving.
"""

import logging
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Vertical tolerance (points) for grouping text blocks into the same row
_BAND_TOLERANCE = 5


def extract_text_from_pdf(pdf_path: Path) -> list[dict]:
    """
    Extract text page-by-page from a PDF.

    Returns a list of {page_num, text} dicts.
    Skips pages that yield no readable text.
    """
    pages = []
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:
        logger.error("Cannot open %s: %s", pdf_path.name, exc)
        return pages

    for page_index in range(len(doc)):
        try:
            page = doc[page_index]
            text = _extract_ordered_text(page)
            if text.strip():
                pages.append({"page_num": page_index + 1, "text": text})
        except Exception as exc:
            logger.warning(
                "Skipping page %d of %s: %s", page_index + 1, pdf_path.name, exc
            )

    doc.close()
    return pages


def _extract_ordered_text(page: fitz.Page) -> str:
    """
    Read text blocks in natural reading order (top→bottom, left→right).

    fitz.Page.get_text('blocks') returns:
      (x0, y0, x1, y1, text, block_no, block_type)
    We sort by y0 band first, then x0, to correctly handle two-column PDFs.
    """
    raw_blocks = page.get_text("blocks")
    # Keep only text blocks (type 0); skip images (type 1)
    text_blocks = [b for b in raw_blocks if b[6] == 0]

    # Sort: primary key = quantised y0 band, secondary key = x0
    def sort_key(b):
        y_band = round(b[1] / _BAND_TOLERANCE)
        return (y_band, b[0])

    text_blocks.sort(key=sort_key)

    return "\n".join(b[4].strip() for b in text_blocks if b[4].strip())
