"""Tests for Embedding Service (Phase 6.2)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from services.memory.embedding_service import (
    _keyword_search,
    _simple_embed,
    filter_by_similarity,
    retrieve_memory,
)


def _make_mock_db():
    db = AsyncMock()
    empty_result = MagicMock()
    empty_result.scalar.return_value = 0
    empty_result.scalars.return_value.all.return_value = []
    empty_result.fetchall.return_value = []
    db.execute = AsyncMock(return_value=empty_result)
    return db


class TestEmbeddingGeneration:
    def test_embedding_dimensions(self):
        vec = _simple_embed("Hello world test query")
        assert len(vec) == 1536

    def test_embedding_normalized(self):
        vec = _simple_embed("Same text same embedding")
        magnitude = sum(v * v for v in vec) ** 0.5
        assert abs(magnitude - 1.0) < 0.001

    def test_empty_text(self):
        vec = _simple_embed("")
        assert len(vec) == 1536
        assert all(v == 0.0 for v in vec)

    def test_deterministic(self):
        vec1 = _simple_embed("Hello world")
        vec2 = _simple_embed("Hello world")
        assert vec1 == vec2


class TestSemanticSearch:
    @pytest.mark.asyncio
    async def test_keyword_search_fallback_empty(self):
        db = _make_mock_db()
        results = await _keyword_search(db, "test query")
        assert isinstance(results, list)


class TestSimilarityFilter:
    @pytest.mark.asyncio
    async def test_filter_below_threshold(self):
        results = [
            {"content": "a", "similarity": 0.8},
            {"content": "b", "similarity": 0.5},
            {"content": "c", "similarity": 0.9},
        ]
        filtered = await filter_by_similarity(results, threshold=0.7)
        assert len(filtered) == 2

    @pytest.mark.asyncio
    async def test_all_above_threshold(self):
        results = [
            {"content": "a", "similarity": 0.8},
            {"content": "b", "similarity": 0.9},
        ]
        filtered = await filter_by_similarity(results, threshold=0.7)
        assert len(filtered) == 2

    @pytest.mark.asyncio
    async def test_empty_results(self):
        filtered = await filter_by_similarity([], threshold=0.7)
        assert len(filtered) == 0


class TestRetrieveMemory:
    @pytest.mark.asyncio
    async def test_retrieve_empty(self):
        db = _make_mock_db()
        results = await retrieve_memory(db, "test", top_k=5, threshold=0.0)
        assert isinstance(results, list)
