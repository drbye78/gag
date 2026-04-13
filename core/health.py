"""Health checking for external services."""

import time
from typing import Any, Dict

import httpx


class HealthChecker:
    def __init__(self):
        self._qdrant_ok = False
        self._falkordb_ok = False
        self._redis_ok = False
        self._last_check = 0.0
        self._last_result: Dict[str, Any] = {}

    async def check_qdrant(self, host: str = "localhost", port: int = 6333) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"http://{host}:{port}/ready")
                ok = resp.status_code == 200
                self._qdrant_ok = ok
                return ok
        except Exception:
            self._qdrant_ok = False
            return False

    async def check_falkordb(self, host: str = "localhost", port: int = 7379) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # FalkorDB exposes an HTTP health endpoint
                resp = await client.get(f"http://{host}:{port}")
                ok = resp.status_code in (200, 404)
                self._falkordb_ok = ok
                return ok
        except Exception:
            self._falkordb_ok = False
            return False

    async def check_redis(self, url: str = "redis://localhost:6379") -> bool:
        """Check Redis connectivity.

        Attempts to use redis.asyncio if available, otherwise marks as skipped
        since we don't want to require Redis as a hard dependency.
        """
        try:
            import redis.asyncio as redis_lib

            r = redis_lib.from_url(url)
            try:
                pong = await r.ping()
                self._redis_ok = bool(pong)
                return self._redis_ok
            finally:
                await r.aclose()
        except ImportError:
            # redis package not installed — mark as skipped, not failed
            self._redis_ok = False
            return False
        except Exception:
            self._redis_ok = False
            return False

    async def check_all(self) -> Dict[str, Any]:
        now = time.time()
        # Cache results for 10 seconds
        if now - self._last_check < 10 and self._last_result:
            return self._last_result

        results = {
            "qdrant": await self.check_qdrant(),
            "falkordb": await self.check_falkordb(),
            "redis": await self.check_redis(),
        }

        self._last_result = results
        self._last_check = now
        return results

    async def get_status(self) -> Dict[str, Any]:
        status = await self.check_all()
        all_ok = all(status.values())
        any_ok = any(status.values())

        if all_ok:
            overall = "healthy"
        elif any_ok:
            overall = "degraded"
        else:
            overall = "unhealthy"

        return {
            "status": overall,
            "timestamp": time.time(),
            "services": status,
        }


_health_checker: HealthChecker = None  # type: ignore[assignment]


def get_health_checker() -> HealthChecker:
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker
