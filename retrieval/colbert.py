"""
ColBERT Indexer - Late interaction indexing for better retrieval.

ColBERT creates multi-vector representations and uses late interaction
scoring which can outperform standard dense embeddings.

This complements:
- ColPali (visual document indexing)
- Standard vector indexing (Qdrant)
"""

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from ingestion.chunker import Chunk, ChunkResult


logger = logging.getLogger(__name__)


COLBERT_AVAILABLE = False
ColBERTModel = None

try:
    from fastembed import LateInteractionTextEmbedding

    COLBERT_AVAILABLE = True
    ColBERTModel = LateInteractionTextEmbedding
except ImportError:
    pass


@dataclass
class ColBERTIndexResult:
    chunks: List[Any]
    vectors: List[List[float]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ColBERTQdrantIndexer:
    """
    ColBERT indexer that stores multi-vector embeddings in Qdrant.
    
    Uses Qdrant's multi-vector capability to store per-token embeddings,
    enabling MaxSIM late-interaction scoring at query time.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 6333,
        collection: str = "colbert_docs",
        model_name: str = "colbert-ir/colbertv2.0",
    ):
        self.host = host or os.getenv("QDRANT_HOST", "localhost")
        self.port = port
        self.collection = collection
        self.model_name = model_name
        self.base_url = f"http://{self.host}:{self.port}"
        self._client: Optional[httpx.AsyncClient] = None
        self._model = None
        self.vector_dim = 128

    @property
    def available(self) -> bool:
        return COLBERT_AVAILABLE

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=30.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _get_model(self):
        if self._model is None and COLBERT_AVAILABLE:
            try:
                self._model = ColBERTModel(model_name=self.model_name)
            except Exception as e:
                logger.warning("Failed to load ColBERT model: %s", e)
        return self._model

    async def create_collection(self) -> bool:
        payload = {
            "vectors": {
                "size": self.vector_dim,
                "distance": "Dot",
                "multivector_config": {
                    "mode": "max_sim"
                }
            }
        }

        try:
            client = await self._get_client()
            resp = await client.put(
                f"{self.base_url}/collections/{self.collection}",
                json=payload,
                timeout=30.0,
            )
            if resp.status_code in (200, 201):
                logger.info("Created ColBERT collection: %s", self.collection)
                return True
            elif resp.status_code == 409:
                logger.info("ColBERT collection already exists: %s", self.collection)
                return True
            else:
                logger.error("Failed to create collection: HTTP %d", resp.status_code)
                return False
        except Exception as e:
            logger.error("Failed to create ColBERT collection: %s", e)
            return False

    async def delete_collection(self) -> bool:
        try:
            client = await self._get_client()
            resp = await client.delete(
                f"{self.base_url}/collections/{self.collection}",
                timeout=30.0,
            )
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.warning("Failed to delete collection: %s", e)
            return False

    async def index_chunks(
        self,
        chunks: List[Dict[str, Any]],
        source_id: str = "default",
        source_type: str = "document",
    ) -> Dict[str, Any]:
        start = time.time()
        model = self._get_model()

        if not model:
            return {
                "indexed_count": 0,
                "took_ms": 0,
                "errors": ["ColBERT model not available"],
            }

        if not chunks:
            return {"indexed_count": 0, "took_ms": 0, "errors": []}

        try:
            await self.create_collection()
        except Exception as e:
            logger.warning("Collection creation check failed: %s", e)

        points = []
        batch_size = 50

        for idx, chunk in enumerate(chunks):
            content = chunk.get("content", "")
            if not content:
                continue

            try:
                emb = next(model.passage_embed([content]))
                vectors = emb.tolist()
            except Exception as e:
                logger.warning("Failed to embed chunk %d: %s", idx, e)
                continue

            point = {
                "id": chunk.get("id", str(uuid.uuid4())),
                "vector": vectors,
                "payload": {
                    "content": content,
                    "source_id": source_id,
                    "source_type": source_type,
                    "chunk_index": chunk.get("chunk_index", idx),
                    "metadata": chunk.get("metadata", {}),
                },
            }
            points.append(point)

        if not points:
            return {"indexed_count": 0, "took_ms": 0, "errors": ["No embeddings generated"]}

        indexed = 0
        errors = []
        client = await self._get_client()

        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            try:
                resp = await client.put(
                    f"{self.base_url}/collections/{self.collection}/points",
                    json={"points": batch},
                    timeout=120.0,
                )
                if resp.status_code in (200, 201):
                    indexed += len(batch)
                else:
                    errors.append(f"Batch {i // batch_size}: HTTP {resp.status_code}")
            except Exception as e:
                errors.append(f"Batch {i // batch_size}: {e}")

        took = int((time.time() - start) * 1000)
        return {
            "indexed_count": indexed,
            "took_ms": took,
            "errors": errors,
            "metadata": {
                "total_chunks": len(chunks),
                "source_id": source_id,
                "model": self.model_name,
            },
        }

    async def delete_by_source(self, source_id: str) -> Dict[str, Any]:
        try:
            client = await self._get_client()
            resp = await client.post(
                f"{self.base_url}/collections/{self.collection}/points/delete",
                json={
                    "filter": {
                        "must": [
                            {"key": "source_id", "match": {"value": source_id}}
                        ]
                    }
                },
                timeout=30.0,
            )
            return {"success": resp.status_code in (200, 201), "deleted_source": source_id}
        except Exception as e:
            return {"success": False, "error": str(e)}


class ColBERTQdrantRetriever:
    """
    ColBERT retriever that uses Qdrant's native MaxSIM scoring.
    
    Leverages Qdrant's multi-vector search with max_sim configuration
    for efficient late-interaction retrieval.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 6333,
        collection: str = "colbert_docs",
        model_name: str = "colbert-ir/colbertv2.0",
        top_k: int = 10,
    ):
        self.host = host or os.getenv("QDRANT_HOST", "localhost")
        self.port = port
        self.collection = collection
        self.model_name = model_name
        self.top_k = top_k
        self.base_url = f"http://{self.host}:{self.port}"
        self._client: Optional[httpx.AsyncClient] = None
        self._model = None
        self.vector_dim = 128

    @property
    def available(self) -> bool:
        return COLBERT_AVAILABLE

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=30.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _get_model(self):
        if self._model is None and COLBERT_AVAILABLE:
            try:
                self._model = ColBERTModel(model_name=self.model_name)
            except Exception as e:
                logger.warning("Failed to load ColBERT model: %s", e)
        return self._model

    async def search(
        self,
        query: str,
        limit: Optional[int] = None,
        source_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        start = time.time()
        model = self._get_model()

        if not model:
            return {
                "query": query,
                "results": [],
                "total": 0,
                "took_ms": 0,
                "error": "ColBERT model not available",
            }

        limit = limit or self.top_k

        try:
            query_emb = next(model.query_embed([query]))
            query_vectors = query_emb.tolist()
        except Exception as e:
            return {
                "query": query,
                "results": [],
                "total": 0,
                "took_ms": 0,
                "error": f"Failed to embed query: {e}",
            }

        filter_dict = None
        if source_filter:
            filter_dict = {"must": [{"key": "source_id", "match": {"value": source_filter}}]}

        search_payload = {
            "vector": query_vectors,
            "limit": limit,
            "with_payload": True,
            "with_vector": False,
        }
        if filter_dict:
            search_payload["filter"] = filter_dict

        try:
            client = await self._get_client()
            resp = await client.post(
                f"{self.base_url}/collections/{self.collection}/points/search",
                json=search_payload,
                timeout=60.0,
            )

            if resp.status_code != 200:
                return {
                    "query": query,
                    "results": [],
                    "total": 0,
                    "took_ms": int((time.time() - start) * 1000),
                    "error": f"Search HTTP {resp.status_code}",
                }

            data = resp.json()
            results = []
            for point in data.get("result", []):
                results.append({
                    "id": point.get("id"),
                    "score": point.get("score", 0.0),
                    "content": point.get("payload", {}).get("content", ""),
                    "source_id": point.get("payload", {}).get("source_id", ""),
                    "source_type": point.get("payload", {}).get("source_type", "document"),
                    "chunk_index": point.get("payload", {}).get("chunk_index", 0),
                })

            took = int((time.time() - start) * 1000)
            return {
                "query": query,
                "results": results,
                "total": len(results),
                "took_ms": took,
            }

        except Exception as e:
            return {
                "query": query,
                "results": [],
                "total": 0,
                "took_ms": int((time.time() - start) * 1000),
                "error": str(e),
            }


class ColBERTIndexer:
    """Legacy ColBERT indexer for in-memory indexing."""

    def __init__(
        self,
        model_name: str = "colbert-ir/colbertv2.0",
        max_length: int = 512,
    ):
        self.model_name = model_name
        self.max_length = max_length
        self._model = None

    @property
    def available(self) -> bool:
        return COLBERT_AVAILABLE

    def _get_model(self):
        if self._model is None and COLBERT_AVAILABLE:
            try:
                self._model = ColBERTModel(model_name=self.model_name)
            except Exception:
                pass
        return self._model

    def _get_texts(self, chunks: List[Any]) -> List[str]:
        return [chunk.content if hasattr(chunk, "content") else str(chunk) for chunk in chunks]

    async def index_chunks(
        self,
        chunks: List[Any],
        source_id: str,
    ) -> ColBERTIndexResult:
        model = self._get_model()

        if not model:
            return ColBERTIndexResult(
                chunks=chunks, vectors=[], metadata={"error": "ColBERT not available"}
            )

        try:
            texts = self._get_texts(chunks)

            embeddings = []
            for text in texts:
                try:
                    emb = next(model.passage_embed([text]))
                    embeddings.append(emb.tolist())
                except Exception:
                    embeddings.append([])

            return ColBERTIndexResult(
                chunks=chunks,
                vectors=embeddings,
                metadata={
                    "model": self.model_name,
                    "dim": len(embeddings[0][0]) if embeddings and embeddings[0] else 0,
                    "count": len(embeddings),
                },
            )
        except Exception as e:
            return ColBERTIndexResult(
                chunks=chunks, vectors=[], metadata={"error": str(e)}
            )

    def index(self, chunks: List[Any], source_id: str) -> ColBERTIndexResult:
        """Synchronous version."""
        import time

        start = time.time()

        model = self._get_model()

        if not model:
            return ColBERTIndexResult(
                chunks=chunks, vectors=[], metadata={"error": "ColBERT not available"}
            )

        try:
            texts = self._get_texts(chunks)

            embeddings = []
            batch_size = 32

            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                for text in batch:
                    try:
                        emb = next(model.passage_embed([text]))
                        embeddings.append(emb.tolist())
                    except Exception:
                        embeddings.append([])

            return ColBERTIndexResult(
                chunks=chunks,
                vectors=embeddings,
                metadata={
                    "model": self.model_name,
                    "dim": len(embeddings[0][0]) if embeddings and embeddings[0] else 0,
                    "count": len(embeddings),
                    "took_ms": int((time.time() - start) * 1000),
                },
            )
        except Exception as e:
            return ColBERTIndexResult(
                chunks=chunks, vectors=[], metadata={"error": str(e)}
            )


class ColBERTRetriever:
    """Legacy in-memory ColBERT retriever."""

    def __init__(self, indexer: ColBERTIndexer):
        self.indexer = indexer

    def compute_maxsim(
        self,
        query_emb: List[float],
        doc_embeddings: List[List[float]],
    ) -> float:
        """Compute MaxSIM score between query and document."""
        if not doc_embeddings:
            return 0.0

        max_score = 0.0
        for doc_emb in doc_embeddings:
            if not doc_emb or not query_emb:
                continue

            score = sum(
                max(0, query_emb[t] * doc_emb[t])
                for t in range(min(len(query_emb), len(doc_emb)))
            )
            max_score = max(max_score, score)

        return max_score

    async def search(
        self,
        query: str,
        indexed_docs: Dict[str, ColBERTIndexResult],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        model = self.indexer._get_model()

        if not model:
            return []

        try:
            query_emb = next(model.query_embed([query]))
            if hasattr(query_emb, "tolist"):
                query_emb = query_emb.tolist()
            else:
                query_emb = list(query_emb)
        except Exception:
            return []

        results = []

        for doc_id, doc_result in indexed_docs.items():
            if not doc_result.vectors:
                continue

            score = self.compute_maxsim(query_emb, doc_result.vectors)
            results.append({
                "doc_id": doc_id,
                "score": score,
                "chunks": doc_result.chunks,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


_indexer_instance: Optional[ColBERTQdrantIndexer] = None
_retriever_instance: Optional[ColBERTQdrantRetriever] = None


def get_colbert_qdrant_indexer(
    host: Optional[str] = None,
    port: int = 6333,
    collection: str = "colbert_docs",
    model_name: str = "colbert-ir/colbertv2.0",
) -> Optional[ColBERTQdrantIndexer]:
    """Factory for ColBERT Qdrant indexer."""
    global _indexer_instance
    if not COLBERT_AVAILABLE:
        return None
    if _indexer_instance is None:
        _indexer_instance = ColBERTQdrantIndexer(
            host=host, port=port, collection=collection, model_name=model_name
        )
    return _indexer_instance


def get_colbert_qdrant_retriever(
    host: Optional[str] = None,
    port: int = 6333,
    collection: str = "colbert_docs",
    model_name: str = "colbert-ir/colbertv2.0",
    top_k: int = 10,
) -> Optional[ColBERTQdrantRetriever]:
    """Factory for ColBERT Qdrant retriever."""
    global _retriever_instance
    if not COLBERT_AVAILABLE:
        return None
    if _retriever_instance is None:
        _retriever_instance = ColBERTQdrantRetriever(
            host=host, port=port, collection=collection, model_name=model_name, top_k=top_k
        )
    return _retriever_instance


def get_colbert_indexer(
    model_name: str = "colbert-ir/colbertv2.0",
) -> Optional[ColBERTIndexer]:
    """Legacy in-memory indexer factory."""
    if not COLBERT_AVAILABLE:
        return None
    return ColBERTIndexer(model_name=model_name)


def get_colbert_retriever(
    indexer: Optional[ColBERTIndexer] = None,
) -> Optional[ColBERTRetriever]:
    """Legacy in-memory retriever factory."""
    if indexer is None:
        indexer = get_colbert_indexer()
    if indexer is None:
        return None
    return ColBERTRetriever(indexer)


class ColBERTSearchClient:
    """Unified ColBERT search client using Qdrant backend."""

    def __init__(
        self,
        collection_name: str = "colbert_docs",
        model_name: str = "colbert-ir/colbertv2.0",
        max_length: int = 512,
        top_k: int = 10,
    ):
        self.collection_name = collection_name
        self.model_name = model_name
        self.max_length = max_length
        self.top_k = top_k
        self._indexer: Optional[ColBERTQdrantIndexer] = None
        self._retriever: Optional[ColBERTQdrantRetriever] = None

    @property
    def available(self) -> bool:
        return COLBERT_AVAILABLE

    def _get_indexer(self) -> Optional[ColBERTQdrantIndexer]:
        if self._indexer is None and COLBERT_AVAILABLE:
            self._indexer = ColBERTQdrantIndexer(
                collection=self.collection_name,
                model_name=self.model_name,
            )
        return self._indexer

    def _get_retriever(self) -> Optional[ColBERTQdrantRetriever]:
        if self._retriever is None and COLBERT_AVAILABLE:
            self._retriever = ColBERTQdrantRetriever(
                collection=self.collection_name,
                model_name=self.model_name,
                top_k=self.top_k,
            )
        return self._retriever

    async def index_chunks(
        self,
        chunks: List[Dict[str, Any]],
        source_id: str = "default",
        source_type: str = "document",
    ) -> Dict[str, Any]:
        indexer = self._get_indexer()
        if not indexer:
            return {"indexed_count": 0, "error": "ColBERT not available"}
        return await indexer.index_chunks(chunks, source_id, source_type)

    async def search(
        self,
        query: str,
        limit: Optional[int] = None,
        source_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        retriever = self._get_retriever()
        if not retriever:
            return {"results": [], "error": "ColBERT not available"}
        return await retriever.search(query, limit, source_filter)

    async def delete_by_source(self, source_id: str) -> Dict[str, Any]:
        indexer = self._get_indexer()
        if not indexer:
            return {"success": False, "error": "ColBERT not available"}
        return await indexer.delete_by_source(source_id)


def get_colbert_search_client(
    collection_name: str = "colbert_docs",
    model_name: str = "colbert-ir/colbertv2.0",
    max_length: int = 512,
    top_k: int = 10,
) -> Optional[ColBERTSearchClient]:
    """Factory function for ColBERT search client."""
    if not COLBERT_AVAILABLE:
        return None
    return ColBERTSearchClient(
        collection_name=collection_name,
        model_name=model_name,
        max_length=max_length,
        top_k=top_k,
    )