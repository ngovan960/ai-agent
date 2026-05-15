import logging
from uuid import UUID
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.task import Task, TaskStatus, TaskDependency
from shared.models.registry import MentorInstruction, AuditLog, AuditResult
from shared.schemas.task import StateTransitionRequest
from services.orchestrator.services import tasks as task_service

logger = logging.getLogger(__name__)


class MentorAction(str, Enum):
    REWRITE = "rewrite"
    REDESIGN = "redesign"
    OVERRIDE = "override"
    REJECT = "reject"
    APPROVE = "approve"


async def mentor_takeover(
    db: AsyncSession,
    task_id: UUID,
    mentor_id: str,
    action: MentorAction,
    reason: str,
    new_instructions: str | None = None,
) -> tuple[bool, str, dict | None]:
    """Mentor takes over an escalated task with a decision."""
    task = await task_service.get_task(db, task_id)
    if not task:
        return False, "Task not found", None

    current_status = task.status.value if hasattr(task.status, "value") else str(task.status)
    history = {
        "retries": task.retries,
        "current_status": current_status,
        "title": task.title,
        "description": task.description,
        "failure_reason": task.failure_reason,
    }

    decision_result = {
        "mentor_id": mentor_id,
        "action": action.value,
        "reason": reason,
        "task_id": str(task_id),
    }

    target_state = None
    if action == MentorAction.REWRITE:
        target_state = "IMPLEMENTING"
        decision_result["message"] = "Mentor rewrite: returning to implementation"
    elif action == MentorAction.REDESIGN:
        target_state = "PLANNING"
        decision_result["message"] = "Mentor redesign: returning to planning"
    elif action == MentorAction.OVERRIDE:
        target_state = "VERIFYING"
        decision_result["message"] = "Mentor override: skipping to verification"
    elif action == MentorAction.REJECT:
        target_state = "FAILED"
        decision_result["message"] = "Mentor rejected task"
    elif action == MentorAction.APPROVE:
        target_state = "DONE"
        decision_result["message"] = "Mentor approved task"

    if target_state:
        updated, error = await task_service.transition_task_state(
            db, task_id,
            StateTransitionRequest(target_status=target_state, reason=f"Mentor {action.value}: {reason}"),
        )
        if error:
            decision_result["transition_error"] = error
        else:
            decision_result["transitioned_to"] = target_state

    instruction = MentorInstruction(
        task_id=task_id,
        instruction_type=action.value,
        content=new_instructions or f"Mentor {action.value}: {reason}",
        context={
            "mentor_id": mentor_id,
            "action": action.value,
            "reason": reason,
            "task_history": history,
        },
        applied=target_state is not None,
    )
    db.add(instruction)

    log = AuditLog(
        task_id=task_id,
        action=f"mentor_{action.value}",
        actor=mentor_id,
        actor_type="mentor",
        input={"reason": reason, "action": action.value},
        output={"target_state": target_state, "new_instructions": new_instructions},
        result=AuditResult.SUCCESS,
        message=f"Mentor {action.value}: {reason}",
    )
    db.add(log)
    await db.flush()

    return True, f"Mentor {action.value} completed", decision_result


async def get_mentor_instructions(
    db: AsyncSession, task_id: UUID
) -> list[dict]:
    """Get all mentor instructions for a task."""
    result = await db.execute(
        select(MentorInstruction)
        .where(MentorInstruction.task_id == task_id)
        .order_by(MentorInstruction.created_at.desc())
    )
    instructions = result.scalars().all()

    return [
        {
            "id": str(i.id),
            "instruction_type": i.instruction_type,
            "content": i.content,
            "context": i.context,
            "applied": i.applied,
            "created_at": i.created_at.isoformat() if i.created_at else None,
        }
        for i in instructions
    ]


async def check_mentor_quota(db: AsyncSession, user_id: UUID | None = None) -> tuple[bool, int, int]:
    from shared.models.registry import MentorQuota
    today = datetime.now(timezone.utc).date()

    if user_id is None:
        from uuid import UUID
        user_id = UUID("00000000-0000-0000-0000-000000000000")

    result = await db.execute(
        select(MentorQuota).where(MentorQuota.user_id == user_id, MentorQuota.date == today)
    )
    quota = result.scalar_one_or_none()

    if not quota:
        quota = MentorQuota(user_id=user_id, date=today, calls_used=0, calls_limit=10)
        db.add(quota)
        await db.flush()

    remaining = quota.calls_limit - quota.calls_used
    return remaining > 0, remaining, quota.calls_limit


async def record_mentor_call(db: AsyncSession, user_id: UUID | None = None) -> None:
    from shared.models.registry import MentorQuota
    today = datetime.now(timezone.utc).date()

    if user_id is None:
        from uuid import UUID
        user_id = UUID("00000000-0000-0000-0000-000000000000")

    result = await db.execute(
        select(MentorQuota).where(MentorQuota.user_id == user_id, MentorQuota.date == today)
    )
    quota = result.scalar_one_or_none()

    if not quota:
        quota = MentorQuota(user_id=user_id, date=today, calls_used=1, calls_limit=10)
        db.add(quota)
    else:
        quota.calls_used += 1

    await db.flush()

    remaining = quota.calls_limit - quota.calls_used
    return remaining > 0, remaining, quota.calls_limit


async def record_mentor_call(db: AsyncSession) -> None:
    """Record a mentor call in the quota tracker."""
    from shared.models.registry import MentorQuota
    today = datetime.now(timezone.utc).date()

    result = await db.execute(
        select(MentorQuota).where(MentorQuota.date == today)
    )
    quota = result.scalar_one_or_none()

    if not quota:
        quota = MentorQuota(date=today, calls_used=1, calls_limit=10)
        db.add(quota)
    else:
        quota.calls_used += 1

    await db.flush()
