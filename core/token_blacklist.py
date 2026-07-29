"""JWT token blacklist backed by Redis with TTL-based expiry."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TokenBlacklist:
    """Redis-backed JWT token blacklist.

    Blacklisted tokens are stored with TTL matching their natural expiry.
    When the TTL expires, the entry is automatically removed by Redis.
    No cleanup needed — Redis handles expiry natively.
    """

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def blacklist(self, jti: str, expires_in: int) -> bool:
        """Add a token JTI to the blacklist.

        Args:
            jti: JWT ID (from token claims)
            expires_in: Seconds until the token naturally expires

        The blacklist entry auto-expires after `expires_in` seconds,
        matching the token's natural expiry.
        """
        redis = await self._get_redis()
        await redis.setex(f"blacklist:{jti}", expires_in, "1")
        return True

    async def is_blacklisted(self, jti: str) -> bool:
        """Check if a token JTI is blacklisted."""
        redis = await self._get_redis()
        return bool(await redis.exists(f"blacklist:{jti}"))

    async def close(self):
        if self._redis:
            await self._redis.close()
            self._redis = None


_blacklist: Optional[TokenBlacklist] = None


async def get_token_blacklist() -> TokenBlacklist:
    global _blacklist
    if _blacklist is None:
        from core.config import get_settings

        settings = get_settings()
        redis_url = getattr(settings, "redis_url", "redis://localhost:6379")
        _blacklist = TokenBlacklist(redis_url=redis_url)
    return _blacklist
