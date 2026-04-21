"""
FastAPI entry point — serves the API and the React frontend as static files.

POST /query  →  embed → cosine search → Groq LLM → answer
GET  /health →  liveness check
GET  /stats  →  collection document count
GET  /*      →  React SPA (index.html fallback)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from generation.llm_client import generate_answer, get_groq_client
from retrieval.vector_store import get_collection, query_db, add_papers_to_db

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[1]
_STATIC_DIR = _ROOT / "frontend" / "dist"

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Space Research RAG API",
    description="Semantic search over space research papers.",
    version="1.0.0",
    # Hide docs in production if desired; keep enabled for now
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
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
        logger.info("Vector store ready — %d documents indexed.", col.count())
    except Exception as exc:
        logger.error("Vector store init failed: %s", exc)


# ---------------------------------------------------------------------------
# API routes  (must be registered BEFORE the static file catch-all)
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3)
    n_results: int = Field(default=5, ge=1, le=20)


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


class IngestRequest(BaseModel):
    query: str = Field(default="Exoplanets", description="arxiv search query")
    num_papers: int = Field(default=5, ge=1, le=20)


@app.post("/ingest", tags=["ops"])
async def ingest(req: IngestRequest):
    """Download papers, chunk them, and upsert into the vector store."""
    import asyncio
    from ingestion.loader import download_arxiv_papers, extract_text_from_pdf
    from ingestion.processor import chunk_pages

    root = Path(__file__).resolve().parents[1]
    raw_dir = root / "data" / "raw"
    processed_dir = root / "data" / "processed"

    try:
        papers = await asyncio.to_thread(
            download_arxiv_papers, req.query, req.num_papers, raw_dir
        )
        if not papers:
            raise HTTPException(status_code=404, detail="No papers found for that query.")

        all_chunks = []
        for paper in papers:
            pages = await asyncio.to_thread(extract_text_from_pdf, Path(paper["pdf_path"]))
            chunks = chunk_pages(pages, paper)
            all_chunks.extend(chunks)

        upserted = await asyncio.to_thread(add_papers_to_db, all_chunks)
        return {"papers": len(papers), "chunks_upserted": upserted}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Ingestion failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


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
    try:
        hits = query_db(req.query, n_results=req.n_results)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Vector search error: {exc}")

    if not hits:
        raise HTTPException(status_code=404, detail="No relevant documents found.")

    try:
        answer = generate_answer(req.query, hits)
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    logger.info("query='%s' | chunks=%d", req.query[:60], len(hits))

    return QueryResponse(
        answer=answer,
        sources=[SourceRef(**{k: h[k] for k in ("source", "title", "page_num", "distance")}) for h in hits],
        model="llama-3.1-8b-instant",
        chunks_retrieved=len(hits),
    )


# ---------------------------------------------------------------------------
# Serve React build (only when the dist folder exists)
# ---------------------------------------------------------------------------
if _STATIC_DIR.exists():
    # Serve JS/CSS/assets under /assets
    app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="assets")

    # SPA fallback — every non-API path returns index.html so React Router works
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        return FileResponse(_STATIC_DIR / "index.html")
else:
    logger.warning(
        "Frontend build not found at %s. Run: cd frontend && npm run build", _STATIC_DIR
    )
