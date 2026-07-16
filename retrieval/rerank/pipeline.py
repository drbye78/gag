from typing import List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from retrieval.rerank.base import BaseReranker, RerankResult, RerankProvider
from retrieval.rerank.providers import (
    CohereReranker,
    BGEReranker,
    SentenceTransformerReranker,
    JinaReranker,
    LlamaIndexReranker,
    get_available_rerankers,
)


class RerankStrategy(str, Enum):
    SINGLE = "single"
    CASCADE = "cascade"
    ENSEMBLE = "ensemble"


@dataclass
class RerankConfig:
    strategy: RerankStrategy = RerankStrategy.CASCADE
    top_k: int = 10
    min_score: float = 0.0
    providers: Optional[List[RerankProvider]] = None

    def __post_init__(self):
        if self.providers is None:
            self.providers = [
                RerankProvider.COHERE,
                RerankProvider.BGE,
                RerankProvider.LLAMA_INDEX,
            ]


class RerankPipeline:
    def __init__(
        self,
        config: Optional[RerankConfig] = None,
    ):
        self.config = config or RerankConfig()
        self._rerankers: dict = {}
        self._init_rerankers()

    def _init_rerankers(self):
        available = get_available_rerankers()
        for provider in self.config.providers:
            if provider in available:
                self._rerankers[provider] = available[provider]

    async def rerank(
        self,
        query: str,
        results: List[dict],
    ) -> List[RerankResult]:
        if not results:
            return []

        if self.config.strategy == RerankStrategy.SINGLE:
            return await self._single_rerank(query, results)
        elif self.config.strategy == RerankStrategy.CASCADE:
            return await self._cascade_rerank(query, results)
        elif self.config.strategy == RerankStrategy.ENSEMBLE:
            return await self._ensemble_rerank(query, results)

        return self._fallback_results(results)

    async def _single_rerank(
        self,
        query: str,
        results: List[dict],
    ) -> List[RerankResult]:
        for provider, reranker in self._rerankers.items():
            try:
                return await reranker.rerank(query, results, self.config.top_k)
            except Exception:
                continue
        return self._fallback_results(results)

    async def _cascade_rerank(
        self,
        query: str,
        results: List[dict],
    ) -> List[RerankResult]:
        best_results = results

        for provider, reranker in self._rerankers.items():
            try:
                reranked = await reranker.rerank(query, best_results, self.config.top_k)
                if reranked and len(reranked) >= len(best_results) * 0.3:
                    best_results = [
                        {
                            "content": r.content,
                            "score": r.score,
                            "id": r.node_id,
                            "source": r.source,
                        }
                        for r in reranked
                    ]
            except Exception:
                continue

        return [
            RerankResult(
                node_id=r.get("id", str(i)),
                content=r.get("content", ""),
                score=r.get("score", 0.5),
                original_rank=i,
                new_rank=i,
                source=r.get("source", "cascade"),
                metadata={},
            )
            for i, r in enumerate(best_results[: self.config.top_k])
        ]

    async def _ensemble_rerank(
        self,
        query: str,
        results: List[dict],
    ) -> List[RerankResult]:
        all_scores = {}

        for provider, reranker in self._rerankers.items():
            try:
                reranked = await reranker.rerank(query, results)
                for r in reranked:
                    if r.node_id not in all_scores:
                        all_scores[r.node_id] = []
                    all_scores[r.node_id].append((r.score, r.content))
            except Exception:
                continue

        if not all_scores:
            return self._fallback_results(results)

        ensemble_results = []
        for node_id, scores_content in all_scores.items():
            avg_score = sum(s[0] for s in scores_content) / len(scores_content)
            content = scores_content[0][1]
            ensemble_results.append((node_id, content, avg_score))

        ensemble_results.sort(key=lambda x: x[2], reverse=True)

        return [
            RerankResult(
                node_id=node_id,
                content=content,
                score=score,
                original_rank=i,
                new_rank=i,
                source="ensemble",
                metadata={},
            )
            for i, (node_id, content, score) in enumerate(
                ensemble_results[: self.config.top_k]
            )
        ]

    def _fallback_results(self, results: List[dict]) -> List[RerankResult]:
        return [
            RerankResult(
                node_id=r.get("id", str(i)),
                content=r.get("content", ""),
                score=r.get("score", 0.5),
                original_rank=i,
                new_rank=i,
                source=r.get("source", "fallback"),
                metadata=r.get("metadata", {}),
            )
            for i, r in enumerate(results[: self.config.top_k])
        ]


_rerank_pipeline: Optional[RerankPipeline] = None


def get_rerank_pipeline(config: Optional[RerankConfig] = None) -> RerankPipeline:
    global _rerank_pipeline
    if _rerank_pipeline is None:
        _rerank_pipeline = RerankPipeline(config)
    return _rerank_pipeline
