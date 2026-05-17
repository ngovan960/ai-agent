"""Integration tests for Memory System (Phase 6.4)."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from services.memory import ledger
from services.memory.cache_service import get_cache_stats
from services.memory.decision_service import store_decision
from services.memory.embedding_service import generate_embedding, retrieve_memory
from services.memory.integration import (
    gatekeeper_memory_lookup,
    orchestrator_memory_lookup,
    quality_check_memory,
    specialist_memory_lookup,
    update_memory_after_task,
)


def _make_mock_db():
    db = AsyncMock()
    empty_result = MagicMock()
    empty_result.scalar.return_value = 0
    empty_result.scalars.return_value.all.return_value = []
    empty_result.fetchall.return_value = []
    empty_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=empty_result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


class TestMemoryIntegration:
    """6.4.6 — Integration test: memory system end-to-end."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_instruction(self):
        db = _make_mock_db()
        task_id = uuid4()
        inst = await ledger.store_mentor_advice(
            db, task_id, "Use Pydantic for all API input validation",
            {"risk": "high", "file": "routes.py"},
        )
        assert inst.instruction_type.value == "advice"
        assert "Pydantic" in inst.content

    @pytest.mark.asyncio
    async def test_store_and_retrieve_decision(self):
        db = _make_mock_db()
        project_id = uuid4()
        dec = await store_decision(
            db, project_id, "Use PostgreSQL for ACID", "Need ACID compliance",
            alternatives=[{"name": "MySQL", "reason": "familiarity"}],
        )
        assert dec.decision == "Use PostgreSQL for ACID"
        assert dec.project_id == project_id

    @pytest.mark.asyncio
    async def test_similarity_filter(self):
        from services.memory.embedding_service import filter_by_similarity
        results = [
            {"content": "Pydantic validation for APIs", "similarity": 0.85},
            {"content": "Random unrelated note", "similarity": 0.45},
            {"content": "PostgreSQL connection pooling", "similarity": 0.72},
        ]
        filtered = await filter_by_similarity(results, threshold=0.7)
        assert len(filtered) == 2
        assert filtered[0]["similarity"] > filtered[1]["similarity"]

    def test_cache_stats_reset(self):
        from services.memory.cache_service import reset_cache_stats
        reset_cache_stats()
        stats = get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    @pytest.mark.asyncio
    async def test_embedding_deterministic(self):
        emb1 = await generate_embedding("test query")
        emb2 = await generate_embedding("test query")
        assert emb1 == emb2

    @pytest.mark.asyncio
    async def test_different_texts_different_embeddings(self):
        emb1 = await generate_embedding("hello world")
        emb2 = await generate_embedding("something completely different")
        assert emb1 != emb2

    @pytest.mark.asyncio
    async def test_store_failed_pattern_and_decision(self):
        db = _make_mock_db()
        task_id = uuid4()
        pattern = await ledger.store_failed_pattern(
            db, task_id,
            "Using raw SQL in API routes",
            "SQL injection vulnerability detected",
            {"file": "routes.py", "line": 42},
        )
        assert pattern.instruction_type.value == "warning"
        assert "FAILED" in pattern.content

        dec = await store_decision(
            db, uuid4(), "Use ORM instead of raw SQL",
            "Eliminate SQL injection risk",
            task_id=task_id,
        )
        assert dec.reason == "Eliminate SQL injection risk"

    @pytest.mark.asyncio
    async def test_keyword_search_fallback(self):
        db = _make_mock_db()
        results = await retrieve_memory(db, "test query", top_k=5, threshold=0.0)
        assert isinstance(results, list)


class TestMemoryIntegrationService:
    """Tests for 6.4.1-6.4.5 memory integration functions."""

    @pytest.mark.asyncio
    async def test_gatekeeper_lookup_empty(self):
        db = _make_mock_db()
        results = await gatekeeper_memory_lookup(db, "test task", top_k=3)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_orchestrator_lookup_empty(self):
        db = _make_mock_db()
        results = await orchestrator_memory_lookup(db, "test spec", top_k=5)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_specialist_lookup_empty(self):
        db = _make_mock_db()
        results = await specialist_memory_lookup(db, "test coding task", top_k=3)
        assert isinstance(results, list)

    def test_quality_check_rejects_short(self):
        assert quality_check_memory({"content": "short"}) is False

    def test_quality_check_rejects_placeholder(self):
        assert quality_check_memory({"content": "todo fix this later"}) is False

    def test_quality_check_accepts_good(self):
        assert quality_check_memory({"content": "Always validate input using Pydantic schemas"}) is True

    @pytest.mark.asyncio
    async def test_update_memory_after_task_empty(self):
        db = _make_mock_db()
        task_id = uuid4()
        counts = await update_memory_after_task(db, task_id, project_id=uuid4(), logs=[])
        assert counts["lessons"] == 0
        assert counts["decisions"] == 0
        assert counts["patterns"] == 0

    @pytest.mark.asyncio
    async def test_update_memory_with_lessons(self):
        db = _make_mock_db()
        task_id = uuid4()
        logs = [
            {"content": "Use Pydantic for input validation", "type": "lesson", "context": {"file": "routes.py"}},
            {"content": "Set connection pool size to 10", "type": "lesson"},
        ]
        counts = await update_memory_after_task(db, task_id, project_id=uuid4(), logs=logs)
        assert counts["lessons"] == 2
        assert counts["rejected"] == 0

    @pytest.mark.asyncio
    async def test_update_memory_with_decision(self):
        db = _make_mock_db()
        task_id = uuid4()
        project_id = uuid4()
        logs = [
            {"content": "Use PostgreSQL over MySQL for ACID", "type": "decision",
             "reason": "Need ACID compliance", "project_id": project_id,
             "context": {"team": "backend"}, "alternatives": [{"name": "MySQL"}]},
        ]
        counts = await update_memory_after_task(db, task_id, project_id=project_id, logs=logs)
        assert counts["decisions"] == 1
        assert counts["rejected"] == 0

    @pytest.mark.asyncio
    async def test_update_memory_with_pattern(self):
        db = _make_mock_db()
        task_id = uuid4()
        logs = [
            {"content": "Avoid using raw SQL in routes", "type": "pattern",
             "context": {"file": "routes.py"}},
        ]
        counts = await update_memory_after_task(db, task_id, project_id=uuid4(), logs=logs)
        assert counts["patterns"] == 1
        assert counts["rejected"] == 0

    @pytest.mark.asyncio
    async def test_update_memory_deduplicates_decisions(self):
        db = _make_mock_db()
        task_id = uuid4()
        project_id = uuid4()
        logs = [
            {"content": "Use PostgreSQL over MySQL for ACID", "type": "decision",
             "reason": "ACID compliance", "project_id": project_id},
            {"content": "Use PostgreSQL over MySQL for ACID", "type": "decision",
             "reason": "ACID compliance", "project_id": project_id},
        ]
        counts = await update_memory_after_task(db, task_id, project_id=project_id, logs=logs)
        assert counts["decisions"] == 1
        assert counts["rejected"] == 0
