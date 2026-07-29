"""Distributed rate limiter backed by Redis."""
import asyncio
import logging
import time
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class DistributedRateLimiter:
    """Redis-backed sliding window rate limiter.

    Uses Redis INCR + EXPIRE for accurate per-key counting across
    multiple worker processes/replicas.
    """

    def __init__(self, redis_url: str, default_limit: int = 100, window_seconds: int = 60):
        self.redis_url = redis_url
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self._redis = None
        self._lock = asyncio.Lock()

    async def _get_redis(self):
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def is_allowed(self, key: str, limit: Optional[int] = None) -> Tuple[bool, int]:
        """Check if request is allowed for the given key.

        Args:
            key: Rate limit key (e.g., client IP, user ID, or API key)
            limit: Max requests per window (default: self.default_limit)

        Returns:
            (allowed: bool, remaining: int)
        """
        max_requests = limit or self.default_limit

        try:
            redis = await self._get_redis()
            window_key = f"ratelimit:{key}:{int(time.time() / self.window_seconds)}"

            count = await redis.incr(window_key)
            if count == 1:
                await redis.expire(window_key, self.window_seconds + 1)

            remaining = max(0, max_requests - count)
            return count <= max_requests, remaining
        except Exception as e:
            logger.warning("Rate limiter Redis error (allowing request): %s", e)
            return True, 0  # Fail open

    async def get_usage(self, key: str) -> Dict:
        """Get current usage stats for a key."""
        try:
            redis = await self._get_redis()
            window_key = f"ratelimit:{key}:{int(time.time() / self.window_seconds)}"
            count = await redis.get(window_key)
            return {
                "key": key,
                "current": int(count) if count else 0,
                "limit": self.default_limit,
                "window_seconds": self.window_seconds,
            }
        except Exception:
            return {"key": key, "current": 0, "limit": self.default_limit, "window_seconds": self.window_seconds}

    async def close(self):
        if self._redis:
            await self._redis.close()
            self._redis = None


_limiter: Optional[DistributedRateLimiter] = None


async def get_distributed_rate_limiter() -> DistributedRateLimiter:
    global _limiter
    if _limiter is None:
        from core.config import get_settings
        settings = get_settings()
        redis_url = getattr(settings, 'redis_url', 'redis://localhost:6379')
        _limiter = DistributedRateLimiter(
            redis_url=redis_url,
            default_limit=getattr(settings, 'rate_limit_requests', 100),
            window_seconds=getattr(settings, 'rate_limit_window', 60),
        )
    return _limiter
