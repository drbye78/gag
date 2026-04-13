"""
Embedder - Embedding generation pipeline.

Provides batched embedding generation with provider
abstraction (OpenAI, Qwen, Ollama, local models).
Uses persistent httpx clients for connection pooling.
Includes per-text SHA-256 caching to skip repeated embeddings.
"""

import hashlib
import logging
import os
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

from core.config import get_settings
from core.text_utils import detect_language, TextLanguage

logger = logging.getLogger(__name__)


class EmbedderProvider(str, Enum):
    OPENAI = "openai"
    QWEN = "qwen"
    OLLAMA = "ollama"
    QDRANT = "qdrant"


class EmbeddingPipeline:
    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        batch_size: int = 100,
        max_concurrent: int = 5,
        dimensions: int = 1536,
        cache_capacity: int = 10_000,
        cache_ttl: int = 86400,  # 24 hours
    ):
        self.provider = provider.lower()
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self._client: Optional[httpx.AsyncClient] = None
        self._semaphore = httpx.Limits(max_connections=max_concurrent)

        # Embedding cache: text hash → embedding vector
        self._cache_capacity = cache_capacity
        self._cache_ttl = cache_ttl
        self._embedding_cache: OrderedDict[str, tuple] = (
            OrderedDict()
        )  # hash → (vector, timestamp)

        settings = get_settings()

        if self.provider == "openai":
            self.model = model or "text-embedding-3-small"
            self.dimensions = 1536
        elif self.provider == "qwen":
            self.model = model or "text-embedding-v3"
            self.dimensions = 1024
        elif self.provider == "ollama":
            self.model = model or "nomic-embed-text"
            self.dimensions = 768
        else:
            self.model = model or "default"
            self.dimensions = dimensions

    # ------------------------------------------------------------------
    # Embedding cache helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _text_hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()

    def _cache_get(self, text_hash: str) -> Optional[List[float]]:
        entry = self._embedding_cache.get(text_hash)
        if entry is None:
            return None
        embedding, timestamp = entry
        if (time.time() - timestamp) > self._cache_ttl:
            del self._embedding_cache[text_hash]
            return None
        self._embedding_cache.move_to_end(text_hash)
        return embedding

    def _cache_put(self, text_hash: str, embedding: List[float]) -> None:
        if len(self._embedding_cache) >= self._cache_capacity:
            self._embedding_cache.popitem(last=False)
        self._embedding_cache[text_hash] = (embedding, time.time())

    def get_cache_stats(self) -> Dict[str, Any]:
        return {
            "size": len(self._embedding_cache),
            "capacity": self._cache_capacity,
            "ttl_seconds": self._cache_ttl,
        }

    def get_model_for_language(self, text: str) -> str:
        if not text:
            return self.model

        lang = detect_language(text)

        if lang == TextLanguage.RUSSIAN:
            if self.provider == "qwen":
                return "text-embedding-v3"
            elif self.provider == "ollama":
                return "nomic-embed-text"
            return "text-embedding-3-small"

        return self.model

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                limits=self._semaphore,
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def embed(self, text: str) -> List[float]:
        results = await self.embed_batch([text])
        return results[0] if results else []

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        # Check cache for each text
        cached: Dict[int, List[float]] = {}
        to_embed: List[str] = []
        to_embed_indices: List[int] = []

        for i, text in enumerate(texts):
            text_hash = self._text_hash(text)
            cached_vec = self._cache_get(text_hash)
            if cached_vec is not None:
                cached[i] = cached_vec
            else:
                to_embed.append(text)
                to_embed_indices.append(i)

        # Embed only the uncached texts
        fresh_embeddings: List[List[float]] = []
        if to_embed:
            if self.provider == "openai":
                fresh_embeddings = await self._embed_openai(to_embed)
            elif self.provider == "qwen":
                fresh_embeddings = await self._embed_qwen(to_embed)
            elif self.provider == "ollama":
                fresh_embeddings = await self._embed_ollama(to_embed)
            else:
                fresh_embeddings = await self._embed_qdrant(to_embed)

            # Cache the fresh embeddings
            for idx, embedding in zip(to_embed_indices, fresh_embeddings):
                text_hash = self._text_hash(texts[idx])
                self._cache_put(text_hash, embedding)

        # Assemble final result in original order
        results: List[List[float]] = [None] * len(texts)  # type: ignore
        for i, vec in cached.items():
            results[i] = vec
        for pos, idx in enumerate(to_embed_indices):
            results[idx] = fresh_embeddings[pos]

        return results

    async def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        settings = get_settings()
        api_key = settings.llm_api_key or os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not configured")

        headers = {"Authorization": f"Bearer {api_key}"}
        client = await self._get_client()

        resp = await client.post(
            "https://api.openai.com/v1/embeddings",
            json={"input": texts, "model": self.model},
            headers=headers,
            timeout=120.0,
        )
        resp.raise_for_status()
        data = resp.json()
        embeddings = [d["embedding"] for d in data.get("data", [])]

        if len(embeddings) != len(texts):
            logger.warning(
                "OpenAI returned %d embeddings for %d texts",
                len(embeddings),
                len(texts),
            )

        return embeddings

    async def _embed_qwen(self, texts: List[str]) -> List[List[float]]:
        settings = get_settings()
        api_key = os.getenv("DASHSCOPE_API_KEY", settings.llm_api_key or "")
        base_url = os.getenv(
            "QWEN_EMBED_URL",
            "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/embedding",
        )

        if not api_key:
            raise RuntimeError("DASHSCOPE_API_KEY not configured")

        headers = {"Authorization": f"Bearer {api_key}"}
        client = await self._get_client()

        results = []
        for text in texts:
            resp = await client.post(
                base_url,
                json={
                    "model": self.model,
                    "input": text,
                },
                headers=headers,
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            embedding = (
                data.get("output", {}).get("embeddings", [{}])[0].get("embedding", [])
            )
            results.append(embedding)
        return results

    async def _embed_ollama(self, texts: List[str]) -> List[List[float]]:
        base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        client = await self._get_client()

        results = []
        for text in texts:
            resp = await client.post(
                f"{base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            embedding = data.get("embedding", [])
            results.append(embedding)
        return results

    async def _embed_qdrant(self, texts: List[str]) -> List[List[float]]:
        base_url = os.getenv("QDRANT_HOST", "http://localhost:6333")
        client = await self._get_client()

        resp = await client.post(
            f"{base_url}/collections/embeddings/points/search",
            json={"vector": texts, "limit": len(texts)},
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", [])

    async def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not chunks:
            return []

        texts = [c.get("content", "") for c in chunks]
        embeddings = await self.embed_batch(texts)

        results = []
        for idx, chunk in enumerate(chunks):
            embedding = embeddings[idx] if idx < len(embeddings) else []
            result = {
                **chunk,
                "embedding": embedding,
                "provider": self.provider,
                "model": self.model,
            }
            results.append(result)

        return results


_pipeline: Optional[EmbeddingPipeline] = None


def get_embedding_pipeline() -> EmbeddingPipeline:
    global _pipeline
    if _pipeline is None:
        provider = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
        _pipeline = EmbeddingPipeline(provider=provider)
    return _pipeline
