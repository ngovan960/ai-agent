"""Tests for Decision Service (Phase 6.3)."""

from datetime import UTC
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from services.memory import decision_service


def _make_mock_db():
    db = AsyncMock()
    empty_result = MagicMock()
    empty_result.scalar.return_value = 0
    empty_result.scalars.return_value.all.return_value = []
    empty_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=empty_result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _make_mock_db_with_decision():
    mock_decision = MagicMock()
    mock_decision.task_id = None
    mock_decision.context = {}
    mock_decision.decision = "Test decision"
    mock_decision.reason = "Test reason"
    mock_decision.project_id = uuid4()
    mock_decision.alternatives = []

    db = AsyncMock()
    result = MagicMock()
    result.scalar.return_value = 1
    result.scalars.return_value.all.return_value = [mock_decision]
    result.scalar_one_or_none.return_value = mock_decision
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db, mock_decision


class TestStoreDecision:
    @pytest.mark.asyncio
    async def test_store_decision(self):
        db = _make_mock_db()
        dec = await decision_service.store_decision(
            db, uuid4(), "Use microservices", "Need scalability",
            task_id=uuid4(), context={"team": "platform"},
            alternatives=[{"name": "monolith", "reason": "simpler"}],
        )
        assert dec.decision == "Use microservices"
        assert dec.reason == "Need scalability"

    @pytest.mark.asyncio
    async def test_store_decision_minimal(self):
        db = _make_mock_db()
        dec = await decision_service.store_decision(
            db, uuid4(), "Test decision", "Test reason",
        )
        assert dec.alternatives == []


class TestGetDecisions:
    @pytest.mark.asyncio
    async def test_get_decisions_empty(self):
        db = _make_mock_db()
        items, total = await decision_service.get_decisions(db)
        assert total == 0
        assert len(items) == 0

    @pytest.mark.asyncio
    async def test_get_decisions_by_project(self):
        db = _make_mock_db()
        project_id = uuid4()
        items, total = await decision_service.get_decisions(db, project_id=project_id)
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_decisions_pagination(self):
        db, mock_decision = _make_mock_db_with_decision()
        items, total = await decision_service.get_decisions(db, page=1, page_size=10)
        assert total == 1
        assert len(items) == 1

    @pytest.mark.asyncio
    async def test_get_decisions_page_out_of_range(self):
        db = _make_mock_db()
        items, total = await decision_service.get_decisions(db, page=100, page_size=10)
        assert total == 0
        assert len(items) == 0

    @pytest.mark.asyncio
    async def test_get_decisions_filter_by_task(self):
        db = _make_mock_db()
        task_id = uuid4()
        items, total = await decision_service.get_decisions(db, task_id=task_id)
        assert total == 0
        assert len(items) == 0


class TestDecisionToResponse:
    def test_decision_to_response(self):
        from datetime import datetime

        from shared.models.registry import Decision

        dec = Decision(
            id=uuid4(), project_id=uuid4(), task_id=uuid4(),
            decision="Use PostgreSQL", reason="ACID",
            context={"team": "platform"}, alternatives=[{"name": "MySQL"}],
            decided_by="mentor",
            created_at=datetime.now(UTC),
        )
        resp = decision_service.decision_to_response(dec)
        assert resp["decision"] == "Use PostgreSQL"
        assert resp["reason"] == "ACID"
        assert resp["decided_by"] == "mentor"
        assert resp["context"]["team"] == "platform"


class TestLinkDecision:
    @pytest.mark.asyncio
    async def test_link_decision_to_task(self):
        db, mock_decision = _make_mock_db_with_decision()
        decision_id = uuid4()
        task_id = uuid4()
        result = await decision_service.link_decision(db, decision_id, task_id)
        assert result is not None
        assert result.task_id == task_id

    @pytest.mark.asyncio
    async def test_link_nonexistent_decision(self):
        db = _make_mock_db()
        result = await decision_service.link_decision(db, uuid4(), uuid4())
        assert result is None
