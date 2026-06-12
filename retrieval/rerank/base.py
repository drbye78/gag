from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class RerankProvider(str, Enum):
    COHERE = "cohere"
    BGE = "bge-reranker"
    LLAMA_INDEX = "llama_index"
    SENTENCE_TRANSFORMER = "sentence_transformer"
    CROSS_ENCODER = "cross_encoder"
    JINA = "jina"


@dataclass
class RerankResult:
    node_id: str
    content: str
    score: float
    original_rank: int
    new_rank: int
    source: str
    metadata: Dict[str, Any]


class BaseReranker(ABC):
    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_n: Optional[int] = None,
    ) -> List[RerankResult]: ...

    async def rerank_batch(
        self,
        queries: List[str],
        results_list: List[List[Dict[str, Any]]],
        top_n: Optional[int] = None,
    ) -> List[List[RerankResult]]:
        """Rerank multiple query-result pairs.

        Default implementation calls rerank() for each pair sequentially.
        Subclasses may override for more efficient batched processing.
        """
        batch_results: List[List[RerankResult]] = []
        for query, results in zip(queries, results_list):
            batch_results.append(await self.rerank(query, results, top_n))
        return batch_results

    @property
    @abstractmethod
    def provider(self) -> RerankProvider: ...

    @property
    def available(self) -> bool:
        return True
