from unittest.mock import AsyncMock, MagicMock

import pytest

from services.orchestrator.services.monitoring_service import MonitoringService


class TestMonitoringAgent:
    @pytest.mark.asyncio
    async def test_create_service(self):
        mock_db = AsyncMock()
        mock_runtime = MagicMock()
        service = MonitoringService(mock_db, mock_runtime, None)
        assert service is not None

    @pytest.mark.asyncio
    async def test_track_errors(self):
        mock_db = AsyncMock()
        mock_runtime = MagicMock()
        service = MonitoringService(mock_db, mock_runtime, None)
        mock_db.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
        result = await service.track_errors()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_detect_anomalies(self):
        mock_db = AsyncMock()
        mock_runtime = MagicMock()
        service = MonitoringService(mock_db, mock_runtime, None)
        mock_db.execute.return_value = MagicMock(scalar=MagicMock(return_value=0))
        result = await service.detect_anomalies()
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_detect_anomalies_with_failures(self):
        mock_db = AsyncMock()
        mock_runtime = MagicMock()
        service = MonitoringService(mock_db, mock_runtime, None)

        call_count = 0
        def mock_scalar():
            nonlocal call_count
            call_count += 1
            mapping = {1: 2, 2: 1, 3: 0}
            return mapping.get(call_count, 0)

        mock_db.execute.return_value = MagicMock(scalar=mock_scalar)
        result = await service.detect_anomalies()
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["type"] == "high_failure_rate"
        assert result[1]["type"] == "blocked_tasks"

    @pytest.mark.asyncio
    async def test_generate_report(self):
        mock_db = AsyncMock()
        mock_runtime = MagicMock()
        service = MonitoringService(mock_db, mock_runtime, None)

        call_count = 0
        def mock_scalar():
            nonlocal call_count
            call_count += 1
            mapping = {1: 10, 2: 3, 3: 1, 4: 4}
            return mapping.get(call_count, 0)

        mock_db.execute.return_value = MagicMock(scalar=mock_scalar)
        result = await service.generate_report()
        assert isinstance(result, dict)
        assert "summary" in result
