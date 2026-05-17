"""Instruction Ledger — Phase 6.1: mentor advice, failed patterns, lessons learned."""

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.cache import cache_invalidate_pattern
from shared.models.registry import InstructionType, MentorInstruction
from shared.schemas.mentor_instruction import (
    InstructionUpdate,
)

logger = logging.getLogger(__name__)

CACHE_PREFIX = "instruction:"
CACHE_TTL = 3600


async def store_instruction(
    db: AsyncSession,
    task_id: UUID,
    instruction_type: str,
    content: str,
    context: dict | None = None,
) -> MentorInstruction:
    """6.1.3 — Store a general instruction."""
    type_enum = InstructionType(instruction_type)
    instruction = MentorInstruction(
        task_id=task_id,
        instruction_type=type_enum,
        content=content,
        context=context or {},
    )
    db.add(instruction)
    await db.flush()
    await db.refresh(instruction)
    await cache_invalidate_pattern(f"{CACHE_PREFIX}{task_id}:*")
    logger.info(f"Stored {instruction_type} for task {task_id}")
    return instruction


async def store_mentor_advice(
    db: AsyncSession, task_id: UUID, advice: str, context: dict | None = None,
) -> MentorInstruction:
    """6.1.4 — Store mentor advice."""
    return await store_instruction(db, task_id, "advice", advice, context)


async def store_failed_pattern(
    db: AsyncSession, task_id: UUID, pattern: str, reason: str, context: dict | None = None,
) -> MentorInstruction:
    """6.1.5 — Store failed pattern."""
    ctx = {"reason": reason, **(context or {})}
    return await store_instruction(db, task_id, "warning", f"FAILED: {pattern} — {reason}", ctx)


async def store_architecture_decision(
    db: AsyncSession, task_id: UUID, decision: str, reason: str, alternatives: list | None = None,
) -> MentorInstruction:
    """6.1.6 — Store architecture decision."""
    ctx = {"reason": reason, "alternatives": alternatives or []}
    return await store_instruction(db, task_id, "decision", decision, ctx)


async def store_lesson_learned(
    db: AsyncSession, task_id: UUID, lesson: str, context: dict | None = None,
) -> MentorInstruction:
    """6.1.7 — Store lesson learned."""
    return await store_instruction(db, task_id, "pattern", lesson, context)


async def get_instructions(
    db: AsyncSession,
    task_id: UUID | None = None,
    instruction_type: str | None = None,
    applied: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[MentorInstruction], int]:
    """6.1.8 — Get instructions with filters."""
    query = select(MentorInstruction).order_by(MentorInstruction.created_at.desc())
    count_q = select(func.count()).select_from(MentorInstruction)

    if task_id:
        query = query.where(MentorInstruction.task_id == task_id)
        count_q = count_q.where(MentorInstruction.task_id == task_id)
    if instruction_type:
        query = query.where(MentorInstruction.instruction_type == instruction_type)
        count_q = count_q.where(MentorInstruction.instruction_type == instruction_type)
    if applied is not None:
        query = query.where(MentorInstruction.applied == applied)
        count_q = count_q.where(MentorInstruction.applied == applied)

    total = (await db.execute(count_q)).scalar()
    result = await db.execute(
        query.offset((page - 1) * page_size).limit(page_size)
    )
    return result.scalars().all(), total


async def update_instruction(
    db: AsyncSession, instruction_id: UUID, data: InstructionUpdate,
) -> MentorInstruction | None:
    """Update an instruction (e.g. mark as applied)."""
    result = await db.execute(select(MentorInstruction).where(MentorInstruction.id == instruction_id))
    instruction = result.scalar_one_or_none()
    if not instruction:
        return None
    if data.applied is not None:
        instruction.applied = data.applied
    await db.flush()
    await db.refresh(instruction)
    await cache_invalidate_pattern(f"{CACHE_PREFIX}{instruction.task_id}:*")
    return instruction


def instruction_to_response(inst: MentorInstruction) -> dict:
    return {
        "id": inst.id,
        "task_id": inst.task_id,
        "instruction_type": inst.instruction_type.value if hasattr(inst.instruction_type, "value") else str(inst.instruction_type),
        "content": inst.content,
        "context": inst.context,
        "applied": inst.applied,
        "embedding": getattr(inst, "embedding", None),
        "created_at": inst.created_at.isoformat() if inst.created_at else None,
        "updated_at": inst.updated_at.isoformat() if inst.updated_at else None,
    }
