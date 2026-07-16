"""Connection pooling for HTTP clients with proper lifecycle."""

import asyncio
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class HttpPool:
    """Shared HTTP connection pool with graceful startup/shutdown."""

    def __init__(
        self,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        keepalive_expiry: float = 30.0,
    ):
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self.keepalive_expiry = keepalive_expiry
        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        async with self._lock:
            if self._started:
                return
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=10.0),
                limits=httpx.Limits(
                    max_connections=self.max_connections,
                    max_keepalive_connections=self.max_keepalive_connections,
                    keepalive_expiry=self.keepalive_expiry,
                ),
            )
            self._started = True
            logger.info("HttpPool started (max_conn=%d)", self.max_connections)

    async def stop(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            self._started = False
            logger.info("HttpPool stopped")

    def get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("HttpPool not started")
        return self._client

    async def get(self, url: str, **kwargs) -> httpx.Response:
        client = self.get_client()
        return await client.get(url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        client = self.get_client()
        return await client.post(url, **kwargs)

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        client = self.get_client()
        return await client.request(method, url, **kwargs)


_http_pool: Optional[HttpPool] = None


def get_http_pool() -> HttpPool:
    global _http_pool
    if _http_pool is None:
        from core.config import get_settings

        settings = get_settings()
        _http_pool = HttpPool(max_connections=settings.max_workers * 4)
    return _http_pool