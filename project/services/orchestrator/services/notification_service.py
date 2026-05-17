import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class Notification:
    task_id: UUID
    event: str
    message: str
    severity: str
    created_at: str
    read: bool = False


class EscalationPriorityQueue:
    def __init__(self):
        self._queue: list[dict] = []

    async def push(self, task_id: UUID, reason: str, severity: str):
        priority = {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(severity, 2)
        self._queue.append({"task_id": str(task_id), "reason": reason, "severity": severity, "priority": priority, "created_at": datetime.now(UTC).isoformat()})
        self._queue.sort(key=lambda x: (x["priority"], x["created_at"]))

    async def pop(self) -> dict | None:
        if self._queue:
            return self._queue.pop(0)
        return None

    async def peek(self) -> dict | None:
        if self._queue:
            return self._queue[0]
        return None

    async def get_all(self) -> list[dict]:
        return list(self._queue)

    async def remove(self, task_id: UUID) -> bool:
        before = len(self._queue)
        self._queue = [q for q in self._queue if q["task_id"] != str(task_id)]
        return len(self._queue) < before


_escalation_queue = EscalationPriorityQueue()


def get_escalation_queue() -> EscalationPriorityQueue:
    return _escalation_queue


class NotificationService:
    def __init__(self):
        self._notifications: list[Notification] = []

    async def notify(self, task_id: UUID, event: str, message: str, severity: str = "info"):
        notification = Notification(
            task_id=task_id, event=event, message=message,
            severity=severity, created_at=datetime.now(UTC).isoformat(),
        )
        self._notifications.append(notification)
        logger.info(f"Notification: [{severity}] {event} for task {task_id}: {message}")
        return notification

    async def get_notifications(self, task_id: UUID | None = None, unread_only: bool = False) -> list[Notification]:
        results = self._notifications
        if task_id:
            results = [n for n in results if n.task_id == task_id]
        if unread_only:
            results = [n for n in results if not n.read]
        return results

    async def mark_read(self, notification_id: int) -> bool:
        if 0 <= notification_id < len(self._notifications):
            self._notifications[notification_id].read = True
            return True
        return False

    async def escalate_with_notification(self, task_id: UUID, reason: str, severity: str = "high"):
        await self.notify(task_id, "escalation", f"Task escalated: {reason}", severity)
        priority = {"high": 1, "medium": 2, "low": 3}.get(severity, 2)
        return {"task_id": str(task_id), "reason": reason, "severity": severity, "priority": priority}


_notification_service = NotificationService()


def get_notification_service() -> NotificationService:
    return _notification_service
