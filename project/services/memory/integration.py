"""Memory Integration — Phase 6.4: hook into Gatekeeper, Orchestrator, Specialist."""

import hashlib
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from services.memory import ledger
from services.memory.cache_service import cache_get, cache_set
from services.memory.decision_service import store_decision
from services.memory.embedding_service import retrieve_memory

logger = logging.getLogger(__name__)

CACHE_PREFIX = "memory_integration:"
CACHE_TTL = 600


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


async def gatekeeper_memory_lookup(
    db: AsyncSession, task_description: str, top_k: int = 3,
) -> list[dict]:
    """6.4.1 — Look up past solutions for similar tasks."""
    cache_key = f"{CACHE_PREFIX}gatekeeper:{_text_hash(task_description)}"
    cached = await cache_get(cache_key)
    if cached is not None:
        logger.debug("Gatekeeper memory lookup cache hit")
        return cached
    results = await retrieve_memory(db, task_description, top_k=top_k, threshold=0.7)
    if results:
        await cache_set(cache_key, results, ttl=CACHE_TTL)
        logger.info(f"Gatekeeper found {len(results)} past solutions")
    return results


async def orchestrator_memory_lookup(
    db: AsyncSession, task_spec: str, top_k: int = 5,
) -> list[dict]:
    """6.4.2 — Retrieve relevant solutions for task planning."""
    cache_key = f"{CACHE_PREFIX}orchestrator:{_text_hash(task_spec)}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    results = await retrieve_memory(db, task_spec, top_k=top_k, threshold=0.65)
    if results:
        await cache_set(cache_key, results, ttl=CACHE_TTL)
        logger.info(f"Orchestrator found {len(results)} relevant solutions")
    return results


async def specialist_memory_lookup(
    db: AsyncSession, task_spec: str, top_k: int = 3,
) -> list[dict]:
    """6.4.3 — Retrieve warnings (failed patterns) before coding."""
    cache_key = f"{CACHE_PREFIX}specialist:{_text_hash(task_spec)}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    results = await retrieve_memory(db, task_spec, top_k=top_k * 2, threshold=0.6)
    warnings = [r for r in results if r.get("instruction_type") == "warning"]
    if warnings:
        await cache_set(cache_key, warnings, ttl=CACHE_TTL)
        logger.info(f"Specialist found {len(warnings)} past warnings")
    return warnings[:top_k]


def quality_check_memory(entry: dict) -> bool:
    """6.4.5 — Filter low-quality memory entries before storing."""
    content = (entry.get("content") or "").strip()
    if len(content) < 10:
        logger.debug(f"Rejected memory entry: too short ({len(content)} chars)")
        return False
    min_content_words = 3
    if len(content.split()) < min_content_words:
        logger.debug("Rejected memory entry: too few words")
        return False
    low_quality_phrases = [
        "test", "placeholder", "todo", "fixme", "example", "sample",
        "dummy", "lorem ipsum", "asdf",
    ]
    content_lower = content.lower()
    for phrase in low_quality_phrases:
        if phrase in content_lower and len(content) < 30:
            logger.debug("Rejected memory entry: low-quality content")
            return False
    return True


async def update_memory_after_task(
    db: AsyncSession,
    task_id: UUID,
    project_id: UUID | None = None,
    logs: list[dict] | None = None,
) -> dict[str, int]:
    """6.4.4 — Auto-store lessons learned, decisions, patterns after task completes."""
    counts = {"lessons": 0, "decisions": 0, "patterns": 0, "rejected": 0}
    logs = logs or []
    seen_decisions = set()
    for log_entry in logs:
        content = log_entry.get("content", "")
        entry_type = log_entry.get("type", "lesson")
        if not quality_check_memory({"content": content}):
            counts["rejected"] += 1
            continue
        if entry_type == "decision":
            key = (log_entry.get("project_id", project_id), content[:100])
            if key in seen_decisions:
                continue
            seen_decisions.add(key)
            if project_id or log_entry.get("project_id"):
                await store_decision(
                    db,
                    project_id=log_entry.get("project_id", project_id),
                    decision=content,
                    reason=log_entry.get("reason", "Auto-logged after task completion"),
                    task_id=task_id,
                    context=log_entry.get("context", {}),
                    alternatives=log_entry.get("alternatives", []),
                    decided_by="system",
                )
            counts["decisions"] += 1
        else:
            await ledger.store_lesson_learned(
                db, task_id, content, context=log_entry.get("context"),
            )
            if entry_type == "pattern":
                counts["patterns"] += 1
            else:
                counts["lessons"] += 1
    logger.info(f"Memory updated after task {task_id}: {counts}")
    return counts
