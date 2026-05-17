from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from services.orchestrator.services.audit_service import create_audit_log, get_audit_logs


class MockResult:
    def scalars(self):
        return self
    def all(self):
        return []
    def scalar(self):
        return 0


class TestAuditService:
    @pytest.mark.asyncio
    async def test_create_audit_log(self):
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()
        log = await create_audit_log(mock_db, uuid4(), "test_action", "tester", "user")
        assert log is not None

    @pytest.mark.asyncio
    async def test_get_audit_logs(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MockResult())
        items, total = await get_audit_logs(mock_db)
        assert items == []

    @pytest.mark.asyncio
    async def test_get_audit_logs_with_task(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MockResult())
        items, total = await get_audit_logs(mock_db, uuid4())
        assert items == []
