from retrieval.rerank.base import BaseReranker, RerankResult, RerankProvider

import os
from typing import Any, Dict, List, Optional


class CohereReranker(BaseReranker):
    def __init__(
        self,
        model: str = "rerank-multilingual-v3.0",
        api_key: Optional[str] = None,
        top_n: int = 10,
    ):
        self.model = model
        self.api_key = api_key
        self.top_n = top_n

    @property
    def provider(self) -> RerankProvider:
        return RerankProvider.COHERE

    @property
    def available(self) -> bool:
        import os

        return bool(os.getenv("COHERE_API_KEY"))

    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_n: Optional[int] = None,
    ) -> List[RerankResult]:
        if not self.api_key:
            self.api_key = os.getenv("COHERE_API_KEY")

        if not self.api_key:
            return self._fallback_results(results, top_n)

        import httpx

        docs = [r.get("content", r.get("text", "")) for r in results]

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.cohere.com/v1/rerank",
                    json={
                        "query": query,
                        "documents": docs,
                        "model": self.model,
                        "top_n": top_n or self.top_n,
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=30.0,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return self._fallback_results(results, top_n)

        reranked = []
        for i, r in enumerate(data.get("results", [])):
            orig = results[r["index"]]
            reranked.append(
                RerankResult(
                    node_id=orig.get("id", str(r["index"])),
                    content=orig.get("content", ""),
                    score=r["relevance_score"],
                    original_rank=r["index"],
                    new_rank=i,
                    source=orig.get("source", "cohere"),
                    metadata=orig.get("metadata", {}),
                )
            )

        return reranked

    def _fallback_results(
        self,
        results: List[Dict[str, Any]],
        top_n: Optional[int],
    ) -> List[RerankResult]:
        return [
            RerankResult(
                node_id=r.get("id", str(i)),
                content=r.get("content", ""),
                score=r.get("score", 0.5),
                original_rank=i,
                new_rank=i,
                source=r.get("source", "unknown"),
                metadata=r.get("metadata", {}),
            )
            for i, r in enumerate(results[: top_n or len(results)])
        ]


class BGEReranker(BaseReranker):
    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: str = "cpu",
        use_fp16: bool = False,
    ):
        self.model_name = model_name
        self.device = device
        self.use_fp16 = use_fp16
        self._model = None

    @property
    def provider(self) -> RerankProvider:
        return RerankProvider.BGE

    @property
    def available(self) -> bool:
        try:
            from sentence_transformers import CrossEncoder

            return True
        except ImportError:
            return False

    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_n: Optional[int] = None,
    ) -> List[RerankResult]:
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name, device=self.device)

        docs = [r.get("content", r.get("text", "")) for r in results]
        pairs = [(query, doc) for doc in docs]

        scores = self._model.predict(pairs)

        ranked = sorted(zip(results, scores), key=lambda x: x[1], reverse=True)

        reranked = []
        for new_rank, (orig, score) in enumerate(ranked[: top_n or len(results)]):
            reranked.append(
                RerankResult(
                    node_id=orig.get("id", str(new_rank)),
                    content=orig.get("content", ""),
                    score=float(score),
                    original_rank=0,
                    new_rank=new_rank,
                    source=orig.get("source", "bge"),
                    metadata=orig.get("metadata", {}),
                )
            )

        return reranked


class SentenceTransformerReranker(BaseReranker):
    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-base",
        device: str = "cpu",
    ):
        self.model_name = model_name
        self.device = device
        self._model = None

    @property
    def provider(self) -> RerankProvider:
        return RerankProvider.SENTENCE_TRANSFORMER

    @property
    def available(self) -> bool:
        try:
            from sentence_transformers import CrossEncoder

            return True
        except ImportError:
            return False

    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_n: Optional[int] = None,
    ) -> List[RerankResult]:
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name, device=self.device)

        docs = [r.get("content", r.get("text", "")) for r in results]
        pairs = [(query, doc) for doc in docs]

        scores = self._model.predict(pairs)

        ranked = sorted(zip(results, scores), key=lambda x: x[1], reverse=True)

        reranked = []
        for new_rank, (orig, score) in enumerate(ranked[: top_n or len(results)]):
            reranked.append(
                RerankResult(
                    node_id=orig.get("id", str(new_rank)),
                    content=orig.get("content", ""),
                    score=float(score),
                    original_rank=0,
                    new_rank=new_rank,
                    source=orig.get("source", "sentence_transformer"),
                    metadata=orig.get("metadata", {}),
                )
            )

        return reranked


class JinaReranker(BaseReranker):
    def __init__(
        self,
        model: str = "jina-reranker-v1-base-en",
        api_key: Optional[str] = None,
        top_n: int = 10,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        self.top_n = top_n

    @property
    def provider(self) -> RerankProvider:
        return RerankProvider.JINA

    @property
    def available(self) -> bool:
        return bool(os.getenv("JINA_API_KEY"))

    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_n: Optional[int] = None,
    ) -> List[RerankResult]:
        if not self.api_key:
            return self._fallback_results(results, top_n)

        import httpx

        docs = [r.get("content", r.get("text", "")) for r in results]

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.jina.ai/v1/rerank",
                    json={
                        "query": query,
                        "documents": docs,
                        "model": self.model,
                        "top_n": top_n or self.top_n,
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=30.0,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return self._fallback_results(results, top_n)

        reranked = []
        for i, r in enumerate(data.get("results", [])):
            orig = results[r["index"]]
            reranked.append(
                RerankResult(
                    node_id=orig.get("id", str(r["index"])),
                    content=orig.get("content", ""),
                    score=r["relevance_score"],
                    original_rank=r["index"],
                    new_rank=i,
                    source=orig.get("source", "jina"),
                    metadata=orig.get("metadata", {}),
                )
            )

        return reranked

    def _fallback_results(
        self,
        results: List[Dict[str, Any]],
        top_n: Optional[int],
    ) -> List[RerankResult]:
        return [
            RerankResult(
                node_id=r.get("id", str(i)),
                content=r.get("content", ""),
                score=r.get("score", 0.5),
                original_rank=i,
                new_rank=i,
                source=r.get("source", "unknown"),
                metadata=r.get("metadata", {}),
            )
            for i, r in enumerate(results[: top_n or len(results)])
        ]


class LlamaIndexReranker(BaseReranker):
    def __init__(self, top_n: int = 10):
        self.top_n = top_n
        self._reranker = None

    @property
    def provider(self) -> RerankProvider:
        return RerankProvider.LLAMA_INDEX

    @property
    def available(self) -> bool:
        try:
            from llama_index.core import Document

            return True
        except ImportError:
            return False

    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_n: Optional[int] = None,
    ) -> List[RerankResult]:
        try:
            from llama_index.core import TextNode, NodeWithScore
            from llama_index.retrievers.reranker import FlashRankReranker
        except ImportError:
            return self._fallback_results(results, top_n)

        if self._reranker is None:
            self._reranker = FlashRankReranker(top_k=top_n or self.top_n)

        nodes = [
            NodeWithScore(
                node=TextNode(text=r.get("content", ""), id=r.get("id", str(i))),
                score=r.get("score", 1.0),
            )
            for i, r in enumerate(results)
        ]

        reranked = await self._reranker.arerank(nodes, query_string=query)

        return [
            RerankResult(
                node_id=n.node.id_,
                content=n.node.text,
                score=n.score or 0.0,
                original_rank=i,
                new_rank=i,
                source="llama_index",
                metadata={},
            )
            for i, n in enumerate(reranked)
        ]

    def _fallback_results(
        self,
        results: List[Dict[str, Any]],
        top_n: Optional[int],
    ) -> List[RerankResult]:
        return [
            RerankResult(
                node_id=r.get("id", str(i)),
                content=r.get("content", ""),
                score=r.get("score", 0.5),
                original_rank=i,
                new_rank=i,
                source=r.get("source", "unknown"),
                metadata=r.get("metadata", {}),
            )
            for i, r in enumerate(results[: top_n or len(results)])
        ]


def get_available_rerankers():
    rerankers = {}
    for cls in [
        CohereReranker,
        BGEReranker,
        SentenceTransformerReranker,
        JinaReranker,
        LlamaIndexReranker,
    ]:
        r = cls()
        if r.available:
            rerankers[r.provider] = r
    return rerankers
