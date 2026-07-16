"""
Code Retriever - Code retrieval from vector store.

Queries code entities from Qdrant with language filtering.
"""

import time
from typing import Any, Dict, List, Optional

import httpx


class CodeRetriever:
    def __init__(
        self, host: Optional[str] = None, port: int = 6333, collection: str = "code"
    ):
        self.host = host or "localhost"
        self.port = port
        self.collection = collection
        self.base_url = f"http://{self.host}:{self.port}"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Cached HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
            )
        return self._client

    async def search(
        self,
        query: str,
        limit: int = 10,
        language: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)

        from llm.router import get_router
        router = get_router()
        embedding = await router.embed(query)
        payload = {"vector": embedding, "limit": limit, "filter": filters or {}, "with_payload": True}

        if language:
            payload["filter"]["language"] = {"eq": language}

        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/collections/{self.collection}/points/search",
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Code search failed: {e}")
            data = {"result": [], "status": "error", "error": str(e)}

        took = int(time.time() * 1000) - start

        return {
            "source": "code",
            "query": query,
            "results": data.get("result", []),
            "total": len(data.get("result", [])),
            "took_ms": took,
        }


def get_code_retriever() -> CodeRetriever:
    return CodeRetriever()
