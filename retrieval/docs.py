"""
Docs Retriever - Document retrieval with embeddings.

Supports Qdrant and OpenAI embedding providers,
with in-memory fallback for development.
"""

import os
import time
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass


class QdrantEmbeddingProvider(EmbeddingProvider):
    def __init__(self, url: Optional[str] = None):
        self.url = url or os.getenv("QDRANT_HOST", "http://localhost:6333")
        self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def embed(self, text: str) -> List[float]:
        results = await self.embed_batch([text])
        if results:
            return results[0]
        from ingestion.embedder import EmbeddingPipeline
        pipeline = EmbeddingPipeline()
        return await pipeline.embed(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            from ingestion.embedder import get_embedder
            embedder = get_embedder()
            return await embedder.embed_batch(texts)
        except Exception as e:
            logger.warning("QdrantEmbeddingProvider: embedder unavailable: %s", e)
            return []


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self, api_key: Optional[str] = None, model: str = "text-embedding-3-small"
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"Authorization": f"Bearer {self.api_key}"}, timeout=60.0
            )
        return self._client

    async def embed(self, text: str) -> List[float]:
        results = await self.embed_batch([text])
        if not results:
            raise RuntimeError("OpenAI embed failed: no results returned")
        return results[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            resp = await self._get_client().post(
                "https://api.openai.com/v1/embeddings",
                json={"input": texts, "model": self.model},
            )
            resp.raise_for_status()
            data = resp.json()
            return [d["embedding"] for d in data.get("data", [])]
        except Exception as e:
            logger.error("OpenAI embed_batch failed: %s", e)
            raise RuntimeError(f"OpenAI embedding failed: {e}") from e


class DocsBackend(ABC):
    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        pass


class QdrantDocsBackend(DocsBackend):
    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 6333,
        collection: str = "documents",
        embedding_provider: Optional[EmbeddingProvider] = None,
    ):
        self.host = host or os.getenv("QDRANT_HOST", "localhost")
        self.port = port
        self.collection = collection
        self.base_url = f"http://{self.host}:{self.port}"
        self.embedding_provider = embedding_provider or QdrantEmbeddingProvider()

    @staticmethod
    def _create_embedding_provider() -> EmbeddingProvider:
        provider_type = os.getenv("EMBEDDING_PROVIDER", "").lower()
        if provider_type == "openai":
            return OpenAIEmbeddingProvider()
        else:
            return QdrantEmbeddingProvider()

    async def search(
        self,
        query: str,
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        vector = await self.embedding_provider.embed(query)

        payload = {
            "vector": vector,
            "limit": limit,
            "score_threshold": score_threshold,
            "filter": filters or {},
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/collections/{self.collection}/points/search",
                    json=payload,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("result", [])
        except Exception as e:
            logger.warning("Error searching Qdrant: %s", e)
            return []

    async def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/collections/{self.collection}/points/{doc_id}"
                )
                response.raise_for_status()
                return response.json().get("result")
        except Exception as e:
            logger.warning("Error getting doc from Qdrant: %s", e)
            return None


class InMemoryDocsBackend(DocsBackend):
    """Fallback in-memory backend for development."""

    def __init__(self):
        self._docs: List[Dict[str, Any]] = []

    def add_doc(self, doc: Dict[str, Any]) -> None:
        self._docs.append(doc)

    async def search(
        self,
        query: str,
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        results = []

        for doc in self._docs:
            content = doc.get("content", "").lower()
            if query_lower in content:
                results.append(doc)
            elif any(q in content for q in query_lower.split()):
                score = sum(q in content for q in query_lower.split())
                if score > 0:
                    results.append(doc)

        return results[:limit]

    async def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        for doc in self._docs:
            if doc.get("id") == doc_id:
                return doc
        return None


class DocsRetriever:
    def __init__(
        self,
        backend: Optional[DocsBackend] = None,
    ):
        self.backend = backend or self._create_backend()

    @staticmethod
    def _create_backend() -> DocsBackend:
        backend_type = os.getenv("DOCS_BACKEND", "").lower()
        if backend_type == "qdrant":
            return QdrantDocsBackend()
        else:
            return InMemoryDocsBackend()

    async def search(
        self,
        query: str,
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)

        results = await self.backend.search(query, limit, score_threshold, filters)

        took = int(time.time() * 1000) - start

        return {
            "source": "docs",
            "query": query,
            "results": results,
            "total": len(results),
            "took_ms": took,
        }

    async def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        return await self.backend.get(doc_id)


def get_docs_retriever() -> DocsRetriever:
    return DocsRetriever()
