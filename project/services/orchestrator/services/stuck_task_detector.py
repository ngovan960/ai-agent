import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.task import Task, TaskStatus
from shared.schemas.task import StateTransitionRequest
from shared.concurrency import OptimisticLockError

logger = logging.getLogger(__name__)

STUCK_TIMEOUT_MINUTES = 30
ESCALATION_TIMEOUT_MINUTES = 60
BLOCKED_TIMEOUT_MINUTES = 120


async def detect_stuck_tasks(db: AsyncSession) -> list[dict[str, Any]]:
    """
    Detect tasks stuck in non-terminal states beyond timeout threshold.

    Returns list of stuck tasks with details for alerting.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=STUCK_TIMEOUT_MINUTES)

    terminal_statuses = [TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED]

    result = await db.execute(
        select(Task).where(
            Task.status.not_in(terminal_statuses),
            Task.updated_at < cutoff,
        )
    )
    stuck_tasks = result.scalars().all()

    stuck_details = []
    for task in stuck_tasks:
        minutes_stuck = int((now - task.updated_at).total_seconds() / 60)
        stuck_details.append({
            "task_id": task.id,
            "title": task.title,
            "status": task.status.value if hasattr(task.status, "value") else task.status,
            "minutes_stuck": minutes_stuck,
            "severity": "critical" if minutes_stuck > ESCALATION_TIMEOUT_MINUTES else "warning",
        })

    if stuck_details:
        logger.warning(f"Detected {len(stuck_details)} stuck tasks")

    return stuck_details


async def auto_resolve_blocked_tasks(db: AsyncSession) -> list[dict[str, Any]]:
    """
    Auto-escalate BLOCKED tasks that have been stuck beyond timeout.

    If a task is BLOCKED for more than BLOCKED_TIMEOUT_MINUTES,
    escalate to Mentor for review.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=BLOCKED_TIMEOUT_MINUTES)

    result = await db.execute(
        select(Task)
        .with_for_update()
        .where(
            Task.status == TaskStatus.BLOCKED,
            Task.updated_at < cutoff,
        )
    )
    expired_blocked_tasks = result.scalars().all()

    resolved = []
    for task in expired_blocked_tasks:
        try:
            task.status = TaskStatus.ESCALATED
            task.version += 1
            task.failure_reason = (
                f"Auto-escalated: task was BLOCKED for {BLOCKED_TIMEOUT_MINUTES}+ minutes "
                f"without resolution. Requires Mentor review."
            )
            await db.flush()
            await db.refresh(task)

            resolved.append({
                "task_id": task.id,
                "title": task.title,
                "previous_status": "BLOCKED",
                "new_status": "ESCALATED",
                "reason": task.failure_reason,
            })

            logger.info(
                f"Auto-escalated BLOCKED task {task.id} ({task.title}) "
                f"after {BLOCKED_TIMEOUT_MINUTES}+ minutes"
            )
        except Exception as e:
            logger.warning(f"Failed to auto-escalate BLOCKED task {task.id}: {e}")
            continue

    return resolved


async def auto_escalate_stuck_tasks(db: AsyncSession) -> list[dict[str, Any]]:
    """
    Auto-escalate tasks stuck in non-terminal states beyond critical timeout.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=ESCALATION_TIMEOUT_MINUTES)

    terminal_statuses = [TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.ESCALATED]

    result = await db.execute(
        select(Task)
        .with_for_update()
        .where(
            Task.status.not_in(terminal_statuses),
            Task.updated_at < cutoff,
        )
    )
    stuck_tasks = result.scalars().all()

    escalated = []
    for task in stuck_tasks:
        try:
            old_status = task.status.value if hasattr(task.status, "value") else task.status
            task.status = TaskStatus.ESCALATED
            task.version += 1
            task.failure_reason = (
                f"Auto-escalated: task stuck in {old_status} for {ESCALATION_TIMEOUT_MINUTES}+ minutes"
            )
            await db.flush()
            await db.refresh(task)

            escalated.append({
                "task_id": task.id,
                "title": task.title,
                "previous_status": old_status,
                "new_status": "ESCALATED",
                "reason": task.failure_reason,
            })

        except Exception as e:
            logger.warning(f"Failed to auto-escalate stuck task {task.id}: {e}")
            continue

        logger.info(
            f"Auto-escalated stuck task {task.id} ({task.title}) "
            f"from {old_status} after {ESCALATION_TIMEOUT_MINUTES}+ minutes"
        )

    return escalated


async def run_stuck_task_detection(db: AsyncSession) -> dict[str, Any]:
    """
    Main function to run all stuck task detection and resolution.
    Call this periodically (e.g., every 5 minutes via cron or background task).
    """
    stuck = await detect_stuck_tasks(db)
    blocked_resolved = await auto_resolve_blocked_tasks(db)
    stuck_escalated = await auto_escalate_stuck_tasks(db)

    return {
        "stuck_tasks_detected": len(stuck),
        "blocked_tasks_auto_escalated": len(blocked_resolved),
        "stuck_tasks_auto_escalated": len(stuck_escalated),
        "details": {
            "stuck": stuck,
            "blocked_resolved": blocked_resolved,
            "stuck_escalated": stuck_escalated,
        },
    }
