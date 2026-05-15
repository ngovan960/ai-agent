import pytest
from unittest.mock import AsyncMock, MagicMock
from shared.schemas.retry_audit import RetryCreate, RetryReason, AuditLogCreate, AuditLogQuery
from shared.models.registry import Retry, AuditLog
from services.orchestrator.services.retry_audit_service import RetryService, AuditService, MAX_RETRIES_PER_TASK


class TestRetryService:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()
        return db

    @pytest.mark.asyncio
    async def test_create_retry_first_attempt(self, mock_db):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        service = RetryService(mock_db)
        data = RetryCreate(
            task_id="00000000-0000-0000-0000-000000000001",
            reason=RetryReason.LLM_TIMEOUT,
            agent_name="coder",
        )
        retry = await service.create_retry(data)

        assert retry.attempt_number == 1
        assert retry.reason == "llm_timeout"
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_retry_max_exceeded(self, mock_db):
        mock_result = MagicMock()
        mock_result.scalar.return_value = MAX_RETRIES_PER_TASK
        mock_db.execute.return_value = mock_result

        service = RetryService(mock_db)
        data = RetryCreate(
            task_id="00000000-0000-0000-0000-000000000001",
            reason=RetryReason.LLM_ERROR,
            agent_name="coder",
        )

        with pytest.raises(ValueError, match="Max retries"):
            await service.create_retry(data)

    @pytest.mark.asyncio
    async def test_get_retry_stats_empty(self, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        service = RetryService(mock_db)
        stats = await service.get_retry_stats("00000000-0000-0000-0000-000000000001")

        assert stats["total_retries"] == 0
        assert stats["max_retries_exceeded"] is False

    @pytest.mark.asyncio
    async def test_can_retry_true(self, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock()] * 2
        mock_db.execute.return_value = mock_result

        service = RetryService(mock_db)
        can = await service.can_retry("00000000-0000-0000-0000-000000000001")
        assert can is True

    @pytest.mark.asyncio
    async def test_can_retry_false(self, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock()] * MAX_RETRIES_PER_TASK
        mock_db.execute.return_value = mock_result

        service = RetryService(mock_db)
        can = await service.can_retry("00000000-0000-0000-0000-000000000001")
        assert can is False


class TestAuditService:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()
        return db

    @pytest.mark.asyncio
    async def test_create_audit_log(self, mock_db):
        service = AuditService(mock_db)
        data = AuditLogCreate(
            action="state_transition",
            actor="orchestrator",
            result="SUCCESS",
        )
        audit = await service.create_audit_log(data)

        assert audit.action == "state_transition"
        assert audit.result == "SUCCESS"
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_audit_logs_no_filters(self, mock_db):
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = []
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        service = AuditService(mock_db)
        query = AuditLogQuery()
        logs, total = await service.query_audit_logs(query)

        assert logs == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_export_csv(self, mock_db):
        mock_log = MagicMock()
        mock_log.id = "1"
        mock_log.task_id = None
        mock_log.action = "test"
        mock_log.actor = "system"
        mock_log.actor_type = "agent"
        mock_log.result = "SUCCESS"
        mock_log.message = "Test message"
        mock_log.created_at = "2026-05-15T00:00:00"

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [mock_log]
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        service = AuditService(mock_db)
        query = AuditLogQuery()
        csv = await service.export_audit_logs_csv(query)

        assert "id,task_id,action,actor,actor_type,result,message,created_at" in csv
        assert "test" in csv
