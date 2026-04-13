"""
Hybrid Retriever - Advanced multi-strategy retrieval.

Implements parallel, cascade, iterative retrieval strategies
with reasoning-guided query refinement.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from retrieval.classifier import (
    QueryClassifier,
    RetrievalStrategy,
    get_query_classifier,
)
from retrieval.fusion import FusionMethod, ResultFusion, get_result_fusion
from retrieval.reasoning import ReasoningEngine, ReasoningMode, get_reasoning_engine
from retrieval.docs import DocsRetriever, get_docs_retriever
from retrieval.graph import GraphRetriever, get_graph_retriever
from retrieval.code import CodeRetriever, get_code_retriever
from retrieval.code_graph import CodeGraphRetriever, get_code_graph_retriever
from retrieval.entity_centric import (
    EntityCentricRetriever,
    get_entity_centric_retriever,
)
from retrieval.rerank import get_rerank_pipeline, RerankConfig
from retrieval.citations import CitationBuilder, CitationStyle
from retrieval.entity_cache import (
    EntityGraphCache,
    EntityGraphCacheEntry,
    get_entity_graph_cache,
)
from retrieval.reasoning.entity_aware import get_entity_aware_reasoning_engine
from retrieval.reasoning.iterative import get_iterative_reasoning_engine


@dataclass
class RetrievalIteration:
    iteration: int
    query: str
    results: List[Dict[str, Any]]
    reasoning: str
    refined_query: Optional[str] = None
    score: float = 0.0


@dataclass
class CascadeStage:
    stage: str
    query: str
    results: List[Dict[str, Any]]
    refine_context: Dict[str, Any] = field(default_factory=dict)
    next_stage_query: Optional[str] = None


class HybridRetriever:
    def __init__(
        self,
        classifier: Optional[QueryClassifier] = None,
        fusion: Optional[ResultFusion] = None,
        reasoning: Optional[ReasoningEngine] = None,
    ):
        self.classifier = classifier or get_query_classifier()
        self.fusion = fusion or get_result_fusion(FusionMethod.RRF)
        self.reasoning = reasoning or get_reasoning_engine(
            ReasoningMode.CHAIN_OF_THOUGHTS
        )
        self.citation_builder = CitationBuilder()

        # Lazy-initialized retrievers — only created when first accessed
        self._docs_retriever: Optional[Any] = None
        self._code_retriever: Optional[Any] = None
        self._graph_retriever: Optional[Any] = None
        self._code_graph_retriever: Optional[Any] = None
        self._entity_centric_retriever: Optional[Any] = None
        self._reranker: Optional[Any] = None
        self._entity_reasoning: Optional[Any] = None
        self._iterative_reasoning: Optional[Any] = None

    # Lazy retriever properties
    @property
    def docs_retriever(self):
        if self._docs_retriever is None:
            self._docs_retriever = get_docs_retriever()
        return self._docs_retriever

    @property
    def code_retriever(self):
        if self._code_retriever is None:
            self._code_retriever = get_code_retriever()
        return self._code_retriever

    @property
    def graph_retriever(self):
        if self._graph_retriever is None:
            self._graph_retriever = get_graph_retriever()
        return self._graph_retriever

    @property
    def code_graph_retriever(self):
        if self._code_graph_retriever is None:
            self._code_graph_retriever = get_code_graph_retriever()
        return self._code_graph_retriever

    @property
    def entity_centric_retriever(self):
        if self._entity_centric_retriever is None:
            self._entity_centric_retriever = get_entity_centric_retriever()
        return self._entity_centric_retriever

    @property
    def reranker(self):
        if self._reranker is None:
            self._reranker = get_rerank_pipeline()
        return self._reranker

    @property
    def entity_reasoning(self):
        if self._entity_reasoning is None:
            self._entity_reasoning = get_entity_aware_reasoning_engine()
        return self._entity_reasoning

    @property
    def iterative_reasoning(self):
        if self._iterative_reasoning is None:
            self._iterative_reasoning = get_iterative_reasoning_engine()
        return self._iterative_reasoning

    async def search(
        self,
        query: str,
        limit: int = 10,
        use_reasoning: bool = True,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)

        classification = self.classifier.classify(query)
        strategy = classification.get("strategy", RetrievalStrategy.VECTOR_ONLY.value)

        if strategy == RetrievalStrategy.VECTOR_ONLY.value:
            return await self._vector_only_search(query, limit, start)
        elif strategy == RetrievalStrategy.GRAPH_ONLY.value:
            return await self._graph_only_search(query, limit, start)
        elif strategy == RetrievalStrategy.MULTI_HOP.value:
            return await self._multi_hop_search(query, limit, start)
        elif strategy == RetrievalStrategy.CASCADE.value:
            return await self._cascade_search(query, limit, start)
        elif strategy == RetrievalStrategy.ITERATIVE.value:
            return await self._iterative_search(query, limit, start, use_reasoning)
        else:
            return await self._hybrid_search(query, limit, start, use_reasoning)

    async def _vector_only_search(
        self,
        query: str,
        limit: int,
        start: int,
    ) -> Dict[str, Any]:
        docs_result = await self.docs_retriever.search(query, limit=limit)
        code_result = await self.code_retriever.search(query, limit=limit)

        source_results = {
            "docs": docs_result.get("results", []),
            "code": code_result.get("results", []),
        }
        fused = self.fusion.fuse(source_results)

        took = int(time.time() * 1000) - start

        return {
            "query": query,
            "results": fused[:limit],
            "total": len(fused),
            "strategy": "vector_only",
            "took_ms": took,
        }

    async def _graph_only_search(
        self,
        query: str,
        limit: int,
        start: int,
    ) -> Dict[str, Any]:
        graph_result = await self.graph_retriever.search(query, limit=limit)

        took = int(time.time() * 1000) - start

        return {
            "query": query,
            "results": graph_result.get("results", []),
            "total": graph_result.get("total", 0),
            "strategy": "graph_only",
            "took_ms": took,
        }

    async def _multi_hop_search(
        self,
        query: str,
        limit: int,
        start: int,
    ) -> Dict[str, Any]:
        graph_result = await self.graph_retriever.multi_hop_search(
            query=query,
            max_hops=3,
            limit=limit,
        )
        docs_result = await self.docs_retriever.search(query, limit=limit)

        source_results = {
            "graph": graph_result.get("results", []),
            "code": docs_result.get("results", []),
        }
        fused = self.fusion.fuse(source_results)

        took = int(time.time() * 1000) - start

        return {
            "query": query,
            "results": fused[:limit],
            "total": len(fused),
            "strategy": "multi_hop",
            "hops": graph_result.get("max_hops", 0),
            "took_ms": took,
        }

    async def _cascade_search(
        self,
        query: str,
        limit: int,
        start: int,
    ) -> Dict[str, Any]:
        stages = []

        stage1_docs = await self.docs_retriever.search(query, limit=limit // 2)
        refine_context = self._extract_refine_context(stage1_docs.get("results", []))

        refined_query = self._build_refined_query(query, refine_context)

        stage2_code = await self.code_retriever.search(refined_query, limit=limit // 2)

        combine_stage_dict = {
            "docs": stage1_docs.get("results", []),
            "code": stage2_code.get("results", []),
        }
        result = self.fusion.fuse(combine_stage_dict)

        stages.append(
            CascadeStage(
                stage="docs",
                query=query,
                results=stage1_docs.get("results", []),
            )
        )
        stages.append(
            CascadeStage(
                stage="code",
                query=refined_query,
                results=stage2_code.get("results", []),
                refine_context=refine_context,
                next_stage_query=refined_query,
            )
        )

        if refine_context.get("entity_names"):
            graph_query = f"{refined_query} {' '.join(refine_context['entity_names'])}"
            stage3_graph = await self.graph_retriever.search(
                graph_query, limit=limit // 2
            )
            stages.append(
                CascadeStage(
                    stage="graph",
                    query=graph_query,
                    results=stage3_graph.get("results", []),
                    refine_context=refine_context,
                )
            )

            source_results = {
                "docs": stage1_docs.get("results", []),
                "code": stage2_code.get("results", []),
                "graph": stage3_graph.get("results", []),
            }
            result = self.fusion.fuse(source_results)

        took = int(time.time() * 1000) - start

        return {
            "query": query,
            "results": result[:limit],
            "total": len(result),
            "strategy": "cascade",
            "stages": [
                {"stage": s.stage, "query": s.query, "result_count": len(s.results)}
                for s in stages
            ],
            "refine_context": refine_context,
            "took_ms": took,
        }

    async def _iterative_search(
        self,
        query: str,
        limit: int,
        start: int,
        use_reasoning: bool = True,
        max_iterations: int = 3,
    ) -> Dict[str, Any]:
        iterations = []
        current_query = query
        all_results = []

        for iteration in range(max_iterations):
            docs_result = await self.docs_retriever.search(current_query, limit=limit)
            code_result = await self.code_retriever.search(current_query, limit=limit)

            iteration_results = [
                *docs_result.get("results", []),
                *code_result.get("results", []),
            ]
            all_results.extend(iteration_results)

            reasoning_result = None
            refined_query = None

            if use_reasoning and iteration < max_iterations - 1:
                reasoning_result = await self.reasoning.reason(
                    query,
                    iteration_results,
                )

                reasoning_thinking = reasoning_result.get("answer", "")
                confidence = reasoning_result.get("confidence", 0.0)

                if confidence < 0.7 and iteration < max_iterations - 1:
                    refined_query = self._generate_refined_query(
                        query=query,
                        current_results=iteration_results,
                        reasoning=reasoning_thinking,
                        iteration=iteration + 1,
                    )
                    current_query = refined_query

                iterations.append(
                    RetrievalIteration(
                        iteration=iteration + 1,
                        query=current_query,
                        results=iteration_results,
                        reasoning=reasoning_thinking,
                        refined_query=refined_query,
                        score=confidence,
                    )
                )

                if confidence >= 0.8:
                    break
            else:
                iterations.append(
                    RetrievalIteration(
                        iteration=iteration + 1,
                        query=current_query,
                        results=iteration_results,
                        reasoning=reasoning_result.get("answer", "")
                        if reasoning_result
                        else "",
                        score=reasoning_result.get("confidence", 0.0)
                        if reasoning_result
                        else 0.0,
                    )
                )
                break

        unique_results = self._deduplicate_results(all_results)
        final_result = unique_results[:limit]

        took = int(time.time() * 1000) - start

        return {
            "query": query,
            "results": final_result,
            "total": len(unique_results),
            "strategy": "iterative",
            "iterations": [
                {
                    "iteration": i.iteration,
                    "query": i.query,
                    "result_count": len(i.results),
                    "reasoning": i.reasoning[:100],
                    "refined_query": i.refined_query,
                    "confidence": i.score,
                }
                for i in iterations
            ],
            "took_ms": took,
        }

    async def _hybrid_search(
        self,
        query: str,
        limit: int,
        start: int,
        use_reasoning: bool,
    ) -> Dict[str, Any]:
        graph_result = await self.graph_retriever.search(query, limit=limit)
        docs_result = await self.docs_retriever.search(query, limit=limit)
        code_result = await self.code_retriever.search(query, limit=limit)

        source_results = {
            "graph": graph_result.get("results", []),
            "docs": docs_result.get("results", []),
            "code": code_result.get("results", []),
        }
        fused = self.fusion.fuse(source_results)

        if use_reasoning:
            reasoning_result = await self.reasoning.reason(query, fused)
            answer = reasoning_result.get("answer", "")
            confidence = reasoning_result.get("confidence", 0.0)
            reasoning_steps = reasoning_result.get("steps", [])
        else:
            answer = fused[0].get("content", "") if fused else ""
            confidence = fused[0].get("score", 0.0) if fused else 0.0
            reasoning_steps = []

        took = int(time.time() * 1000) - start

        return {
            "query": query,
            "answer": answer,
            "results": fused[:limit],
            "total": len(fused),
            "strategy": "hybrid",
            "confidence": confidence,
            "reasoning_steps": len(reasoning_steps),
            "sources": {
                "graph": graph_result.get("total", 0),
                "docs": docs_result.get("total", 0),
                "code": code_result.get("total", 0),
            },
            "took_ms": took,
        }

    async def search_with_code_graph_fallback(
        self,
        query: str,
        limit: int = 10,
        use_reasoning: bool = True,
        primary_sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)

        sources = primary_sources or ["docs", "code", "graph"]

        source_results = {}
        for src in sources:
            if src == "docs":
                source_results[src] = await self.docs_retriever.search(
                    query, limit=limit
                )
            elif src == "code":
                source_results[src] = await self.code_retriever.search(
                    query, limit=limit
                )
            elif src == "graph":
                source_results[src] = await self.graph_retriever.search(
                    query, limit=limit
                )

        fused = self.fusion.fuse(source_results)

        total_results = sum(len(v.get("results", [])) for v in source_results.values())

        if total_results < limit and "code_graph" not in sources:
            cg_result = await self.code_graph_retriever.search(
                query, limit=limit - total_results
            )
            source_results["code_graph"] = cg_result
            fused.extend(cg_result.get("results", []))

        if use_reasoning and fused:
            reasoning_result = await self.reasoning.reason(query, fused[-limit:])
            answer = reasoning_result.get("answer", "")
            confidence = reasoning_result.get("confidence", 0.0)
        else:
            answer = fused[0].get("content", "") if fused else ""
            confidence = fused[0].get("score", 0.0) if fused else 0.0

        took = int(time.time() * 1000) - start

        return {
            "query": query,
            "answer": answer,
            "results": fused[:limit],
            "total": len(fused),
            "strategy": "hybrid_with_code_graph_fallback",
            "confidence": confidence,
            "sources": source_results,
            "took_ms": took,
        }

    async def search_by_intent(
        self,
        query: str,
        intent: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        if intent == "relationship":
            return await self._multi_hop_search(query, limit, int(time.time() * 1000))
        elif intent == "causal":
            result = await self.graph_retriever.find_relationships(
                source=query.split()[0],
                target=query.split()[-1],
            )
            return {"query": query, "intent": intent, "paths": result.get("paths", [])}
        elif intent == "list":
            docs_result = await self.docs_retriever.search(query, limit=limit)
            return {
                "query": query,
                "intent": intent,
                "results": docs_result.get("results", []),
            }
        else:
            return await self._vector_only_search(query, limit, int(time.time() * 1000))

    def _extract_refine_context(
        self,
        results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        entity_names = set()
        keywords = set()

        for result in results:
            content = result.get("content", "")
            for word in content.split():
                if word[0].isupper() and len(word) > 2:
                    entity_names.add(word)
                if len(word) > 5:
                    keywords.add(word)

        return {
            "entity_names": list(entity_names)[:10],
            "keywords": list(keywords)[:10],
            "result_count": len(results),
        }

    def _build_refined_query(
        self,
        original_query: str,
        context: Dict[str, Any],
    ) -> str:
        parts = [original_query]

        if context.get("entity_names"):
            parts.extend(context["entity_names"][:3])

        if context.get("keywords"):
            parts.extend(context["keywords"][:3])

        return " ".join(parts)

    def _generate_refined_query(
        self,
        query: str,
        current_results: List[Dict[str, Any]],
        reasoning: str,
        iteration: int,
    ) -> str:
        missing_terms = []

        if "not found" in reasoning.lower() or "insufficient" in reasoning.lower():
            if current_results:
                found_content = " ".join(
                    r.get("content", "")[:200] for r in current_results[:3]
                )
                missing_terms.append(found_content)

        context_from_results = " ".join(
            r.get("content", "")[:100] for r in current_results[:2]
        )

        return f"{query} {context_from_results}".strip()[:500]

    def _deduplicate_results(
        self,
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        seen = set()
        unique = []

        for result in results:
            content = result.get("content", "")
            source = result.get("source", "")
            key = f"{source}:{content[:100]}"

            if key not in seen:
                seen.add(key)
                unique.append(result)

        return unique

    async def search_with_reranking(
        self,
        query: str,
        limit: int = 10,
        use_reasoning: bool = True,
        rerank: bool = True,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)

        initial_results = await self._hybrid_search(
            query, limit=limit * 2, start=start, use_reasoning=use_reasoning
        )
        results_list = initial_results.get("results", [])

        if not rerank:
            took = int(time.time() * 1000) - start
            return {
                "query": query,
                "results": results_list[:limit],
                "reranked": False,
                "took_ms": took,
            }

        reranked = await self.reranker.rerank(query, results_list)

        answer = reranked[0].content if reranked else ""
        results_as_dicts = [
            {
                "content": r.content,
                "score": r.score,
                "id": r.node_id,
                "source": r.source,
                "metadata": r.metadata,
            }
            for r in reranked[:limit]
        ]
        annotated = self.citation_builder.build(answer, results_as_dicts)

        took = int(time.time() * 1000) - start

        return {
            "query": query,
            "answer": annotated.answer,
            "results": reranked[:limit],
            "citations": [
                {"id": c.id, "confidence": c.confidence} for c in annotated.citations
            ],
            "sources": [
                {
                    "id": s.source_id,
                    "name": s.source_name,
                    "type": s.source_type,
                    "content": s.content[:200],
                    "score": s.score,
                }
                for s in annotated.sources
            ],
            "reranked": True,
            "took_ms": took,
        }

    async def search_with_entity_centric(
        self,
        query: str,
        limit: int = 10,
        use_entity_search: bool = True,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)

        classification = self.classifier.classify(query)
        intent = classification.get("primary_intent", "")

        results = await self.search(query, limit=limit * 2)

        if use_entity_search and intent in ("relationship", "code_relationship"):
            entity_name = self._extract_entity_from_query(query)
            if entity_name:
                entity_results = await self.entity_centric_retriever.search_by_entity(
                    entity_name=entity_name,
                    depth=2,
                    limit=limit,
                )

                results["entity_graph"] = entity_results.get("results", [])
                results["sources"]["entity"] = entity_results.get("total", 0)

        results["took_ms"] = int(time.time() * 1000) - start
        return results

    def _extract_entity_from_query(self, query: str) -> Optional[str]:
        patterns = [
            r"(?:find|get|show)\s+(?:all\s+)?(?:callers?|callees?)\s+of\s+(\w+)",
            r"(?:who|what)\s+(?:calls?|uses?|imports?)\s+(\w+)",
            r"(\w+)\s+(?:function|method|class|module)",
            r"entities?\s+(?:for|related to)\s+(\w+)",
        ]

        import re

        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1)

        words = query.split()
        if len(words) <= 3:
            return words[-1] if words else None

        return None


_hybrid_retriever: Optional[HybridRetriever] = None


def get_hybrid_retriever() -> HybridRetriever:
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever()
    return _hybrid_retriever


class EnhancedHybridRetriever(HybridRetriever):
    def __init__(self, cache: Optional[EntityGraphCache] = None):
        super().__init__()
        self.entity_cache = cache or get_entity_graph_cache()

    async def search_with_enhanced_reasoning(
        self,
        query: str,
        limit: int = 10,
        use_entity_reasoning: bool = True,
        use_iterative: bool = True,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)

        # Extract entities from query for cache lookup
        query_entities = self._extract_entity_names(query)

        # Build entity graph: check cache first, fall back to DB
        entity_graph = await self._resolve_entity_graph(query_entities)

        docs_result = await self.docs_retriever.search(query, limit=limit)
        code_result = await self.code_retriever.search(query, limit=limit)
        graph_result = await self.graph_retriever.search(query, limit=limit)

        source_results = {
            "docs": docs_result.get("results", []),
            "code": code_result.get("results", []),
            "graph": graph_result.get("results", []),
        }
        fused = self.fusion.fuse(source_results)

        reasoning_result = None
        if use_entity_reasoning and entity_graph:
            entity_result = await self.entity_reasoning.reason(
                query, fused, entity_graph
            )
            reasoning_result = entity_result
        elif use_iterative:
            iterative_result = await self.iterative_reasoning.retrieve(
                query,
                lambda q: self._sync_search(q, limit),
            )
            reasoning_result = iterative_result
        else:
            reasoning_result = await self.reasoning.reason(query, fused)

        answer = reasoning_result.get("answer", "") if reasoning_result else ""
        confidence = (
            reasoning_result.get("confidence", 0.0) if reasoning_result else 0.0
        )

        took = int(time.time() * 1000) - start

        return {
            "query": query,
            "answer": answer,
            "results": fused[:limit],
            "confidence": confidence,
            "reasoning_mode": reasoning_result.get("reasoning_mode", "direct")
            if reasoning_result
            else "direct",
            "entities": reasoning_result.get("entities", [])
            if reasoning_result
            else [],
            "graph_paths": reasoning_result.get("graph_paths", {})
            if reasoning_result
            else {},
            "cache_stats": self.entity_cache.get_stats(),
            "took_ms": took,
        }

    async def _resolve_entity_graph(
        self,
        entity_names: List[str],
    ) -> Dict[str, List[Any]]:
        """Build an entity graph for the given entity names.

        Checks the cache first. On a miss, queries the graph DB and caches
        the result. Returns a mapping of entity_name → [relations].
        """
        graph: Dict[str, List[Any]] = {}

        for name in entity_names:
            cached = self.entity_cache.get(name)
            if cached:
                graph[name] = cached.relations
                continue

            # Cache miss — query the graph DB
            try:
                relations = await self._fetch_entity_relations(name)
                entry = EntityGraphCacheEntry(
                    entity_name=name,
                    relations=relations,
                    graph_paths={name: [r.get("target", "") for r in relations]},
                    related_entities=[r.get("target", "") for r in relations],
                    ttl=self.entity_cache.default_ttl,
                )
                self.entity_cache.put(name, entry)
                graph[name] = relations
            except Exception:
                # DB unavailable — leave empty list
                graph[name] = []

        return graph

    async def _fetch_entity_relations(
        self,
        entity_name: str,
        depth: int = 2,
    ) -> List[Dict[str, Any]]:
        """Fetch entity relationships from FalkorDB via the graph retriever."""
        result = await self.graph_retriever.search(
            f"relationships of {entity_name}",
            limit=50,
        )
        return result.get("results", [])

    def _extract_entity_names(self, query: str) -> List[str]:
        """Extract potential entity names from a query string."""
        words = query.split()
        names = []
        for word in words:
            clean = word.rstrip(".,!?;:()[]{}\"'")
            if clean and clean[0].isupper() and len(clean) > 1:
                names.append(clean)
        return names

    def invalidate_entity_cache(self, entity_name: Optional[str] = None) -> bool:
        """Invalidate entity cache entries."""
        if entity_name:
            return self.entity_cache.invalidate(entity_name)
        self.entity_cache.clear()
        return True

    def get_entity_cache_stats(self) -> Dict[str, Any]:
        """Return cache statistics for monitoring."""
        return self.entity_cache.get_stats()

    def _sync_search(
        self,
        query: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Synchronous search wrapper for iterative reasoning engine.

        Runs the async search in a sync context via asyncio.run.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in an async context — return empty and let the
                # caller use the async search_with_enhanced_reasoning directly.
                return []
            result = loop.run_until_complete(
                self.search(query, limit=limit, use_reasoning=True)
            )
            return result.get("results", [])
        except Exception:
            return []


_enhanced_hybrid_retriever: Optional[EnhancedHybridRetriever] = None


def get_enhanced_hybrid_retriever() -> EnhancedHybridRetriever:
    global _enhanced_hybrid_retriever
    if _enhanced_hybrid_retriever is None:
        _enhanced_hybrid_retriever = EnhancedHybridRetriever()
    return _enhanced_hybrid_retriever
