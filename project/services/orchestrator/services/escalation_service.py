import logging
from dataclasses import dataclass, field
from uuid import UUID
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.task import Task, TaskStatus
from shared.models.registry import AuditLog, AuditResult

logger = logging.getLogger(__name__)


class EscalationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(order=True)
class EscalationItem:
    priority: int
    task_id: UUID = field(compare=False)
    task_title: str = field(compare=False, default="")
    risk_level: str = field(compare=False, default="medium")
    retries: int = field(compare=False, default=0)
    reason: str = field(compare=False, default="")
    created_at: datetime = field(compare=False, default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def priority_rank(risk_level: str) -> int:
        ranking = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return ranking.get(risk_level.lower(), 2)


class EscalationPriorityQueue:
    """Priority queue for escalated tasks, ordered by severity."""

    def __init__(self):
        self._queue: list[EscalationItem] = []

    def push(self, item: EscalationItem) -> None:
        item.priority = EscalationItem.priority_rank(item.risk_level)
        self._queue.append(item)
        self._queue.sort(key=lambda x: (x.priority, x.created_at))

    def pop(self) -> EscalationItem | None:
        if not self._queue:
            return None
        return self._queue.pop(0)

    def peek(self) -> EscalationItem | None:
        if not self._queue:
            return None
        return self._queue[0]

    def remove(self, task_id: UUID) -> bool:
        for i, item in enumerate(self._queue):
            if item.task_id == task_id:
                self._queue.pop(i)
                return True
        return False

    def get_all(self) -> list[EscalationItem]:
        return list(self._queue)

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def size(self) -> int:
        return len(self._queue)


_escalation_queue = EscalationPriorityQueue()


def get_escalation_queue() -> EscalationPriorityQueue:
    return _escalation_queue


async def should_escalate(db: AsyncSession, task_id: UUID) -> tuple[bool, str]:
    """Check if a task should be escalated based on retry count."""
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        return False, "Task not found"

    if task.retries > 2:
        return True, f"Task exceeded max retries ({task.retries} > 2)"

    current_status = task.status.value if hasattr(task.status, "value") else str(task.status)
    if current_status == "FAILED":
        return True, "Task in FAILED state"

    return False, "Task does not need escalation"


async def escalate_task(
    db: AsyncSession, task_id: UUID, reason: str, context: dict | None = None
) -> tuple[bool, str]:
    """Escalate a task and add it to the priority queue."""
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        return False, "Task not found"

    current_status = task.status.value if hasattr(task.status, "value") else str(task.status)
    if current_status in ("ESCALATED",):
        return False, "Task is already escalated"

    risk_level = task.risk_level.value if hasattr(task.risk_level, "value") else str(task.risk_level) if task.risk_level else "medium"

    item = EscalationItem(
        task_id=task_id,
        task_title=task.title,
        risk_level=risk_level,
        retries=task.retries,
        reason=reason,
        priority=EscalationItem.priority_rank(risk_level),
    )
    _escalation_queue.push(item)

    log = AuditLog(
        task_id=task_id,
        action="escalation_triggered",
        actor="escalation_engine",
        actor_type="system",
        input={"reason": reason, "context": context or {}},
        output={"risk_level": risk_level, "retries": task.retries},
        result=AuditResult.SUCCESS,
        message=f"Task escalated: {reason}",
    )
    db.add(log)
    await db.flush()

    logger.warning(
        f"Task {task_id} escalated: {reason} "
        f"(risk={risk_level}, retries={task.retries}, "
        f"queue_size={_escalation_queue.size()})"
    )

    return True, f"Task escalated to priority queue"


async def get_escalation_stats(db: AsyncSession) -> dict:
    """Get escalation queue statistics."""
    result = await db.execute(
        select(func.count()).select_from(Task).where(Task.status == TaskStatus.ESCALATED)
    )
    escalated_count = result.scalar() or 0

    return {
        "queue_size": _escalation_queue.size(),
        "total_escalated_tasks": escalated_count,
        "next_in_queue": str(_escalation_queue.peek().task_id) if _escalation_queue.peek() else None,
    }
