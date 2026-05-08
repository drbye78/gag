"""Redis-backed LLM response cache."""

import hashlib
import json
import logging
from typing import Any, Dict, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Default TTL: 1 hour
DEFAULT_LLM_TTL = 3600


def _hash_prompt(prompt: str, system_prompt: Optional[str] = None) -> str:
    """Generate a cache key from prompt and optional system prompt."""
    key_input = f"{system_prompt or ''}:{prompt}"
    return hashlib.sha256(key_input.encode()).hexdigest()[:32]


class RedisLLMCache:
    """Redis cache for LLM responses by prompt hash."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        ttl: int = DEFAULT_LLM_TTL,
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
                logger.warning(f"Redis unavailable for LLM cache: {e}")
                self._client = None
        return self._client

    async def get(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get cached LLM response by prompt hash."""
        key = _hash_prompt(prompt, system_prompt)
        try:
            client = await self._get_client()
            if client is None:
                return None

            data = await client.get(f"llm:{key}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Redis LLM cache get error: {e}")
            return None

    async def set(
        self,
        prompt: str,
        response: Dict[str, Any],
        system_prompt: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """Cache LLM response with optional custom TTL."""
        key = _hash_prompt(prompt, system_prompt)
        effective_ttl = ttl or self._ttl
        try:
            client = await self._get_client()
            if client is None:
                return False

            await client.setex(
                f"llm:{key}",
                effective_ttl,
                json.dumps(response),
            )
            return True
        except Exception as e:
            logger.warning(f"Redis LLM cache set error: {e}")
            return False

    async def delete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> bool:
        """Delete cached response."""
        key = _hash_prompt(prompt, system_prompt)
        try:
            client = await self._get_client()
            if client is None:
                return False

            await client.delete(f"llm:{key}")
            return True
        except Exception as e:
            logger.warning(f"Redis LLM cache delete error: {e}")
            return False

    async def clear(self) -> bool:
        """Clear all LLM cache entries."""
        try:
            client = await self._get_client()
            if client is None:
                return False

            keys = []
            async for key in client.scan_iter(match="llm:*"):
                keys.append(key)
            if keys:
                await client.delete(*keys)
            return True
        except Exception as e:
            logger.warning(f"Redis LLM cache clear error: {e}")
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None


# Singleton instance
_cache: Optional[RedisLLMCache] = None


def get_llm_cache(
    redis_url: str = "redis://localhost:6379/0",
    ttl: int = DEFAULT_LLM_TTL,
) -> RedisLLMCache:
    """Get or create RedisLLMCache singleton."""
    global _cache
    if _cache is None:
        _cache = RedisLLMCache(redis_url, ttl)
    return _cache