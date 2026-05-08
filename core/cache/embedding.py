"""Redis-backed embedding cache."""

import json
import logging
from typing import Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisEmbeddingCache:
    def __init__(self, redis_url: str = "redis://localhost:6379/0", ttl: int = 86400):
        self.redis = redis.from_url(redis_url)
        self.ttl = ttl

    async def get(self, key: str) -> Optional[list]:
        try:
            data = await self.redis.get(f"embed:{key}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None

    async def set(self, key: str, embedding: list) -> bool:
        try:
            await self.redis.setex(
                f"embed:{key}",
                self.ttl,
                json.dumps(embedding),
            )
            return True
        except Exception as e:
            logger.warning(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        try:
            await self.redis.delete(f"embed:{key}")
            return True
        except Exception:
            return False


_cache: Optional[RedisEmbeddingCache] = None


def get_embedding_cache(
    redis_url: str = "redis://localhost:6379/0",
    ttl: int = 86400,
) -> RedisEmbeddingCache:
    global _cache
    if _cache is None:
        _cache = RedisEmbeddingCache(redis_url, ttl)
    return _cache