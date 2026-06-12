"""
Retrieval Orchestrator - Multi-source retrieval coordination.

Coordinates parallel retrieval across docs, code,
graph, tickets, and telemetry sources.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from core.adapters import get_adapter_registry
from core.text_utils import TextLanguage, detect_language, normalize_text
from models.retrieval import RetrievalSource
from retrieval.classifier import get_query_classifier
from retrieval.code import get_code_retriever
from retrieval.code_graph import get_code_graph_retriever
from retrieval.colbert import get_colbert_search_client
from retrieval.diagram import get_diagram_retriever
from retrieval.docs import get_docs_retriever
from retrieval.graph import get_graph_retriever
from retrieval.hybrid import get_hybrid_retriever
from retrieval.knowledge import get_knowledge_retriever
from retrieval.telemetry import get_telemetry_retriever
from retrieval.ticket import get_ticket_retriever

logger = logging.getLogger(__name__)


class RetrievalMode(str, Enum):
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    HYBRID = "hybrid"
    MULTI_HOP = "multi_hop"


class RetrievalOrchestrator:
    def __init__(self, sources: Optional[List[Any]] = None):
        self.docs_retriever = get_docs_retriever()
        self.code_retriever = get_code_retriever()
        self.graph_retriever = get_graph_retriever()
        self.code_graph_retriever = get_code_graph_retriever()
        self.ticket_retriever = get_ticket_retriever()
        self.telemetry_retriever = get_telemetry_retriever()
        self.diagram_retriever = get_diagram_retriever()
        self.hybrid_retriever = get_hybrid_retriever()
        self.classifier = get_query_classifier()
        from ui.retriever import get_ui_retriever

        self.ui_retriever = get_ui_retriever()
        self.colbert_retriever = get_colbert_search_client()
        self.knowledge_retriever = get_knowledge_retriever()
        self.adapter_registry = get_adapter_registry()
        # Configurable source list (defaults to all known sources)
        self._sources = sources

    async def retrieve(
        self,
        query: str,
        sources: Optional[List[RetrievalSource]] = None,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)

        normalized_query = self._preprocess_query(query)
        if normalized_query != query:
            query = normalized_query

        if not sources:
            sources = self._sources if self._sources is not None else list(RetrievalSource)

        tasks = []
        for source in sources:
            if source == RetrievalSource.DOCS:
                tasks.append(self._retrieve_docs(query, limit, filters))
            elif source == RetrievalSource.CODE:
                tasks.append(self._retrieve_code(query, limit, filters))
            elif source == RetrievalSource.GRAPH:
                tasks.append(self._retrieve_graph(query, limit, filters))
            elif source == RetrievalSource.CODE_GRAPH:
                tasks.append(self._retrieve_code_graph(query, limit, filters))
            elif source == RetrievalSource.TICKETS:
                tasks.append(self._retrieve_tickets(query, limit, filters))
            elif source == RetrievalSource.TELEMETRY:
                tasks.append(self._retrieve_telemetry(query, limit, filters))
            elif source == RetrievalSource.DIAGRAM:
                tasks.append(self._retrieve_diagram(query, limit, filters))
            elif source == RetrievalSource.UI_SKETCH:
                tasks.append(self._retrieve_ui(query, limit, filters))
            elif source == RetrievalSource.COLBERT:
                tasks.append(self._retrieve_colbert(query, limit, filters))
            elif source == RetrievalSource.KNOWLEDGE:
                tasks.append(self._retrieve_knowledge(query, limit, filters))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = []
        errors = []
        failed_sources = []
        for source, r in zip(sources, results):
            if isinstance(r, Exception):
                errors.append({"error": str(r), "type": type(r).__name__, "source": source.value})
                failed_sources.append(source.value)
            else:
                valid_results.append(r)

        total = sum(r.get("total", 0) for r in valid_results)

        took = int(time.time() * 1000) - start

        has_partial_failure = len(errors) > 0 and len(valid_results) > 0
        if has_partial_failure:
            logger.warning(
                "Partial retrieval failure: %d of %d sources failed (%s)",
                len(failed_sources),
                len(sources),
                ", ".join(failed_sources),
            )

        return {
            "query": query,
            "results": valid_results,
            "total_results": total,
            "took_ms": took,
            "errors": errors,
            "success": len(errors) == 0,
            "partial_failure": has_partial_failure,
            "failed_sources": failed_sources,
            "successful_sources": [s.value for s in sources if s.value not in failed_sources],
        }

    async def _retrieve_docs(self, query: str, limit: int, filters: Optional[Dict]) -> Dict:
        try:
            return await self.docs_retriever.search(query, limit, filters=filters)
        except Exception as e:
            logger.exception("docs retrieval failed")
            return {"source": "docs", "results": [], "total": 0, "took_ms": 0}

    async def _retrieve_code(self, query: str, limit: int, filters: Optional[Dict]) -> Dict:
        try:
            return await self.code_retriever.search(query, limit, filters=filters)
        except Exception as e:
            logger.exception("code retrieval failed")
            return {"source": "code", "results": [], "total": 0, "took_ms": 0}

    async def _retrieve_graph(self, query: str, limit: int, filters: Optional[Dict]) -> Dict:
        try:
            return await self.graph_retriever.search(query, limit=limit)
        except Exception as e:
            logger.exception("graph retrieval failed")
            return {"source": "graph", "results": [], "total": 0, "took_ms": 0}

    async def _retrieve_code_graph(self, query: str, limit: int, filters: Optional[Dict]) -> Dict:
        try:
            return await self.code_graph_retriever.search(query, limit=limit)
        except Exception as e:
            logger.exception("code_graph retrieval failed")
            return {"source": "code_graph", "results": [], "total": 0, "took_ms": 0}

    async def _retrieve_tickets(self, query: str, limit: int, filters: Optional[Dict]) -> Dict:
        try:
            return await self.ticket_retriever.search(query, limit=limit)
        except Exception as e:
            logger.exception("tickets retrieval failed")
            return {"source": "tickets", "results": [], "total": 0, "took_ms": 0}

    async def _retrieve_telemetry(self, query: str, limit: int, filters: Optional[Dict]) -> Dict:
        try:
            return await self.telemetry_retriever.search_events(query, limit=limit)
        except Exception as e:
            logger.exception("telemetry retrieval failed")
            return {"source": "telemetry", "results": [], "total": 0, "took_ms": 0}

    async def _retrieve_diagram(self, query: str, limit: int, filters: Optional[Dict]) -> Dict:
        try:
            return await self.diagram_retriever.search_diagrams(query, limit=limit)
        except Exception as e:
            logger.exception("diagram retrieval failed")
            return {"source": "diagram", "results": [], "total": 0, "took_ms": 0}

    async def _retrieve_ui(self, query: str, limit: int, filters: Optional[Dict]) -> Dict:
        try:
            results = await self.ui_retriever.search_combined(
                element_types=[query.lower()], limit=limit
            )
            return {"source": "ui_sketch", "results": results, "total": len(results), "took_ms": 0}
        except Exception as e:
            logger.exception("ui_sketch retrieval failed")
            return {"source": "ui_sketch", "results": [], "total": 0, "took_ms": 0}

    async def _retrieve_colbert(self, query: str, limit: int, filters: Optional[Dict]) -> Dict:
        try:
            if self.colbert_retriever:
                result = await self.colbert_retriever.search(query, limit=limit)
                results = result.get("results", [])
                return {
                    "source": "colbert",
                    "results": results,
                    "total": len(results),
                    "took_ms": result.get("took_ms", 0),
                }
            return {"source": "colbert", "results": [], "total": 0, "took_ms": 0}
        except Exception as e:
            logger.exception("colbert retrieval failed")
            return {"source": "colbert", "results": [], "total": 0, "took_ms": 0}

    async def _retrieve_knowledge(self, query: str, limit: int, filters: Optional[Dict]) -> Dict:
        try:
            result = await self.knowledge_retriever.search(query, limit=limit, filters=filters)
            return result
        except Exception as e:
            logger.exception("knowledge retrieval failed")
            return {"source": "knowledge", "results": [], "total": 0, "took_ms": 0}

    def detect_platform_from_query(self, query: str) -> List[str]:
        query_lower = query.lower()
        return self.knowledge_retriever._detect_platforms(query_lower)

    async def route_hybrid(
        self,
        query: str,
        mode: RetrievalMode = RetrievalMode.HYBRID,
        limit: int = 10,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)

        return await self.hybrid_retriever.search(
            query=query,
            limit=limit,
            use_reasoning=True,
        )

    def _preprocess_query(self, query: str) -> str:
        lang = detect_language(query)
        if lang == TextLanguage.RUSSIAN:
            return normalize_text(query, language=TextLanguage.RUSSIAN)
        if lang == TextLanguage.ENGLISH:
            return normalize_text(query, language=TextLanguage.ENGLISH)
        return normalize_text(query)

    async def route_by_intent(
        self,
        query: str,
        intent: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        return await self.hybrid_retriever.search_by_intent(
            query=query,
            intent=intent,
            limit=limit,
        )


class RetrievalRouter:
    def __init__(self):
        self.orchestrator = RetrievalOrchestrator()
        self.default_sources = [
            RetrievalSource.DOCS,
            RetrievalSource.CODE,
            RetrievalSource.GRAPH,
            RetrievalSource.CODE_GRAPH,
            RetrievalSource.TICKETS,
            RetrievalSource.TELEMETRY,
            RetrievalSource.DIAGRAM,
            RetrievalSource.UI_SKETCH,
            RetrievalSource.KNOWLEDGE,
        ]

    def get_platform_recommendation(self, query: str) -> List[str]:
        detected = self.orchestrator.detect_platform_from_query(query)
        if not detected:
            detected = self._infer_from_adapters(query)
        return detected

    def _infer_from_adapters(self, query: str) -> List[str]:
        query_lower = query.lower()
        recommendations = []
        adapters = self.orchestrator.adapter_registry.list_adapters()
        for adapter in adapters:
            for service in adapter.supported_services:
                if service.lower() in query_lower:
                    recommendations.append(adapter.platform_id)
                    break
        return list(set(recommendations))

    async def route(
        self,
        query: str,
        sources: Optional[List[RetrievalSource]] = None,
        parallel: bool = True,
        merge: bool = True,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not sources:
            sources = self.default_sources

        if parallel:
            return await self.orchestrator.retrieve(query, sources, limit, filters)

        results = []
        for source in sources:
            source_result = await self.orchestrator.retrieve(query, [source], limit, filters)
            results.append(source_result)

        return {
            "query": query,
            "results": results,
            "total_results": sum(r.get("total_results", 0) for r in results),
            "took_ms": sum(r.get("took_ms", 0) for r in results),
        }

    def get_available_sources(self) -> List[str]:
        return [s.value for s in self.default_sources]


_orchestrator: Optional[RetrievalOrchestrator] = None
_router: Optional[RetrievalRouter] = None


def get_retrieval_orchestrator() -> RetrievalOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = RetrievalOrchestrator()
    return _orchestrator


def get_retrieval_router() -> RetrievalRouter:
    global _router
    if _router is None:
        _router = RetrievalRouter()
    return _router
