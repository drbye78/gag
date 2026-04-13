"""
Diagram Retriever - Search and understand architecture diagrams.

Integrates with hybrid retrieval for diagram-aware search.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from documents.diagram_parser import (
    get_diagram_parser,
    DiagramType,
    DiagramExtractionResult,
)


@dataclass
class DiagramSearchResult:
    doc_id: str
    score: float
    diagram_type: str
    entities: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    generated_code: str = ""


@dataclass
class DiagramRetrievalResult:
    query: str
    results: List[DiagramSearchResult]
    detected_type: str = ""
    took_ms: int = 0
    error: Optional[str] = None


class DiagramRetriever:
    def __init__(self):
        self._parser = get_diagram_parser()
        self._indexed: List[Dict[str, Any]] = []

    async def index_diagram(
        self,
        image_content: Any,
        doc_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result = await self._parser.parse_image(image_content)

        indexed = {
            "doc_id": doc_id,
            "diagram_type": result.diagram_type.value,
            "entities": result.entities,
            "relationships": result.relationships,
            "generated_code": result.generated_code,
            "metadata": metadata or {},
        }
        self._indexed.append(indexed)

        return indexed

    async def index_text_diagram(
        self,
        text: str,
        doc_id: str,
        diagram_type: Optional[DiagramType] = None,
    ) -> Dict[str, Any]:
        result = await self._parser.parse_from_text(text, diagram_type)

        indexed = {
            "doc_id": doc_id,
            "diagram_type": result.diagram_type.value,
            "entities": result.entities,
            "relationships": result.relationships,
            "generated_code": result.generated_code,
        }
        self._indexed.append(indexed)

        return indexed

    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> DiagramRetrievalResult:
        start = int(time.time() * 1000)

        if not self._indexed:
            return DiagramRetrievalResult(
                query=query, results=[], error="No diagrams indexed"
            )

        scores = []
        query_lower = query.lower()

        for doc in self._indexed:
            score = 0.0

            for ent in doc.get("entities", []):
                name = ent.get("name", "").lower()
                if name and name in query_lower:
                    score += 1.0

            for rel in doc.get("relationships", []):
                for_val = rel.get("from", "").lower()
                to_val = rel.get("to", "").lower()
                if (for_val and for_val in query_lower) or (
                    to_val and to_val in query_lower
                ):
                    score += 0.5

            scores.append((doc, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for doc, score in scores[:limit]:
            results.append(
                DiagramSearchResult(
                    doc_id=doc.get("doc_id", ""),
                    score=score,
                    diagram_type=doc.get("diagram_type", ""),
                    entities=doc.get("entities", []),
                    relationships=doc.get("relationships", []),
                    generated_code=doc.get("generated_code", ""),
                )
            )

        return DiagramRetrievalResult(
            query=query,
            results=results,
            detected_type=results[0].diagram_type if results else "",
            took_ms=int(time.time() * 1000) - start,
        )

    def get_entities_by_type(self, diagram_type: str) -> List[Dict[str, Any]]:
        entities = []
        for doc in self._indexed:
            if doc.get("diagram_type") == diagram_type:
                entities.extend(doc.get("entities", []))
        return entities

    def get_relationships(self) -> List[Dict[str, Any]]:
        rels = []
        for doc in self._indexed:
            rels.extend(doc.get("relationships", []))
        return rels

    def clear_index(self):
        self._indexed = []

    def get_index_size(self) -> int:
        return len(self._indexed)


_diagram_retriever: Optional[DiagramRetriever] = None


def get_diagram_retriever() -> DiagramRetriever:
    global _diagram_retriever
    if _diagram_retriever is None:
        _diagram_retriever = DiagramRetriever()
    return _diagram_retriever
