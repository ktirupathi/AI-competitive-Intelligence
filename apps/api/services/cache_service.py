"""Redis-backed caching service for Scout AI.

Provides:
- Generic key-value cache with TTL
- News deduplication (URL-based)
- Web snapshot caching (content-hash based)

Falls back gracefully to no-op when Redis is unavailable so the rest
of the application continues to function.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Optional redis import — the service degrades gracefully if missing
try:
    import redis.asyncio as aioredis
except ImportError:  # pragma: no cover
    aioredis = None  # type: ignore[assignment]


class CacheService:
    """Async Redis cache with optional fallback to in-memory dict.

    Parameters
    ----------
    redis_url : str
        Redis connection string (e.g. ``redis://localhost:6379/0``).
    prefix : str
        Key prefix to namespace all cache entries.
    default_ttl : int
        Default TTL in seconds for cached entries.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        prefix: str = "scoutai",
        default_ttl: int = 3600,
    ) -> None:
        self._prefix = prefix
        self._default_ttl = default_ttl
        self._redis: Optional[Any] = None
        self._redis_url = redis_url
        # In-memory fallback when Redis is unavailable
        self._fallback: dict[str, Any] = {}
        self._connected = False

    async def connect(self) -> None:
        """Attempt to connect to Redis.  Logs and falls back if unavailable."""
        if aioredis is None:
            logger.warning("redis package not installed — using in-memory cache fallback")
            return
        try:
            self._redis = aioredis.from_url(
                self._redis_url, decode_responses=True, socket_connect_timeout=3
            )
            await self._redis.ping()
            self._connected = True
            logger.info("Connected to Redis at %s", self._redis_url)
        except Exception as exc:
            logger.warning("Redis unavailable (%s) — using in-memory cache fallback", exc)
            self._redis = None
            self._connected = False

    async def close(self) -> None:
        """Close the Redis connection pool."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
            self._connected = False

    def _key(self, namespace: str, key: str) -> str:
        return f"{self._prefix}:{namespace}:{key}"

    # ------------------------------------------------------------------
    # Generic get / set / delete
    # ------------------------------------------------------------------

    async def get(self, namespace: str, key: str) -> Optional[str]:
        """Return cached value or ``None`` if not found / expired."""
        full_key = self._key(namespace, key)
        if self._redis is not None:
            try:
                return await self._redis.get(full_key)
            except Exception:
                logger.debug("Redis GET failed for %s", full_key)
        return self._fallback.get(full_key)

    async def set(
        self, namespace: str, key: str, value: str, ttl: Optional[int] = None
    ) -> None:
        """Store a value with optional TTL override."""
        full_key = self._key(namespace, key)
        ttl = ttl if ttl is not None else self._default_ttl
        if self._redis is not None:
            try:
                await self._redis.set(full_key, value, ex=ttl)
                return
            except Exception:
                logger.debug("Redis SET failed for %s", full_key)
        self._fallback[full_key] = value

    async def delete(self, namespace: str, key: str) -> None:
        """Remove a cached entry."""
        full_key = self._key(namespace, key)
        if self._redis is not None:
            try:
                await self._redis.delete(full_key)
                return
            except Exception:
                pass
        self._fallback.pop(full_key, None)

    # ------------------------------------------------------------------
    # News deduplication
    # ------------------------------------------------------------------

    async def is_news_seen(self, url: str) -> bool:
        """Check whether a news URL has been seen before."""
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        result = await self.get("news_seen", url_hash)
        return result is not None

    async def mark_news_seen(self, url: str, ttl: int = 86400 * 7) -> None:
        """Mark a news URL as seen (default 7-day TTL)."""
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        await self.set("news_seen", url_hash, "1", ttl=ttl)

    # ------------------------------------------------------------------
    # Snapshot caching
    # ------------------------------------------------------------------

    async def get_snapshot(self, url: str) -> Optional[dict]:
        """Return a cached web snapshot for *url*, if any."""
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        raw = await self.get("snapshot", url_hash)
        if raw is not None:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
        return None

    async def set_snapshot(
        self, url: str, data: dict, ttl: int = 3600 * 24
    ) -> None:
        """Cache a web snapshot for *url* (default 24-hour TTL)."""
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        await self.set("snapshot", url_hash, json.dumps(data), ttl=ttl)
