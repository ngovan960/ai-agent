import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    DASHBOARD = "dashboard"
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"


class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationType(str, Enum):
    BLOCKED_TASK = "blocked_task"
    BLOCKED_TIMEOUT = "blocked_timeout"
    BLOCKED_ESCALATED = "blocked_escalated"
    STUCK_TASK = "stuck_task"
    CONTEXT_OVERFLOW = "context_overflow"
    COST_ALERT = "cost_alert"
    VALIDATION_FAILED = "validation_failed"


class Notification:
    """Represents a notification to be sent to users."""

    def __init__(
        self,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        channels: list[NotificationChannel] | None = None,
        task_id: UUID | None = None,
        project_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.id = UUID.__hash__(self)
        self.type = notification_type
        self.title = title
        self.message = message
        self.priority = priority
        self.channels = channels or [NotificationChannel.DASHBOARD]
        self.task_id = task_id
        self.project_id = project_id
        self.metadata = metadata or {}
        self.created_at = datetime.now(timezone.utc)
        self.sent = False
        self.sent_at: datetime | None = None


def create_blocked_notification(
    task_id: UUID,
    project_id: UUID,
    task_title: str,
    reason: str,
    missing_info: list[str] | None = None,
) -> Notification:
    """Create notification when task enters BLOCKED state."""
    channels = [NotificationChannel.DASHBOARD]
    priority = NotificationPriority.MEDIUM

    missing_info_text = ""
    if missing_info:
        missing_info_text = "\n\nMissing information:\n" + "\n".join(
            f"  - {info}" for info in missing_info
        )

    return Notification(
        notification_type=NotificationType.BLOCKED_TASK,
        title=f"Task Blocked: {task_title}",
        message=(
            f"Task '{task_title}' has been blocked.\n"
            f"Reason: {reason}"
            f"{missing_info_text}\n\n"
            f"Please provide the missing information or cancel the task."
        ),
        priority=priority,
        channels=channels,
        task_id=task_id,
        project_id=project_id,
        metadata={
            "missing_info": missing_info or [],
            "action_required": True,
        },
    )


def create_blocked_timeout_notification(
    task_id: UUID,
    project_id: UUID,
    task_title: str,
    minutes_blocked: int,
    timeout_minutes: int = 120,
) -> Notification:
    """Create notification when BLOCKED task exceeds timeout."""
    return Notification(
        notification_type=NotificationType.BLOCKED_TIMEOUT,
        title=f"Task Blocked Too Long: {task_title}",
        message=(
            f"Task '{task_title}' has been BLOCKED for {minutes_blocked} minutes "
            f"(timeout: {timeout_minutes} minutes).\n\n"
            f"If no action is taken, this task will be auto-escalated to Mentor."
        ),
        priority=NotificationPriority.HIGH,
        channels=[NotificationChannel.DASHBOARD, NotificationChannel.SLACK],
        task_id=task_id,
        project_id=project_id,
        metadata={
            "minutes_blocked": minutes_blocked,
            "timeout_minutes": timeout_minutes,
            "action_required": True,
        },
    )


def create_blocked_escalated_notification(
    task_id: UUID,
    project_id: UUID,
    task_title: str,
    minutes_blocked: int,
) -> Notification:
    """Create notification when BLOCKED task is auto-escalated."""
    return Notification(
        notification_type=NotificationType.BLOCKED_ESCALATED,
        title=f"Task Auto-Escalated: {task_title}",
        message=(
            f"Task '{task_title}' has been auto-escalated to Mentor "
            f"after being BLOCKED for {minutes_blocked} minutes.\n\n"
            f"Mentor will review and decide next action."
        ),
        priority=NotificationPriority.CRITICAL,
        channels=[NotificationChannel.DASHBOARD, NotificationChannel.SLACK, NotificationChannel.EMAIL],
        task_id=task_id,
        project_id=project_id,
        metadata={
            "minutes_blocked": minutes_blocked,
            "action": "auto_escalated_to_mentor",
        },
    )


class NotificationService:
    """
    Service for sending notifications through various channels.

    In production, this would integrate with:
    - WebSocket for dashboard notifications
    - Slack API for Slack notifications
    - SMTP/SendGrid for email notifications
    - Webhook endpoints for custom integrations
    """

    def __init__(self):
        self.sent_notifications: list[Notification] = []

    async def send(self, notification: Notification) -> bool:
        """Send notification through specified channels."""
        try:
            for channel in notification.channels:
                await self._send_to_channel(channel, notification)

            notification.sent = True
            notification.sent_at = datetime.now(timezone.utc)
            self.sent_notifications.append(notification)

            logger.info(
                f"Notification sent: {notification.type.value} - {notification.title}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    async def _send_to_channel(
        self, channel: NotificationChannel, notification: Notification
    ) -> None:
        """Send notification to specific channel."""
        if channel == NotificationChannel.DASHBOARD:
            await self._send_dashboard(notification)
        elif channel == NotificationChannel.SLACK:
            await self._send_slack(notification)
        elif channel == NotificationChannel.EMAIL:
            await self._send_email(notification)
        elif channel == NotificationChannel.WEBHOOK:
            await self._send_webhook(notification)

    async def _send_dashboard(self, notification: Notification) -> None:
        """Send via WebSocket to dashboard."""
        logger.debug(f"Dashboard notification: {notification.title}")

    async def _send_slack(self, notification: Notification) -> None:
        """Send via Slack API."""
        logger.debug(f"Slack notification: {notification.title}")

    async def _send_email(self, notification: Notification) -> None:
        """Send via email."""
        logger.debug(f"Email notification: {notification.title}")

    async def _send_webhook(self, notification: Notification) -> None:
        """Send via webhook."""
        logger.debug(f"Webhook notification: {notification.title}")


notification_service = NotificationService()
