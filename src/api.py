"""
FastAPI RAG service.

POST /query  →  embed query → ChromaDB cosine search → Groq LLM → answer
GET  /health →  liveness check
GET  /stats  →  collection document count
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from pydantic import BaseModel, Field

from vector_store import query_db, _get_collection

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
_LLM_MODEL = "llama-3.1-8b-instant"
_MAX_CONTEXT_CHUNKS = 5
_SYSTEM_PROMPT = (
    "You are an expert astrophysics research assistant. "
    "Answer the user's question using ONLY the provided research paper excerpts. "
    "Cite the source filename and page number when referencing specific content. "
    "If the excerpts do not contain enough information, say so clearly."
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Space Research RAG API",
    description="Semantic search over space research papers powered by ChromaDB + Groq.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Groq client (initialised once at startup)
_groq: Groq | None = None


@app.on_event("startup")
async def startup():
    global _groq
    if not _GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set — /query will raise 503.")
    else:
        _groq = Groq(api_key=_GROQ_API_KEY)
        logger.info("Groq client ready (model: %s).", _LLM_MODEL)

    # Warm up the embedding model and ChromaDB connection
    try:
        col = _get_collection()
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
        col = _get_collection()
        return {"collection": col.name, "documents": col.count()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/query", response_model=QueryResponse, tags=["rag"])
async def query_endpoint(req: QueryRequest):
    if not _groq:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY is not configured. Set it in the .env file.",
        )

    # --- 1. Cosine similarity search via ChromaDB ---
    try:
        hits = query_db(req.query, n_results=min(req.n_results, _MAX_CONTEXT_CHUNKS))
    except Exception as exc:
        logger.error("Vector search failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Vector search error: {exc}")

    if not hits:
        raise HTTPException(
            status_code=404,
            detail="No relevant documents found. Run the ingestion pipeline first.",
        )

    # --- 2. Build context from retrieved chunks ---
    context_blocks = []
    for i, hit in enumerate(hits, 1):
        context_blocks.append(
            f"[{i}] Source: {hit['source']} | Page: {hit['page_num']} | "
            f"Title: {hit['title']}\n{hit['text']}"
        )
    context = "\n\n---\n\n".join(context_blocks)

    user_message = f"Context:\n{context}\n\nQuestion: {req.query}"

    # --- 3. Generate answer with Groq ---
    try:
        completion = _groq.chat.completions.create(
            model=_LLM_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        answer = completion.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("Groq API call failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    sources = [
        SourceRef(
            source=h["source"],
            title=h["title"],
            page_num=h["page_num"],
            distance=h["distance"],
        )
        for h in hits
    ]

    logger.info(
        "Query='%s' | chunks=%d | model=%s", req.query[:60], len(hits), _LLM_MODEL
    )

    return QueryResponse(
        answer=answer,
        sources=sources,
        model=_LLM_MODEL,
        chunks_retrieved=len(hits),
    )
