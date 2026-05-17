"""Tests for Instruction Ledger (Phase 6.1)."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from services.memory import ledger


def _make_mock_db():
    db = AsyncMock()
    empty_result = MagicMock()
    empty_result.scalar.return_value = 0
    empty_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=empty_result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


class TestStoreInstruction:
    @pytest.mark.asyncio
    async def test_store_mentor_advice(self):
        db = _make_mock_db()
        inst = await ledger.store_mentor_advice(
            db, uuid4(), "Use Pydantic for validation", {"file": "routes.py"}
        )
        assert inst.instruction_type.value == "advice"

    @pytest.mark.asyncio
    async def test_store_failed_pattern(self):
        db = _make_mock_db()
        inst = await ledger.store_failed_pattern(
            db, uuid4(), "RAW SQL", "SQL injection risk", {"file": "db.py"}
        )
        assert inst.instruction_type.value == "warning"

    @pytest.mark.asyncio
    async def test_store_architecture_decision(self):
        db = _make_mock_db()
        inst = await ledger.store_architecture_decision(
            db, uuid4(), "Use PostgreSQL", "Need ACID compliance", ["MySQL"]
        )
        assert inst.instruction_type.value == "decision"
        assert "alternatives" in inst.context

    @pytest.mark.asyncio
    async def test_store_lesson_learned(self):
        db = _make_mock_db()
        inst = await ledger.store_lesson_learned(
            db, uuid4(), "Always validate input before processing", {"severity": "high"}
        )
        assert inst.instruction_type.value == "pattern"


class TestGetInstructions:
    @pytest.mark.asyncio
    async def test_get_all_instructions(self):
        db = _make_mock_db()
        items, total = await ledger.get_instructions(db)
        assert total == 0
        assert len(items) == 0


class TestInstructionResponse:
    def test_instruction_to_response(self):
        from shared.models.registry import InstructionType, MentorInstruction

        inst = MentorInstruction(
            id=uuid4(), task_id=uuid4(), instruction_type=InstructionType.ADVICE,
            content="test", context={}, applied=False,
        )
        resp = ledger.instruction_to_response(inst)
        assert resp["instruction_type"] == "advice"
        assert resp["content"] == "test"
        assert resp["applied"] is False
