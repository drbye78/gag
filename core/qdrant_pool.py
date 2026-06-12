"""Qdrant connection pooling using shared HttpPool."""

import logging
from typing import Optional

import httpx

from core.pool import get_http_pool

logger = logging.getLogger(__name__)

DEFAULT_QDRANT_CONNECTIONS = 10
DEFAULT_KEEPALIVE = 5


class QdrantPool:
    def __init__(self, url: str, api_key: Optional[str] = None):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self._pool = get_http_pool()

    async def get_client(self) -> httpx.AsyncClient:
        await self._pool.start()
        return self._pool.client

    async def close(self) -> None:
        await self._pool.stop()


_qdrant_pool: Optional[QdrantPool] = None


def get_qdrant_pool(url: str, api_key: Optional[str] = None) -> QdrantPool:
    global _qdrant_pool
    if _qdrant_pool is None:
        _qdrant_pool = QdrantPool(url, api_key)
    return _qdrant_pool


__all__ = ["QdrantPool", "get_qdrant_pool"]
