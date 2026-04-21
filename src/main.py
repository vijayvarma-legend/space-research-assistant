"""
FastAPI entry point.

POST /query  →  embed → cosine search → Groq LLM → answer
GET  /health →  liveness check
GET  /stats  →  ChromaDB document count
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Allow sibling packages (ingestion, retrieval, generation) to be imported
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from generation.llm_client import generate_answer, get_groq_client
from retrieval.vector_store import get_collection, query_db

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Space Research RAG API",
    description="Semantic search over space research papers — ChromaDB + Groq Llama 3.1",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    try:
        get_groq_client()
    except EnvironmentError as exc:
        logger.warning("%s — /query will return 503.", exc)
    try:
        col = get_collection()
        logger.info("ChromaDB ready — %d documents indexed.", col.count())
    except Exception as exc:
        logger.error("ChromaDB init failed: %s", exc)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Natural-language question")
    n_results: int = Field(default=5, ge=1, le=20, description="Chunks to retrieve")


class SourceRef(BaseModel):
    source: str
    title: str
    page_num: int | str
    distance: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceRef]
    model: str
    chunks_retrieved: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok"}


@app.get("/stats", tags=["ops"])
async def stats():
    try:
        col = get_collection()
        return {"collection": col.name, "documents": col.count()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/query", response_model=QueryResponse, tags=["rag"])
async def query_endpoint(req: QueryRequest):
    # 1. Cosine similarity search
    try:
        hits = query_db(req.query, n_results=req.n_results)
    except Exception as exc:
        logger.error("Vector search failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Vector search error: {exc}")

    if not hits:
        raise HTTPException(
            status_code=404,
            detail="No relevant documents found. Run the ingestion pipeline first.",
        )

    # 2. Generate answer with Groq
    try:
        answer = generate_answer(req.query, hits)
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("LLM generation failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    logger.info("query='%s' | chunks=%d", req.query[:60], len(hits))

    return QueryResponse(
        answer=answer,
        sources=[
            SourceRef(
                source=h["source"],
                title=h["title"],
                page_num=h["page_num"],
                distance=h["distance"],
            )
            for h in hits
        ],
        model="llama-3.1-8b-instant",
        chunks_retrieved=len(hits),
    )
