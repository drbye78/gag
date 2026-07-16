from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


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

    @property
    @abstractmethod
    def provider(self) -> RerankProvider: ...

    @property
    def available(self) -> bool:
        return True
