"""Tests for the CacheService (in-memory fallback mode)."""

from __future__ import annotations

import pytest

from apps.api.services.cache_service import CacheService


@pytest.fixture
def cache() -> CacheService:
    """Return a CacheService instance using in-memory fallback (no Redis)."""
    svc = CacheService(redis_url="redis://localhost:6379/0")
    # Don't call connect() — forces in-memory fallback
    return svc


class TestGenericCache:
    """Tests for generic get/set/delete operations."""

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache: CacheService) -> None:
        await cache.set("ns", "key1", "value1")
        result = await cache.get("ns", "key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self, cache: CacheService) -> None:
        result = await cache.get("ns", "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_removes_entry(self, cache: CacheService) -> None:
        await cache.set("ns", "del_me", "value")
        await cache.delete("ns", "del_me")
        result = await cache.get("ns", "del_me")
        assert result is None

    @pytest.mark.asyncio
    async def test_namespaces_are_isolated(self, cache: CacheService) -> None:
        await cache.set("a", "key", "from_a")
        await cache.set("b", "key", "from_b")
        assert await cache.get("a", "key") == "from_a"
        assert await cache.get("b", "key") == "from_b"


class TestNewsDedup:
    """Tests for news URL deduplication."""

    @pytest.mark.asyncio
    async def test_unseen_url_returns_false(self, cache: CacheService) -> None:
        assert await cache.is_news_seen("https://example.com/article") is False

    @pytest.mark.asyncio
    async def test_mark_seen_then_check(self, cache: CacheService) -> None:
        url = "https://example.com/already-read"
        await cache.mark_news_seen(url)
        assert await cache.is_news_seen(url) is True

    @pytest.mark.asyncio
    async def test_different_urls_independent(self, cache: CacheService) -> None:
        await cache.mark_news_seen("https://a.com/1")
        assert await cache.is_news_seen("https://a.com/1") is True
        assert await cache.is_news_seen("https://a.com/2") is False


class TestSnapshotCache:
    """Tests for web snapshot caching."""

    @pytest.mark.asyncio
    async def test_get_missing_snapshot(self, cache: CacheService) -> None:
        result = await cache.get_snapshot("https://example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get_snapshot(self, cache: CacheService) -> None:
        data = {"content_hash": "abc123", "text": "Hello World"}
        await cache.set_snapshot("https://example.com", data)
        result = await cache.get_snapshot("https://example.com")
        assert result == data

    @pytest.mark.asyncio
    async def test_snapshot_different_urls(self, cache: CacheService) -> None:
        await cache.set_snapshot("https://a.com", {"a": 1})
        await cache.set_snapshot("https://b.com", {"b": 2})
        assert (await cache.get_snapshot("https://a.com"))["a"] == 1
        assert (await cache.get_snapshot("https://b.com"))["b"] == 2
