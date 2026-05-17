from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from services.orchestrator.services.retry_service import MAX_RETRIES, create_retry, get_retries, should_escalate


class MockResult:
    def scalars(self):
        return self
    def all(self):
        return []
    def scalar(self):
        return 0


class TestRetryService:
    @pytest.mark.asyncio
    async def test_create_retry(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MockResult())
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()
        record, error = await create_retry(mock_db, uuid4(), "Test fail")
        assert record is not None
        assert error is None

    @pytest.mark.asyncio
    async def test_create_retry_exceeds_limit(self):
        mock_db = AsyncMock()

        class MockResultHigh:
            def scalars(self):
                return self
            def all(self):
                return []
            def scalar(self):
                return MAX_RETRIES + 1

        mock_db.execute = AsyncMock(return_value=MockResultHigh())
        record, error = await create_retry(mock_db, uuid4(), "Too many")
        assert record is None
        assert error is not None

    @pytest.mark.asyncio
    async def test_should_escalate_false(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MockResult())
        assert await should_escalate(mock_db, uuid4()) is False

    @pytest.mark.asyncio
    async def test_should_escalate_true(self):
        class MockResultHigh:
            def scalars(self):
                return self
            def all(self):
                return []
            def scalar(self):
                return MAX_RETRIES

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MockResultHigh())
        assert await should_escalate(mock_db, uuid4()) is True

    @pytest.mark.asyncio
    async def test_get_retries(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MockResult())
        items, total = await get_retries(mock_db, uuid4())
        assert items == []
