"""
Embeds chunked documents and stores/queries them in a local ChromaDB database.

Expected input: list of Document objects (or dicts with 'content' + 'metadata')
produced by chunker.py.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from chunker import Document

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_DB_DIR = Path(__file__).resolve().parent.parent / "space_research_db"
_COLLECTION_NAME = "space_papers"
_MODEL_NAME = "all-MiniLM-L6-v2"
_BATCH_SIZE = 64  # embed this many chunks at once to avoid OOM on large corpora


# ---------------------------------------------------------------------------
# Singletons (initialised lazily so imports stay cheap)
# ---------------------------------------------------------------------------
_model: SentenceTransformer | None = None
_client: chromadb.PersistentClient | None = None
_collection: chromadb.Collection | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading embedding model '%s'…", _MODEL_NAME)
        _model = SentenceTransformer(_MODEL_NAME)
        logger.info("Model loaded.")
    return _model


def _get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is None:
        # Silence the posthog version-mismatch error that leaks through
        # even when anonymized_telemetry=False.
        logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

        _DB_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(_DB_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "ChromaDB collection '%s' ready at %s (existing docs: %d)",
            _COLLECTION_NAME,
            _DB_DIR,
            _collection.count(),
        )
    return _collection


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_papers_to_db(chunks: list[Union[Document, dict]]) -> int:
    """
    Embed and upsert a list of chunks into the 'space_papers' collection.

    Accepts either Document objects (from chunker.py) or plain dicts with
    'content' and 'metadata' keys.

    Returns the number of chunks upserted.
    """
    if not chunks:
        logger.warning("add_papers_to_db called with empty chunk list.")
        return 0

    model = _get_model()
    collection = _get_collection()

    # Normalise to dicts
    records = [c.to_dict() if isinstance(c, Document) else c for c in chunks]

    texts = [r["content"] for r in records]
    ids = [_make_id(r) for r in records]
    metadatas = [_sanitise_metadata(r["metadata"]) for r in records]

    total = 0
    for start in range(0, len(texts), _BATCH_SIZE):
        batch_texts = texts[start : start + _BATCH_SIZE]
        batch_ids = ids[start : start + _BATCH_SIZE]
        batch_meta = metadatas[start : start + _BATCH_SIZE]

        embeddings = model.encode(batch_texts, show_progress_bar=False).tolist()

        collection.upsert(
            ids=batch_ids,
            documents=batch_texts,
            embeddings=embeddings,
            metadatas=batch_meta,
        )
        total += len(batch_texts)
        logger.info("Upserted batch %d–%d (%d total so far)", start, start + len(batch_texts) - 1, total)

    logger.info("Done. %d chunks in collection (collection total: %d).", total, collection.count())
    return total


def query_db(user_query: str, n_results: int = 3) -> list[dict]:
    """
    Embed the query and return the top-n most relevant chunks.

    Each result dict contains:
      - text          : the matched chunk text
      - source        : source PDF filename
      - page_num      : originating page number
      - title         : paper title
      - distance      : cosine distance (lower = more similar)
      - (all other stored metadata fields)
    """
    if not user_query.strip():
        raise ValueError("user_query must not be empty.")

    model = _get_model()
    collection = _get_collection()

    if collection.count() == 0:
        logger.warning("Collection is empty — run add_papers_to_db first.")
        return []

    query_embedding = model.encode(user_query, show_progress_bar=False).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for text, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append(
            {
                "text": text,
                "source": meta.get("source_filename", ""),
                "page_num": meta.get("page_num", ""),
                "title": meta.get("title", ""),
                "distance": round(dist, 4),
                **{k: v for k, v in meta.items() if k not in ("source_filename", "page_num", "title")},
            }
        )

    return hits


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_id(record: dict) -> str:
    """Stable, unique ID derived from source + page + chunk_index."""
    meta = record["metadata"]
    arxiv_id = meta.get("arxiv_id", "unknown")
    page = meta.get("page_num", 0)
    chunk = meta.get("chunk_index", 0)
    return f"{arxiv_id}_p{page}_c{chunk}"


def _sanitise_metadata(meta: dict) -> dict:
    """ChromaDB metadata values must be str | int | float | bool."""
    sanitised = {}
    for k, v in meta.items():
        if isinstance(v, (str, int, float, bool)):
            sanitised[k] = v
        elif isinstance(v, list):
            sanitised[k] = ", ".join(str(i) for i in v)
        elif v is None:
            sanitised[k] = ""
        else:
            sanitised[k] = str(v)
    return sanitised


# ---------------------------------------------------------------------------
# Quick smoke-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    import json
    from pathlib import Path

    chunks_dir = Path(__file__).resolve().parent.parent / "data" / "chunks"
    chunk_files = sorted(chunks_dir.glob("chunks*.json"))

    if not chunk_files:
        print(f"No chunk files found in {chunks_dir}. Run pipeline.py first.")
    else:
        total_upserted = 0
        for chunk_file in chunk_files:
            with chunk_file.open(encoding="utf-8") as f:
                raw = json.load(f)
            print(f"Loading {len(raw)} chunks from {chunk_file.name} …")
            total_upserted += add_papers_to_db(raw)

        print(f"\nUpserted {total_upserted} chunks total into ChromaDB.")

        print("\n--- Sample query: 'What methods are used to detect exoplanets?' ---")
        hits = query_db("What methods are used to detect exoplanets?", n_results=3)
        for i, hit in enumerate(hits, 1):
            print(f"\n[{i}] distance={hit['distance']}  source={hit['source']}  page={hit['page_num']}")
            print(f"    title  : {hit['title']}")
            print(f"    excerpt: {hit['text'][:200]}…")
