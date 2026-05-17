"""Decision Service — Phase 6.3: architecture decision history."""

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.cache import cache_invalidate_pattern
from shared.models.registry import Decision

logger = logging.getLogger(__name__)

CACHE_PREFIX = "decision:"
CACHE_TTL = 3600


async def store_decision(
    db: AsyncSession,
    project_id: UUID,
    decision: str,
    reason: str,
    task_id: UUID | None = None,
    context: dict | None = None,
    alternatives: list | None = None,
    decided_by: str = "mentor",
) -> Decision:
    """6.3.3 — Store an architecture decision."""
    record = Decision(
        project_id=project_id,
        task_id=task_id,
        decision=decision,
        reason=reason,
        context=context or {},
        alternatives=alternatives or [],
        decided_by=decided_by,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    await cache_invalidate_pattern(f"{CACHE_PREFIX}{project_id}:*")
    logger.info(f"Decision stored for project {project_id}: {decision[:60]}")
    return record


async def get_decisions(
    db: AsyncSession,
    project_id: UUID | None = None,
    task_id: UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Decision], int]:
    """6.3.4 — Get decisions with filters."""
    query = select(Decision).order_by(Decision.created_at.desc())
    count_q = select(func.count()).select_from(Decision)

    if project_id:
        query = query.where(Decision.project_id == project_id)
        count_q = count_q.where(Decision.project_id == project_id)
    if task_id:
        query = query.where(Decision.task_id == task_id)
        count_q = count_q.where(Decision.task_id == task_id)

    total = (await db.execute(count_q)).scalar()
    result = await db.execute(
        query.offset((page - 1) * page_size).limit(page_size)
    )
    return result.scalars().all(), total


async def link_decision(
    db: AsyncSession, decision_id: UUID, task_id: UUID, instruction_id: UUID | None = None,
) -> Decision | None:
    """6.3.8 — Link a decision to a task and optionally to an instruction."""
    result = await db.execute(select(Decision).where(Decision.id == decision_id))
    decision = result.scalar_one_or_none()
    if not decision:
        return None
    decision.task_id = task_id
    if instruction_id:
        ctx = dict(decision.context or {})
        ctx["linked_instruction_id"] = str(instruction_id)
        decision.context = ctx
    await db.flush()
    await db.refresh(decision)
    return decision


def decision_to_response(dec: Decision) -> dict:
    return {
        "id": dec.id,
        "project_id": dec.project_id,
        "task_id": dec.task_id,
        "decision": dec.decision,
        "reason": dec.reason,
        "context": dec.context if dec.context else {},
        "alternatives": dec.alternatives if dec.alternatives else [],
        "decided_by": dec.decided_by,
        "created_at": dec.created_at,
        "updated_at": dec.updated_at,
    }
