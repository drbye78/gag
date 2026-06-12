"""Redis-backed retrieval result cache."""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)

DEFAULT_RETRIEVAL_TTL = 1800


def _hash_query(query: str, limit: int = 10, strategy: str = "hybrid") -> str:
    """Generate a cache key from query, limit, and strategy."""
    key_input = f"{query}:{limit}:{strategy}"
    return hashlib.sha256(key_input.encode()).hexdigest()[:32]


class RedisRetrievalCache:
    """Redis cache for retrieval search results."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        ttl: int = DEFAULT_RETRIEVAL_TTL,
    ):
        self._redis_url = redis_url
        self._ttl = ttl
        self._client: Optional[redis.Redis] = None

    async def _get_client(self) -> Optional[redis.Redis]:
        if self._client is None:
            try:
                self._client = redis.from_url(self._redis_url)
                await self._client.get("__health__")
            except Exception as e:
                logger.warning(f"Redis unavailable for retrieval cache: {e}")
                self._client = None
        return self._client

    async def get(
        self,
        query: str,
        limit: int = 10,
        strategy: str = "hybrid",
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached retrieval results by query hash."""
        key = _hash_query(query, limit, strategy)
        try:
            client = await self._get_client()
            if client is None:
                return None

            data = await client.get(f"retrieval:{key}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Redis retrieval cache get error: {e}")
            return None

    async def set(
        self,
        query: str,
        results: List[Dict[str, Any]],
        limit: int = 10,
        strategy: str = "hybrid",
        ttl: Optional[int] = None,
    ) -> bool:
        """Cache retrieval results with optional custom TTL."""
        key = _hash_query(query, limit, strategy)
        effective_ttl = ttl or self._ttl
        try:
            client = await self._get_client()
            if client is None:
                return False

            await client.setex(
                f"retrieval:{key}",
                effective_ttl,
                json.dumps(results),
            )
            return True
        except Exception as e:
            logger.warning(f"Redis retrieval cache set error: {e}")
            return False

    async def delete(
        self,
        query: str,
        limit: int = 10,
        strategy: str = "hybrid",
    ) -> bool:
        """Delete cached results."""
        key = _hash_query(query, limit, strategy)
        try:
            client = await self._get_client()
            if client is None:
                return False

            await client.delete(f"retrieval:{key}")
            return True
        except Exception as e:
            logger.warning(f"Redis retrieval cache delete error: {e}")
            return False

    async def clear(self) -> bool:
        """Clear all retrieval cache entries."""
        try:
            client = await self._get_client()
            if client is None:
                return False

            keys = []
            async for key in client.scan_iter(match="retrieval:*"):
                keys.append(key)
            if keys:
                await client.delete(*keys)
            return True
        except Exception as e:
            logger.warning(f"Redis retrieval cache clear error: {e}")
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None


_cache: Optional[RedisRetrievalCache] = None


def get_retrieval_cache(
    redis_url: str = "redis://localhost:6379/0",
    ttl: int = DEFAULT_RETRIEVAL_TTL,
) -> RedisRetrievalCache:
    global _cache
    if _cache is None:
        _cache = RedisRetrievalCache(redis_url, ttl)
    return _cache
