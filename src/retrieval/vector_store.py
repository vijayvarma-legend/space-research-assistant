"""
ChromaDB connection, HNSW config, upsert, and cosine similarity search.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Union

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chromadb
from chromadb.config import Settings

from retrieval.embedder import embed
from ingestion.processor import Document

logger = logging.getLogger(__name__)

_DB_DIR = Path(__file__).resolve().parents[2] / "database"
_COLLECTION_NAME = "space_papers"
_BATCH_SIZE = 64

_client: chromadb.PersistentClient | None = None
_collection: chromadb.Collection | None = None


def get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is None:
        logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
        logger.debug("Initialising ChromaDB at %s", _DB_DIR)
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
            "ChromaDB ready — collection '%s', %d docs indexed",
            _COLLECTION_NAME, _collection.count(),
        )
    return _collection


def add_papers_to_db(chunks: list[Union[Document, dict]]) -> int:
    """
    Embed and upsert chunks. Accepts Document objects or plain dicts.
    Returns number of chunks upserted.
    """
    if not chunks:
        logger.warning("add_papers_to_db called with empty chunk list — nothing to do.")
        return 0

    logger.info("Starting upsert of %d chunks into '%s'", len(chunks), _COLLECTION_NAME)
    t0 = time.perf_counter()

    collection = get_collection()
    records = [c.to_dict() if isinstance(c, Document) else c for c in chunks]

    texts = [r["content"] for r in records]
    ids = [_make_id(r) for r in records]
    metadatas = [_sanitise(r["metadata"]) for r in records]

    total = 0
    num_batches = (len(texts) + _BATCH_SIZE - 1) // _BATCH_SIZE

    for batch_num, start in enumerate(range(0, len(texts), _BATCH_SIZE), 1):
        sl = slice(start, start + _BATCH_SIZE)
        batch_texts = texts[sl]

        logger.debug(
            "Embedding batch %d/%d (%d chunks)",
            batch_num, num_batches, len(batch_texts),
        )
        embeddings = embed(batch_texts)

        logger.debug("Upserting batch %d/%d into ChromaDB", batch_num, num_batches)
        collection.upsert(
            ids=ids[sl],
            documents=batch_texts,
            embeddings=embeddings,
            metadatas=metadatas[sl],
        )
        total += len(batch_texts)
        logger.info(
            "Batch %d/%d done — %d/%d chunks upserted",
            batch_num, num_batches, total, len(texts),
        )

    elapsed = time.perf_counter() - t0
    logger.info(
        "Upsert complete — %d chunks in %.2fs (collection total: %d docs)",
        total, elapsed, collection.count(),
    )
    return total


def query_db(user_query: str, n_results: int = 5) -> list[dict]:
    """
    Cosine similarity search. Returns top-n chunks with text + metadata.
    """
    if not user_query.strip():
        raise ValueError("user_query must not be empty.")

    logger.info("Query received: '%s' (n_results=%d)", user_query[:80], n_results)
    t0 = time.perf_counter()

    collection = get_collection()
    if collection.count() == 0:
        logger.warning("Collection '%s' is empty — run ingestion pipeline first.", _COLLECTION_NAME)
        return []

    logger.debug("Embedding query text")
    query_embedding = embed(user_query)

    capped = min(n_results, collection.count())
    logger.debug("Searching collection (n_results=%d)", capped)

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=capped,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for text, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append({
            "text": text,
            "source": meta.get("source_filename", ""),
            "page_num": meta.get("page_num", ""),
            "title": meta.get("title", ""),
            "distance": round(dist, 4),
            **{k: v for k, v in meta.items()
               if k not in ("source_filename", "page_num", "title")},
        })

    elapsed = time.perf_counter() - t0
    logger.info(
        "Search complete — %d results in %.3fs (best distance: %.4f)",
        len(hits), elapsed, hits[0]["distance"] if hits else 0.0,
    )
    for i, h in enumerate(hits, 1):
        logger.debug(
            "  [%d] dist=%.4f  source=%s  page=%s  title=%s",
            i, h["distance"], h["source"], h["page_num"], h["title"],
        )

    return hits


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_id(record: dict) -> str:
    m = record["metadata"]
    return f"{m.get('arxiv_id', 'x')}_p{m.get('page_num', 0)}_c{m.get('chunk_index', 0)}"


def _sanitise(meta: dict) -> dict:
    out = {}
    for k, v in meta.items():
        if isinstance(v, (str, int, float, bool)):
            out[k] = v
        elif isinstance(v, list):
            out[k] = ", ".join(str(i) for i in v)
        else:
            out[k] = "" if v is None else str(v)
    return out


# ---------------------------------------------------------------------------
# CLI smoke-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                Path(__file__).resolve().parents[2] / "logs" / "vector_store.log",
                encoding="utf-8",
            ),
        ],
    )
    (Path(__file__).resolve().parents[2] / "logs").mkdir(exist_ok=True)

    import json

    processed_dir = Path(__file__).resolve().parents[2] / "data" / "processed"
    chunk_files = sorted(processed_dir.glob("chunks*.json"))

    if not chunk_files:
        logger.error("No chunk files found in %s — run pipeline.py first.", processed_dir)
    else:
        total = 0
        for f in chunk_files:
            raw = json.loads(f.read_text(encoding="utf-8"))
            logger.info("Loading %d chunks from %s", len(raw), f.name)
            total += add_papers_to_db(raw)
        logger.info("Total upserted: %d chunks", total)

        hits = query_db("What methods are used to detect exoplanets?", n_results=3)
        for i, h in enumerate(hits, 1):
            print(f"\n[{i}] dist={h['distance']}  {h['source']}  p{h['page_num']}")
            print(f"    {h['text'][:200]}")
