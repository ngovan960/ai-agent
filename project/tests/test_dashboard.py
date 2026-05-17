"""Tests for Dashboard API (Phase 7.4)."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from services.orchestrator.routers.dashboard import (
    _cache,
    active_connections,
    broadcast,
    cost_breakdown,
    dashboard_summary,
    prometheus_metrics,
    recent_activity,
    tasks_by_status,
    websocket_endpoint,
)


def _make_mock_db():
    db = AsyncMock()
    empty = MagicMock()
    empty.scalar.return_value = 0
    empty.scalars.return_value.all.return_value = []
    empty.fetchall.return_value = []
    db.execute = AsyncMock(return_value=empty)
    return db


@pytest.mark.asyncio
async def test_dashboard_summary_empty():
    _cache.clear()
    db = _make_mock_db()
    result = await dashboard_summary(db)
    assert result["projects"] == 0
    assert result["tasks"] == 0
    assert result["active_tasks"] == 0
    assert result["instructions"] == 0
    assert result["decisions"] == 0
    assert result["total_cost"] == 0.0


@pytest.mark.asyncio
async def test_dashboard_summary_with_data():
    _cache.clear()
    db = AsyncMock()
    results = {"projects": 3, "tasks": 10, "active": 2, "instructions": 5, "decisions": 4, "cost": 12.5}
    call_count = [0]

    async def side_effect(*args, **kwargs):
        call_count[0] += 1
        r = MagicMock()
        vals = [results["projects"], results["tasks"], results["active"],
                results["instructions"], results["decisions"], results["cost"]]
        r.scalar.return_value = vals[call_count[0] - 1] if call_count[0] <= len(vals) else 0
        return r

    db.execute = AsyncMock(side_effect=side_effect)
    result = await dashboard_summary(db)
    assert result["projects"] == 3
    assert result["tasks"] == 10
    assert result["active_tasks"] == 2
    assert result["instructions"] == 5
    assert result["decisions"] == 4
    assert result["total_cost"] == 12.5


@pytest.mark.asyncio
async def test_tasks_by_status_empty():
    db = _make_mock_db()
    result = await tasks_by_status(db)
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_cost_breakdown_empty():
    db = _make_mock_db()
    result = await cost_breakdown(db)
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_recent_activity_empty():
    db = _make_mock_db()
    result = await recent_activity(limit=5, db=db)
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_recent_activity_with_logs():
    mock_log = MagicMock()
    mock_log.id = uuid4()
    mock_log.action = "test_action"
    mock_log.actor = "test_actor"
    mock_log.result = "SUCCESS"
    mock_log.message = "test message"
    mock_log.created_at = None

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [mock_log]
    db.execute = AsyncMock(return_value=result_mock)

    result = await recent_activity(limit=10, db=db)
    assert len(result) == 1
    assert result[0]["action"] == "test_action"
    assert result[0]["actor"] == "test_actor"


@pytest.mark.asyncio
async def test_recent_activity_enum_serialization():
    class FakeEnum:
        value = "SUCCESS"

    mock_log = MagicMock()
    mock_log.result = FakeEnum()
    mock_log.id = uuid4()
    mock_log.action = "test"
    mock_log.actor = "test"
    mock_log.message = "test"
    mock_log.created_at = None

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [mock_log]
    db.execute = AsyncMock(return_value=result_mock)

    result = await recent_activity(limit=5, db=db)
    assert result[0]["result"] == "SUCCESS"


@pytest.mark.asyncio
async def test_broadcast_to_active_connections():
    mock_ws = AsyncMock()
    active_connections.append(mock_ws)
    try:
        await broadcast({"type": "test", "data": "hello"})
        mock_ws.send_json.assert_called_once_with({"type": "test", "data": "hello"})
    finally:
        active_connections.clear()


@pytest.mark.asyncio
async def test_broadcast_handles_disconnected():
    mock_ws = AsyncMock()
    mock_ws.send_json.side_effect = Exception("disconnected")
    active_connections.append(mock_ws)
    try:
        await broadcast({"type": "test"})
        assert len(active_connections) == 0
    finally:
        active_connections.clear()


@pytest.mark.asyncio
async def test_broadcast_multiple_connections():
    ws1, ws2 = AsyncMock(), AsyncMock()
    ws2.send_json.side_effect = Exception("gone")
    active_connections.extend([ws1, ws2])
    try:
        await broadcast({"type": "update"})
        ws1.send_json.assert_called_once()
        assert len(active_connections) == 1
    finally:
        active_connections.clear()


@pytest.mark.asyncio
async def test_websocket_endpoint_connect_and_disconnect():
    mock_ws = AsyncMock()
    mock_ws.receive_text.side_effect = ['{"type": "test"}', Exception("disconnect")]
    await websocket_endpoint(mock_ws)
    mock_ws.accept.assert_called_once()
    mock_ws.send_json.assert_called_once_with({"type": "ack", "data": {"type": "test"}})
    assert mock_ws not in active_connections


@pytest.mark.asyncio
async def test_websocket_endpoint_invalid_json():
    mock_ws = AsyncMock()
    mock_ws.receive_text.side_effect = ["not-json", Exception("done")]
    await websocket_endpoint(mock_ws)
    mock_ws.accept.assert_called_once()
    mock_ws.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_prometheus_metrics_without_client():
    with patch("services.orchestrator.routers.dashboard.get_metrics") as mock_get:
        mock_get.return_value = "# metrics mock"
        result = await prometheus_metrics()
        assert result == "# metrics mock"


@pytest.mark.asyncio
async def test_tasks_by_status_serializes_enum():
    class FakeStatus:
        value = "DONE"

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.fetchall.return_value = [(FakeStatus(), 5)]
    db.execute = AsyncMock(return_value=result_mock)

    result = await tasks_by_status(db)
    assert result == [{"status": "DONE", "count": 5}]
