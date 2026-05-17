from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from services.orchestrator.services.agent_runtime import AgentRuntime, EscalationRecord, TakeoverRecord


class TestMentorAgent:
    @pytest.mark.asyncio
    async def test_escalate_task(self):
        mock_db = AsyncMock()
        mock_router = MagicMock()
        runtime = AgentRuntime(mock_db, mock_router)
        record = await runtime.escalate_task(uuid4(), "Deadlock detected", "high")
        assert isinstance(record, EscalationRecord)
        assert record.reason == "Deadlock detected"

    @pytest.mark.asyncio
    async def test_takeover_creates_record(self):
        mock_db = AsyncMock()
        mock_router = MagicMock()
        runtime = AgentRuntime(mock_db, mock_router)
        record = await runtime.takeover(uuid4(), uuid4(), "rewrite", "Code quality too low")
        assert isinstance(record, TakeoverRecord)
        assert record.action == "rewrite"

    @pytest.mark.asyncio
    async def test_takeover_record_fields(self):
        mock_db = AsyncMock()
        mock_router = MagicMock()
        runtime = AgentRuntime(mock_db, mock_router)
        task_id = uuid4()
        mentor_id = uuid4()
        record = await runtime.takeover(task_id, mentor_id, "redesign", "Architecture issue")
        assert record.task_id == task_id
        assert record.mentor_id == mentor_id
        assert record.action == "redesign"
        assert record.created_at is not None

    @pytest.mark.asyncio
    async def test_escalate_record_fields(self):
        mock_db = AsyncMock()
        mock_router = MagicMock()
        runtime = AgentRuntime(mock_db, mock_router)
        record = await runtime.escalate_task(uuid4(), "Test escalation", "critical")
        assert record.severity == "critical"
        assert record.target_state == "ESCALATED"
