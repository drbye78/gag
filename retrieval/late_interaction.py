"""
Late Interaction Retriever - ColPali-based visual retrieval.

Uses ColPali's late interaction mechanism for visual-first document retrieval.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from documents.colpali import get_colpali_client, ColPaliModel, ColPaliSearchResult


@dataclass
class LateInteractionResult:
    query: str
    results: List[Dict[str, Any]]
    took_ms: int = 0
    error: Optional[str] = None
    model: str = ""


class LateInteractionRetriever:
    def __init__(
        self,
        model: str = ColPaliModel.COLQWEN2.value,
        index_name: str = "colpali_docs",
    ):
        self.model = model
        self.index_name = index_name
        self._client = get_colpali_client(model)
        self._indexed_docs: List[Dict[str, Any]] = []

    @property
    def available(self) -> bool:
        return self._client.available

    async def index_document(
        self,
        content: Any,
        doc_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result = await self._client.index_document(content, doc_id)
        result["metadata"] = metadata or {}
        self._indexed_docs.append(result)
        return result

    async def index_documents(
        self,
        documents: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        for doc in documents:
            await self.index_document(
                doc.get("content"),
                doc.get("doc_id", doc.get("id", f"doc_{len(self._indexed_docs)}")),
                doc.get("metadata"),
            )
        return {"indexed": len(documents), "total": len(self._indexed_docs)}

    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> LateInteractionResult:
        start = int(time.time() * 1000)

        if not self._indexed_docs:
            return LateInteractionResult(
                query=query,
                results=[],
                error="No documents indexed",
            )

        result = await self._client.search(query, self._indexed_docs, top_k=limit)

        return LateInteractionResult(
            query=result.query,
            results=[
                {"doc_id": r.doc_id, "score": r.score, "metadata": r.metadata}
                for r in result.results
            ],
            took_ms=result.took_ms,
            error=result.error,
            model=self.model,
        )

    def clear_index(self):
        self._indexed_docs = []

    def get_index_size(self) -> int:
        return len(self._indexed_docs)


_late_retriever: Optional[LateInteractionRetriever] = None


def get_late_interaction_retriever(
    model: str = ColPaliModel.COLQWEN2.value,
) -> LateInteractionRetriever:
    global _late_retriever
    if _late_retriever is None:
        _late_retriever = LateInteractionRetriever(model=model)
    return _late_retriever
