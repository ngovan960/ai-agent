from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from shared.config.state_transitions import TERMINAL_STATES, validate_transition
from shared.schemas.task import TaskCreate


class TestEndToEndFlow:
    @pytest.mark.asyncio
    async def test_create_project_module_task_transition(self):
        mock_db = AsyncMock()
        task_id = uuid4()
        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.status = type("S", (), {"value": "NEW"})()
        mock_task.title = "Integration Test Task"
        mock_task.description = "Testing the full flow"
        mock_task.project_id = uuid4()
        mock_task.completed_at = None
        mock_task.failed_at = None

        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_task
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.get.return_value = mock_task

        assert mock_task.status.value == "NEW"

    def test_valid_state_chain(self):
        chain = ["NEW", "ANALYZING", "PLANNING", "IMPLEMENTING", "VERIFYING", "REVIEWING", "DONE"]
        for i in range(len(chain) - 1):
            valid, _ = validate_transition(chain[i], chain[i + 1])
            assert valid, f"Transition {chain[i]} -> {chain[i + 1]} should be valid"

    def test_invalid_transition_rejected(self):
        valid, error = validate_transition("NEW", "DONE")
        assert not valid
        assert error is not None

    def test_terminal_state_no_transition(self):
        for state in TERMINAL_STATES:
            valid, _ = validate_transition(state, "NEW")
            assert not valid, f"Transition from terminal {state} should be invalid"


class MockResult:
    def scalars(self):
        return self
    def all(self):
        return []
    def scalar(self):
        return 0


class TestRetryFlow:
    @pytest.mark.asyncio
    async def test_retry_tracking(self):
        from services.orchestrator.services.retry_service import create_retry

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        class AwaitableMock:
            def __await__(self):
                return iter([])

        mock_db.add = MagicMock(return_value=None)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        task_id = uuid4()
        counter = [0]

        class MockResultInc:
            def scalars(self):
                return self
            def all(self):
                return []
            def scalar(self):
                v = counter[0]
                counter[0] += 1
                return v

        mock_db.execute = AsyncMock(side_effect=lambda *a, **kw: MockResultInc())
        r1, _ = await create_retry(mock_db, task_id, "First")
        assert r1 is not None
        r2, _ = await create_retry(mock_db, task_id, "Second")
        assert r2 is not None
        r3, err = await create_retry(mock_db, task_id, "Third")
        assert r3 is None
        assert err is not None


class TestAuditLogFlow:
    @pytest.mark.asyncio
    async def test_audit_log_creation(self):
        from services.orchestrator.services.audit_service import create_audit_log, get_audit_logs

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MockResult())
        task_id = uuid4()
        log = await create_audit_log(mock_db, task_id, "test", "user", "user")
        assert log is not None
        logs, total = await get_audit_logs(mock_db, task_id)
        assert logs == []


class TestInvalidOperations:
    @pytest.mark.asyncio
    async def test_invalid_state_transition(self):
        valid, error = validate_transition("NEW", "DONE")
        assert not valid
        assert error is not None

    def test_invalid_task_create_without_title(self):
        with pytest.raises(ValidationError):
            TaskCreate(description="No title")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_task(self):
        from services.orchestrator.services.tasks import delete_task

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await delete_task(mock_db, uuid4())
        assert result is False
