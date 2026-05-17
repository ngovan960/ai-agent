from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from services.orchestrator.services.context_builder import (
    _estimate_tokens,
    build_context,
    load_laws_context,
    load_memory_context,
    trim_context,
)


class TestContextBuilder:
    @pytest.mark.asyncio
    async def test_build_context_task_not_found(self):
        mock_db = AsyncMock()
        mock_db.get.return_value = None
        result = await build_context(mock_db, uuid4())
        assert "error" in result

    @pytest.mark.asyncio
    async def test_build_context_has_task(self):
        mock_task = AsyncMock()
        mock_task.id = uuid4()
        mock_task.title = "Test"
        mock_task.description = "Desc"
        mock_task.expected_output = "Output"
        mock_task.module_id = None
        mock_task.status = type("E", (), {"value": "NEW"})()
        mock_task.priority = type("E", (), {"value": "MEDIUM"})()
        mock_task.risk_level = type("E", (), {"value": "LOW"})()
        mock_db = AsyncMock()
        mock_db.get.return_value = mock_task
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        result = await build_context(mock_db, mock_task.id)
        assert "task" in result
        assert result["task"]["title"] == "Test"
        assert "memory" in result
        assert "laws" in result

    def test_estimate_tokens(self):
        assert _estimate_tokens("hello world") > 0
        assert _estimate_tokens("") == 0

    def test_trim_context(self):
        ctx = {"task": {"title": "test"}, "module": {"name": "mod"}}
        trimmed = trim_context(ctx, 10000)
        assert "task" in trimmed

    def test_trim_context_small_limit(self):
        ctx = {"task": {"title": "x" * 1000}, "module": {"name": "y" * 1000}}
        trimmed = trim_context(ctx, 100)
        assert len(trimmed) <= 2

    @pytest.mark.asyncio
    async def test_load_memory_context(self):
        mock_db = AsyncMock()
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        result = await load_memory_context(mock_db, "test spec")
        assert "recent_completed_tasks" in result

    def test_load_laws_context(self):
        result = load_laws_context()
        assert isinstance(result, dict)
