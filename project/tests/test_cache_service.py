"""Tests for Cache Service (Phase 6.5)."""

from unittest.mock import AsyncMock, patch

import pytest

from services.memory.cache_service import (
    TTL_CONFIG,
    cache_get,
    cache_invalidate,
    cache_invalidate_pattern,
    cache_set,
    get_cache_stats,
    get_ttl,
    reset_cache_stats,
)


class TestCacheService:
    def test_default_ttl(self):
        assert get_ttl("task") == 300
        assert get_ttl("embedding") == 86400
        assert get_ttl("unknown") == 3600

    def test_ttl_config_has_all_types(self):
        expected = ["task", "memory_search", "law_check", "embedding", "instruction", "decision"]
        for t in expected:
            assert t in TTL_CONFIG, f"Missing TTL config for {t}"

    def test_cache_stats(self):
        reset_cache_stats()
        stats = get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_cache_get_miss(self):
        reset_cache_stats()
        with patch("services.memory.cache_service._cache_get", AsyncMock(return_value=None)):
            result = await cache_get("test_key")
            assert result is None
            stats = get_cache_stats()
            assert stats["misses"] == 1
            assert stats["hits"] == 0

    @pytest.mark.asyncio
    async def test_cache_get_hit(self):
        reset_cache_stats()
        with patch("services.memory.cache_service._cache_get", AsyncMock(return_value="cached_value")):
            result = await cache_get("test_key")
            assert result == "cached_value"
            stats = get_cache_stats()
            assert stats["hits"] == 1
            assert stats["misses"] == 0

    @pytest.mark.asyncio
    async def test_cache_set_success(self):
        with patch("services.memory.cache_service._cache_set", AsyncMock(return_value=True)):
            result = await cache_set("key", "value", ttl=300)
            assert result is True

    @pytest.mark.asyncio
    async def test_cache_set_failure(self):
        with patch("services.memory.cache_service._cache_set", AsyncMock(side_effect=Exception("Redis down"))):
            result = await cache_set("key", "value")
            assert result is False

    @pytest.mark.asyncio
    async def test_cache_invalidate_success(self):
        with patch("services.memory.cache_service._cache_delete", AsyncMock(return_value=True)):
            result = await cache_invalidate("some_key")
            assert result is True

    @pytest.mark.asyncio
    async def test_cache_invalidate_failure(self):
        with patch("services.memory.cache_service._cache_delete", AsyncMock(side_effect=Exception("Redis down"))):
            result = await cache_invalidate("some_key")
            assert result is False

    @pytest.mark.asyncio
    async def test_cache_invalidate_pattern_success(self):
        with patch("services.memory.cache_service._cache_invalidate", AsyncMock(return_value=True)):
            result = await cache_invalidate_pattern("prefix:*")
            assert result is True

    @pytest.mark.asyncio
    async def test_hit_rate_calculation(self):
        reset_cache_stats()
        with patch("services.memory.cache_service._cache_get", AsyncMock(return_value="v")):
            await cache_get("k1")
        with patch("services.memory.cache_service._cache_get", AsyncMock(return_value="v")):
            await cache_get("k2")
        with patch("services.memory.cache_service._cache_get", AsyncMock(return_value=None)):
            await cache_get("k3")
        stats = get_cache_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == pytest.approx(2/3, rel=1e-4)
