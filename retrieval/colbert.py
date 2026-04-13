"""
ColBERT Indexer - Late interaction indexing for better retrieval.

ColBERT creates multi-vector representations and uses late interaction
scoring which can outperform standard dense embeddings.

This complements:
- ColPali (visual document indexing)
- Standard vector indexing (Qdrant)
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ingestion.chunker import Chunk, ChunkResult


COLBERT_AVAILABLE = False
ColBERTEmbedder = None
colbert_model = None

try:
    from llama_index.embeddings.colbert import ColBERTEmbedder

    COLBERT_AVAILABLE = True
    ColBERTEmbedder = ColBERTEmbedder
except ImportError:
    try:
        from colbert.indexer import ColBERTIndexer as LegacyColBERT
        from colbert.embedding import ColBERTEmbedding

        COLBERT_AVAILABLE = True
        ColBERTEmbedder = LegacyColBERT
    except ImportError:
        pass


@dataclass
class ColBERTIndexResult:
    chunks: List[Chunk]
    vectors: List[List[float]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ColBERTIndexer:
    """ColBERT-based indexer for late interaction retrieval."""

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
                self._model = ColBERTEmbedder(
                    model_name=self.model_name,
                    max_length=self.max_length,
                )
            except Exception:
                pass
        return self._model

    def _get_texts(self, chunks: List[Chunk]) -> List[str]:
        return [chunk.content for chunk in chunks]

    async def index_chunks(
        self,
        chunks: List[Chunk],
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
                    emb = model.get_embedding(text)
                    if emb:
                        embeddings.append(
                            emb.tolist() if hasattr(emb, "tolist") else list(emb)
                        )
                except Exception:
                    embeddings.append([])

            return ColBERTIndexResult(
                chunks=chunks,
                vectors=embeddings,
                metadata={
                    "model": self.model_name,
                    "dim": len(embeddings[0]) if embeddings else 0,
                    "count": len(embeddings),
                },
            )
        except Exception as e:
            return ColBERTIndexResult(
                chunks=chunks, vectors=[], metadata={"error": str(e)}
            )

    def index(self, chunks: List[Chunk], source_id: str) -> ColBERTIndexResult:
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
                        emb = model.get_embedding(text)
                        if emb:
                            embeddings.append(
                                emb.tolist() if hasattr(emb, "tolist") else list(emb)
                            )
                    except Exception:
                        embeddings.append([])

            return ColBERTIndexResult(
                chunks=chunks,
                vectors=embeddings,
                metadata={
                    "model": self.model_name,
                    "dim": len(embeddings[0]) if embeddings else 0,
                    "count": len(embeddings),
                    "took_ms": int((time.time() - start) * 1000),
                },
            )
        except Exception as e:
            return ColBERTIndexResult(
                chunks=chunks, vectors=[], metadata={"error": str(e)}
            )


class ColBERTRetriever:
    """Retriever using ColBERT late interaction scoring."""

    def __init__(self, indexer: ColBERTIndexer):
        self.indexer = indexer

    def compute_scores(
        self,
        query_emb: List[float],
        doc_embeddings: List[List[float]],
    ) -> List[float]:
        """Compute late interaction similarity scores."""
        if not doc_embeddings:
            return []

        scores = []
        for doc_emb in doc_embeddings:
            if not doc_emb or not query_emb:
                scores.append(0.0)
                continue

            min_len = min(len(query_emb), len(doc_emb))
            score = sum(
                max(0, query_emb[j] * doc_emb[j]) for j in range(min_len)
            ) / max(1, sum(v * v for v in query_emb[:min_len]) ** 0.5)
            scores.append(score)

        return scores

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
            query_emb = model.get_embedding(query)
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

            scores = self.compute_scores(query_emb, doc_result.vectors)
            if scores:
                max_score = max(scores)
                results.append(
                    {
                        "doc_id": doc_id,
                        "score": max_score,
                        "chunks": doc_result.chunks,
                    }
                )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


def get_colbert_indexer(
    model_name: str = "colbert-ir/colbertv2.0",
) -> Optional[ColBERTIndexer]:
    if not COLBERT_AVAILABLE:
        return None
    return ColBERTIndexer(model_name=model_name)


def get_colbert_retriever(
    indexer: Optional[ColBERTIndexer] = None,
) -> Optional[ColBERTRetriever]:
    if indexer is None:
        indexer = get_colbert_indexer()
    if indexer is None:
        return None
    return ColBERTRetriever(indexer)
