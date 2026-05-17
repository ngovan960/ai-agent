from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from services.orchestrator.services.devops_service import DevOpsService


class TestDevOpsAgent:
    @pytest.mark.asyncio
    async def test_create_service(self):
        mock_db = AsyncMock()
        mock_runtime = MagicMock()
        service = DevOpsService(mock_db, mock_runtime, None)
        assert service is not None

    @pytest.mark.asyncio
    async def test_execute(self):
        mock_db = AsyncMock()
        mock_runtime = MagicMock()
        mock_profile_builder = MagicMock()
        mock_profile_builder.build.return_value = MagicMock()
        mock_runtime.execute_agent = AsyncMock()
        mock_runtime.execute_agent.return_value = MagicMock()
        mock_runtime.execute_agent.return_value.error = None
        mock_runtime.execute_agent.return_value.parsed_output = {"build_result": "ok"}
        service = DevOpsService(mock_db, mock_runtime, mock_profile_builder)
        result = await service.execute(uuid4(), {"task": "test"}, {})
        assert result is not None
