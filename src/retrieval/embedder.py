"""
Singleton wrapper around the sentence-transformers embedding model.
"""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import logging

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading embedding model '%s'…", MODEL_NAME)
        _model = SentenceTransformer(MODEL_NAME)
        logger.info("Embedding model ready.")
    return _model


def embed(texts: list[str] | str) -> list[list[float]]:
    """Embed one or more texts. Always returns a list of float vectors."""
    model = get_model()
    if isinstance(texts, str):
        texts = [texts]
    return model.encode(texts, show_progress_bar=False).tolist()
