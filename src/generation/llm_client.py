"""
Groq API integration for Llama 3.1 answer generation.
"""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import logging
import os

from groq import Groq

logger = logging.getLogger(__name__)

_MODEL = "llama-3.1-8b-instant"
_SYSTEM_PROMPT = (
    "You are an expert astrophysics research assistant. "
    "Answer the user's question using ONLY the provided research paper excerpts. "
    "Cite the source filename and page number when referencing specific content. "
    "If the excerpts do not contain enough information, say so clearly."
)

_client: Groq | None = None


def get_groq_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY is not set in the environment.")
        _client = Groq(api_key=api_key)
        logger.info("Groq client initialised (model: %s).", _MODEL)
    return _client


def generate_answer(user_query: str, context_chunks: list[dict]) -> str:
    """
    Build a prompt from retrieved chunks and return the LLM answer.

    context_chunks: list of dicts with keys 'text', 'source', 'page_num', 'title'
    """
    context_blocks = []
    for i, chunk in enumerate(context_chunks, 1):
        context_blocks.append(
            f"[{i}] Source: {chunk['source']} | Page: {chunk['page_num']} | "
            f"Title: {chunk['title']}\n{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_blocks)

    completion = get_groq_client().chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {user_query}"},
        ],
        temperature=0.2,
        max_tokens=1024,
    )
    return completion.choices[0].message.content.strip()
