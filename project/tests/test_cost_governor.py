"""Tests for Cost Governor (Phase 5.3)."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from services.orchestrator.services.cost_governor import (
    MODEL_TIERS,
    CostGovernor,
)


@pytest.fixture
def mock_db():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def governor(mock_db):
    return CostGovernor(db_session=mock_db)


@pytest.fixture
def governor_no_db():
    return CostGovernor(db_session=None)


class TestTokenTracking:
    @pytest.mark.asyncio
    async def test_track_tokens(self, governor):
        usage = await governor.track_tokens(
            task_id=uuid4(),
            model="deepseek_v4_flash",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.005,
            latency_ms=150,
            agent_name="gatekeeper",
        )
        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500
        assert usage.total_tokens == 1500
        assert governor._db.add.called

    @pytest.mark.asyncio
    async def test_track_tokens_no_db(self, governor_no_db):
        usage = await governor_no_db.track_tokens(
            task_id=uuid4(),
            model="qwen_3_5_plus",
            input_tokens=2000,
            output_tokens=1000,
        )
        assert usage.total_tokens == 3000


class TestMentorCallTracking:
    @pytest.mark.asyncio
    async def test_track_mentor_call(self, governor):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        governor._db.execute.return_value = mock_result

        record = await governor.track_mentor_call()
        assert record.calls_used == 1
        assert record.calls_limit == 10
        assert record.can_call is True

    @pytest.mark.asyncio
    async def test_track_mentor_call_no_db(self, governor_no_db):
        record = await governor_no_db.track_mentor_call()
        assert record.calls_used == 1
        assert record.calls_limit == 10
        assert record.can_call is True


class TestRetryLoopDetection:
    @pytest.mark.asyncio
    async def test_no_loop(self, governor):
        task_id = uuid4()
        info = await governor.track_retry_loop(task_id, retry_count=1)
        assert info.is_loop is False
        assert info.retry_count == 1

    @pytest.mark.asyncio
    async def test_loop_detected(self, governor):
        task_id = uuid4()
        info = await governor.track_retry_loop(task_id, retry_count=3)
        assert info.is_loop is True
        assert "infinite loop" in info.message.lower()

    @pytest.mark.asyncio
    async def test_boundary(self, governor):
        task_id = uuid4()
        info = await governor.track_retry_loop(task_id, retry_count=2)
        assert info.is_loop is False


class TestMentorLimit:
    @pytest.mark.asyncio
    async def test_within_limit(self, governor):
        mock_quota = MagicMock()
        mock_quota.calls_used = 5
        mock_quota.calls_limit = 10
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_quota
        governor._db.execute.return_value = mock_result

        result = await governor.check_mentor_limit()
        assert result is True

    @pytest.mark.asyncio
    async def test_exceeded_limit(self, governor):
        mock_quota = MagicMock()
        mock_quota.calls_used = 10
        mock_quota.calls_limit = 10
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_quota
        governor._db.execute.return_value = mock_result

        result = await governor.check_mentor_limit()
        assert result is False

    @pytest.mark.asyncio
    async def test_no_quota_record(self, governor):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        governor._db.execute.return_value = mock_result

        result = await governor.check_mentor_limit()
        assert result is True

    @pytest.mark.asyncio
    async def test_no_db(self, governor_no_db):
        result = await governor_no_db.check_mentor_limit()
        assert result is True


class TestCostAlerts:
    @pytest.mark.asyncio
    async def test_no_alerts_under_threshold(self, governor):
        mock_result_daily = MagicMock()
        mock_result_daily.scalar.return_value = 10.0
        mock_result_weekly = MagicMock()
        mock_result_weekly.scalar.return_value = 50.0
        governor._db.execute = AsyncMock(side_effect=[mock_result_daily, mock_result_weekly])

        alerts = await governor.check_cost_alerts()
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_daily_alert(self, governor):
        mock_result_daily = MagicMock()
        mock_result_daily.scalar.return_value = 100.0
        mock_result_weekly = MagicMock()
        mock_result_weekly.scalar.return_value = 50.0
        governor._db.execute = AsyncMock(side_effect=[mock_result_daily, mock_result_weekly])

        alerts = await governor.check_cost_alerts(daily_threshold=50.0)
        assert len(alerts) == 1
        assert alerts[0].period == "daily"
        assert alerts[0].exceeded is True

    @pytest.mark.asyncio
    async def test_weekly_alert(self, governor):
        mock_result_daily = MagicMock()
        mock_result_daily.scalar.return_value = 10.0
        mock_result_weekly = MagicMock()
        mock_result_weekly.scalar.return_value = 300.0
        governor._db.execute = AsyncMock(side_effect=[mock_result_daily, mock_result_weekly])

        alerts = await governor.check_cost_alerts(weekly_threshold=200.0)
        assert len(alerts) == 1
        assert alerts[0].period == "weekly"
        assert alerts[0].exceeded is True

    @pytest.mark.asyncio
    async def test_no_db(self, governor_no_db):
        alerts = await governor_no_db.check_cost_alerts()
        assert len(alerts) == 0


class TestCostGovernance:
    @pytest.mark.asyncio
    async def test_low_complexity(self, governor):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        governor._db.execute = AsyncMock(return_value=mock_result)

        result = await governor.apply_cost_governance(task_complexity="low")
        assert result.recommended_model in MODEL_TIERS["flash"]
        assert "flash" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_medium_complexity(self, governor):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        governor._db.execute = AsyncMock(return_value=mock_result)

        result = await governor.apply_cost_governance(task_complexity="medium")
        assert result.recommended_model in MODEL_TIERS["pro"]
        assert "pro" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_high_complexity_within_quota(self, governor):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        governor._db.execute = AsyncMock(return_value=mock_result)

        result = await governor.apply_cost_governance(task_complexity="high")
        assert result.recommended_model in MODEL_TIERS["mentor"]
        assert result.within_quota is True

    @pytest.mark.asyncio
    async def test_unknown_complexity(self, governor):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        governor._db.execute = AsyncMock(return_value=mock_result)

        result = await governor.apply_cost_governance(task_complexity="unknown")
        assert result.recommended_model in MODEL_TIERS["pro"]
