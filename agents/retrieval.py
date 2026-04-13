"""
Retrieval Agent - Multi-source retrieval with strategy selection.

Supports PARALLEL, SEQUENTIAL, CASCADE, and ADAPTIVE strategies
with in-memory caching and metrics tracking.
"""

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from agents.planner import ExecutionStep, ExecutionPlan
from retrieval.orchestrator import RetrievalOrchestrator, RetrievalSource
from retrieval.hybrid import get_enhanced_hybrid_retriever
from retrieval.reasoning import get_reasoning_engine
from retrieval.reasoning.entity_aware import get_entity_aware_reasoning_engine


class RetrievalStrategy(str, Enum):
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    CASCADE = "cascade"
    ADAPTIVE = "adaptive"


@dataclass
class RetrievalResult:
    source: str
    query: str
    results: List[Any]
    scores: List[float] = field(default_factory=list)
    total: int = 0
    took_ms: int = 0
    cached: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "query": self.query,
            "results": self.results,
            "total": self.total,
            "took_ms": self.took_ms,
            "cached": self.cached,
            "error": self.error,
        }


class RetrievalCache:
    def __init__(self, ttl_seconds: int = 300):
        self._cache: Dict[str, tuple] = {}
        self._ttl = ttl_seconds
        self._hits = 0
        self._misses = 0

    def _make_key(self, query: str, source: str) -> str:
        return hashlib.sha256(f"{query}:{source}".encode()).hexdigest()

    def get(self, query: str, source: str) -> Optional[RetrievalResult]:
        key = self._make_key(query, source)
        if key in self._cache:
            result, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                self._hits += 1
                result.cached = True
                return result
            else:
                del self._cache[key]
        self._misses += 1
        return None

    def set(self, query: str, source: str, result: RetrievalResult):
        key = self._make_key(query, source)
        self._cache[key] = (result, time.time())

    def clear(self):
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0


class RetrievalAgent:
    def __init__(
        self,
        strategy: RetrievalStrategy = RetrievalStrategy.ADAPTIVE,
        cache_ttl: int = 300,
        max_concurrent: int = 5,
    ):
        self.orchestrator = RetrievalOrchestrator()
        self.strategy = strategy
        self.cache = RetrievalCache(cache_ttl)
        self.max_concurrent = max_concurrent

        self._source_semaphore = asyncio.Semaphore(max_concurrent)
        self._metrics = {
            "total_queries": 0,
            "cache_hits": 0,
            "total_results": 0,
            "avg_latency_ms": 0,
        }

    def _select_strategy(
        self,
        step: ExecutionStep,
        context: Dict[str, Any],
    ) -> RetrievalStrategy:
        if self.strategy == RetrievalStrategy.ADAPTIVE:
            intent = context.get("intent", "explain")
            if intent == "troubleshoot":
                return RetrievalStrategy.SEQUENTIAL
            elif intent == "design":
                return RetrievalStrategy.PARALLEL
            return RetrievalStrategy.CASCADE
        return self.strategy

    async def execute_plan(
        self,
        plan: "ExecutionPlan",
        query: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        start_time = time.time()

        steps = [s for s in plan.steps if s.step_type == "retrieve"]

        results = []

        strategy = self._select_strategy(
            steps[0] if steps else None, {"intent": plan.intent}
        )

        if strategy == RetrievalStrategy.PARALLEL:
            results = await self._execute_parallel(steps, query, limit)
        elif strategy == RetrievalStrategy.CASCADE:
            results = await self._execute_cascade(steps, query, limit)
        else:
            results = await self._execute_sequential(steps, query, limit)

        total_time = int(time.time() - start_time) * 1000
        self._update_metrics(results, total_time)

        return {
            "query": query,
            "results": [r.to_dict() for r in results],
            "total_results": sum(r.total for r in results),
            "strategy_used": strategy.value,
            "took_ms": total_time,
            "cache_hit_rate": self.cache.hit_rate,
        }

    async def _execute_parallel(
        self,
        steps: List[ExecutionStep],
        query: str,
        limit: int,
    ) -> List[RetrievalResult]:
        tasks = []
        for step in steps:
            task = self._execute_single(step, query, limit)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, RetrievalResult)]

    async def _execute_sequential(
        self,
        steps: List[ExecutionStep],
        query: str,
        limit: int,
    ) -> List[RetrievalResult]:
        results = []
        for step in steps:
            result = await self._execute_single(step, query, limit)
            results.append(result)

            if result.error:
                continue

        return results

    async def _execute_cascade(
        self,
        steps: List[ExecutionStep],
        query: str,
        limit: int,
    ) -> List[RetrievalResult]:
        results = []
        accumulated_results = []

        for step in steps:
            result = await self._execute_single(step, query, limit)

            if result.total > 0:
                accumulated_results.extend(result.results)
                results.append(result)

                if len(accumulated_results) >= limit:
                    break

        return results

    async def _execute_single(
        self,
        step: ExecutionStep,
        query: str,
        limit: int,
    ) -> RetrievalResult:
        source = step.source or "docs"
        limit = step.params.get("limit", limit)

        start_time = time.time()

        cached = self.cache.get(query, source)
        if cached:
            self._metrics["cache_hits"] += 1
            return cached

        async with self._source_semaphore:
            try:
                if source == "all":
                    data = await self.orchestrator.retrieve(query, limit=limit)
                else:
                    sources = [RetrievalSource(source)]
                    data = await self.orchestrator.retrieve(
                        query, sources=sources, limit=limit
                    )

                result = RetrievalResult(
                    source=source,
                    query=query,
                    results=data.get("results", []),
                    total=data.get("total_results", 0),
                    took_ms=int(time.time() - start_time) * 1000,
                )

                self.cache.set(query, source, result)
                return result

            except Exception as e:
                return RetrievalResult(
                    source=source,
                    query=query,
                    results=[],
                    total=0,
                    took_ms=int(time.time() - start_time) * 1000,
                    error=str(e),
                )

    async def retrieve_single(
        self,
        query: str,
        source: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        step = ExecutionStep(
            step_type="retrieve", action="search", source=source, params={"limit": limit}
        )
        result = await self._execute_single(step, query, limit)
        return result.to_dict()

    def _update_metrics(self, results: List[RetrievalResult], total_time: int):
        self._metrics["total_queries"] += 1
        self._metrics["total_results"] += sum(r.total for r in results)

        if self._metrics["avg_latency_ms"]:
            self._metrics["avg_latency_ms"] = (
                self._metrics["avg_latency_ms"] + total_time
            ) / 2
        else:
            self._metrics["avg_latency_ms"] = total_time

    def get_metrics(self) -> Dict[str, Any]:
        return {
            **self._metrics,
            "cache_hit_rate": self.cache.hit_rate,
            "cache_hits": self.cache._hits,
            "cache_misses": self.cache._misses,
        }

    def clear_cache(self):
        self.cache.clear()


def get_retrieval_agent() -> RetrievalAgent:
    return RetrievalAgent()
