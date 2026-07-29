"""Redis-backed user store with persistence across restarts/replicas."""
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class RedisUserStore:
    """Redis-backed user storage.

    Keys: user:{username} → JSON user object
    Set: users → set of all usernames
    """

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def create_user(self, user_data: Dict) -> bool:
        """Create a new user. Returns False if username already exists."""
        redis = await self._get_redis()
        username = user_data["username"]

        if await redis.exists(f"user:{username}"):
            return False

        await redis.set(f"user:{username}", json.dumps(user_data))
        await redis.sadd("users", username)
        return True

    async def get_user(self, username: str) -> Optional[Dict]:
        """Get user by username."""
        redis = await self._get_redis()
        data = await redis.get(f"user:{username}")
        return json.loads(data) if data else None

    async def list_users(self) -> List[str]:
        """List all usernames."""
        redis = await self._get_redis()
        return list(await redis.smembers("users"))

    async def delete_user(self, username: str) -> bool:
        """Delete a user."""
        redis = await self._get_redis()
        deleted = await redis.delete(f"user:{username}")
        if deleted:
            await redis.srem("users", username)
        return bool(deleted)

    async def close(self):
        if self._redis:
            await self._redis.close()
            self._redis = None


_user_store: Optional[RedisUserStore] = None


async def get_user_store() -> RedisUserStore:
    global _user_store
    if _user_store is None:
        from core.config import get_settings

        settings = get_settings()
        redis_url = getattr(settings, "redis_url", "redis://localhost:6379")
        _user_store = RedisUserStore(redis_url=redis_url)
    return _user_store
