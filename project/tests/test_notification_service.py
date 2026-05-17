from uuid import uuid4

import pytest

from services.orchestrator.services.notification_service import EscalationPriorityQueue, NotificationService


class TestNotificationService:
    @pytest.mark.asyncio
    async def test_create_service(self):
        svc = NotificationService()
        assert svc is not None

    @pytest.mark.asyncio
    async def test_notify(self):
        svc = NotificationService()
        n = await svc.notify(uuid4(), "test", "Test message")
        assert n.event == "test"

    @pytest.mark.asyncio
    async def test_get_notifications(self):
        svc = NotificationService()
        task_id = uuid4()
        await svc.notify(task_id, "test", "Msg 1")
        await svc.notify(task_id, "test", "Msg 2")
        notifications = await svc.get_notifications(task_id)
        assert len(notifications) == 2

    @pytest.mark.asyncio
    async def test_escalate_with_notification(self):
        svc = NotificationService()
        result = await svc.escalate_with_notification(uuid4(), "Test escalation")
        assert result["severity"] == "high"
        assert result["priority"] == 1


class TestEscalationQueue:
    @pytest.mark.asyncio
    async def test_push_and_pop(self):
        q = EscalationPriorityQueue()
        task_id = uuid4()
        await q.push(task_id, "Reason", "high")
        item = await q.pop()
        assert item is not None
        assert item["task_id"] == str(task_id)

    @pytest.mark.asyncio
    async def test_priority_order(self):
        q = EscalationPriorityQueue()
        t1, t2 = uuid4(), uuid4()
        await q.push(t1, "Low urgency", "low")
        await q.push(t2, "Critical", "critical")
        first = await q.pop()
        assert first["task_id"] == str(t2)

    @pytest.mark.asyncio
    async def test_peek(self):
        q = EscalationPriorityQueue()
        task_id = uuid4()
        await q.push(task_id, "Test", "medium")
        item = await q.peek()
        assert item is not None
        assert item["task_id"] == str(task_id)

    @pytest.mark.asyncio
    async def test_remove(self):
        q = EscalationPriorityQueue()
        task_id = uuid4()
        await q.push(task_id, "Test", "low")
        assert await q.remove(task_id) is True
        assert await q.remove(task_id) is False

    @pytest.mark.asyncio
    async def test_get_all_empty(self):
        q = EscalationPriorityQueue()
        assert await q.get_all() == []
