"""Embedding Service — Phase 6.2: pgvector + embeddings for semantic retrieval."""

import hashlib
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.cache import cache_get, cache_set
from shared.models.registry import MentorInstruction

logger = logging.getLogger(__name__)

EMBEDDING_DIMS = 1536
SIMILARITY_THRESHOLD = 0.7
TOP_K = 5
CACHE_PREFIX = "embedding:"
CACHE_TTL = 86400


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().split())[:1000]


def _simple_embed(text: str) -> list[float]:
    """Generate a deterministic pseudo-embedding based on character distribution.

    Used when no embedding model is available. Maps text to a fixed-dimension vector
    using character-level frequency analysis.
    """
    vec = [0.0] * EMBEDDING_DIMS
    normalized = _normalize_text(text)
    chars = list(normalized)
    if not chars:
        return vec
    for i, ch in enumerate(chars):
        idx = (ord(ch) * (i + 1)) % EMBEDDING_DIMS
        vec[idx] += 1.0
    magnitude = sum(v * v for v in vec) ** 0.5
    if magnitude > 0:
        vec = [v / magnitude for v in vec]
    return vec


async def generate_embedding(text: str) -> list[float]:
    """6.2.2 — Generate embedding for text (uses pseudo-embedding by default)."""
    cache_key = f"{CACHE_PREFIX}{_text_hash(text)}"
    cached = await cache_get(cache_key)
    if cached is not None:
        logger.debug(f"Embedding cache hit for text hash {_text_hash(text)}")
        return cached
    embedding = _simple_embed(text)
    await cache_set(cache_key, embedding, ttl=CACHE_TTL)
    logger.debug(f"Generated embedding ({EMBEDDING_DIMS} dims) for {len(text)} chars")
    return embedding


async def store_embedding(
    db: AsyncSession, instruction_id: UUID, embedding: list[float],
) -> bool:
    """6.2.3 — Store embedding alongside instruction content."""
    try:
        vector_str = "[" + ",".join(str(v) for v in embedding[:EMBEDDING_DIMS]) + "]"
        stmt = text(
            "UPDATE mentor_instructions SET embedding = :embedding WHERE id = :id"
        )
        await db.execute(stmt, {"embedding": vector_str, "id": instruction_id})
        await db.flush()
        return True
    except Exception as e:
        logger.warning(f"Failed to store embedding for {instruction_id}: {e}")
        return False


async def semantic_search(
    db: AsyncSession,
    query: str,
    top_k: int = TOP_K,
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    """6.2.4 — Search instructions by semantic similarity.

    Falls back to keyword matching if pgvector extension is not available.
    """
    try:
        query_embedding = await generate_embedding(query)
        vector_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
        stmt = text("""
            SELECT mi.id, mi.task_id, mi.instruction_type, mi.content,
                   mi.context, mi.applied, mi.created_at,
                   1 - (mi.embedding::vector <=> :query_vec::vector) AS similarity
            FROM mentor_instructions mi
            WHERE mi.embedding IS NOT NULL
              AND 1 - (mi.embedding::vector <=> :query_vec::vector) >= :threshold
            ORDER BY similarity DESC
            LIMIT :top_k
        """)
        result = await db.execute(stmt, {
            "query_vec": vector_str,
            "threshold": threshold,
            "top_k": top_k,
        })
        rows = result.fetchall()
        return [
            {
                "id": row[0], "task_id": row[1], "instruction_type": row[2],
                "content": row[3], "context": row[4], "applied": row[5],
                "created_at": str(row[6]), "similarity": round(float(row[7]), 4),
            }
            for row in rows
        ]
    except Exception as e:
        logger.warning(f"pgvector search failed, falling back to keyword: {e}")
        return await _keyword_search(db, query, top_k, threshold)


async def _keyword_search(
    db: AsyncSession, query: str, top_k: int = TOP_K, threshold: float = SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    """Keyword-based fallback when pgvector is unavailable."""
    keywords = _normalize_text(query).split()
    if not keywords:
        return []
    result = await db.execute(
        select(MentorInstruction).order_by(MentorInstruction.created_at.desc()).limit(top_k * 5)
    )
    instructions = result.scalars().all()
    results = []
    for inst in instructions:
        content = (inst.content or "").lower()
        matches = sum(1 for kw in keywords if kw in content)
        if matches > 0:
            score = matches / len(keywords)
            if score >= threshold:
                results.append({
                    "id": inst.id,
                    "task_id": inst.task_id,
                    "instruction_type": inst.instruction_type.value if hasattr(inst.instruction_type, "value") else str(inst.instruction_type),
                    "content": inst.content,
                    "context": inst.context,
                    "applied": inst.applied,
                    "created_at": str(inst.created_at),
                    "similarity": round(score, 4),
                })
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]


async def filter_by_similarity(
    results: list[dict[str, Any]], threshold: float = SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    """6.2.5 — Filter results below similarity threshold."""
    return [r for r in results if r.get("similarity", 0) >= threshold]


async def retrieve_memory(
    db: AsyncSession, task_spec: str, top_k: int = TOP_K, threshold: float = SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    """6.2.6 — Full memory retrieval workflow: query → search → filter → return."""
    results = await semantic_search(db, task_spec, top_k=top_k * 2, threshold=0.0)
    filtered = await filter_by_similarity(results, threshold)
    return filtered[:top_k]
