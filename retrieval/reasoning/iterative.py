"""
Iterative Refinement - Provides iterative retrieval with query refinement.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

from retrieval.reasoning.entity_aware import (
    EntityAwareReasoningEngine,
)


class IterationStrategy(str, Enum):
    EXPAND = "expand"
    FOCUS = "focus"
    REWRITE = "rewrite"
    DECOMPOSE = "decompose"


@dataclass
class IterationResult:
    iteration: int
    query: str
    retrieved: List[Dict[str, Any]]
    refined_query: Optional[str] = None
    done: bool = False
    confidence: float = 0.0
    duration_ms: int = 0


class IterativeRetrievalReasoner:
    def __init__(
        self,
        max_iterations: int = 3,
        min_results: int = 3,
        confidence_threshold: float = 0.7,
        strategy: IterationStrategy = IterationStrategy.EXPAND,
        entity_engine: Optional[EntityAwareReasoningEngine] = None,
    ):
        self.max_iterations = max_iterations
        self.min_results = min_results
        self.confidence_threshold = confidence_threshold
        self.strategy = strategy
        self.entity_engine = entity_engine or EntityAwareReasoningEngine()
        self._query_expander: Optional[Callable] = None

    def set_query_expander(
        self,
        expander: Callable[[str, List[Dict]], List[str]],
    ) -> None:
        self._query_expander = expander

    async def retrieve(
        self,
        initial_query: str,
        retriever: Callable[[str], List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)
        results: List[IterationResult] = []

        current_query = initial_query
        all_retrieved: List[Dict[str, Any]] = []
        seen_contents: set = set()

        for iteration in range(self.max_iterations):
            iter_start = int(time.time() * 1000)

            retrieved = await self._retrieve_with_timeout(current_query, retriever)

            new_facts = [
                f for f in retrieved if f.get("content", "") not in seen_contents
            ]
            for f in new_facts:
                seen_contents.add(f.get("content", ""))

            all_retrieved.extend(new_facts)

            confidence = self._calculate_confidence(new_facts, all_retrieved, iteration)

            is_done = (
                len(all_retrieved) >= self.min_results
                and confidence >= self.confidence_threshold
            )

            result = IterationResult(
                iteration=iteration + 1,
                query=current_query,
                retrieved=new_facts,
                done=is_done,
                confidence=confidence,
                duration_ms=int(time.time() * 1000) - iter_start,
            )
            results.append(result)

            if is_done:
                break

            refined_query = self._refine_query(current_query, all_retrieved, iteration)
            if refined_query and refined_query != current_query:
                result.refined_query = refined_query
                current_query = refined_query
            else:
                break

        final_answer = self._synthesize_answer(initial_query, all_retrieved)

        return {
            "query": initial_query,
            "answer": final_answer,
            "reasoning_mode": "iterative",
            "iterations": [
                {
                    "iteration": r.iteration,
                    "query": r.query,
                    "results_count": len(r.retrieved),
                    "refined_query": r.refined_query,
                    "done": r.done,
                    "confidence": r.confidence,
                    "duration_ms": r.duration_ms,
                }
                for r in results
            ],
            "total_retrieved": len(all_retrieved),
            "confidence": self._calculate_final_confidence(all_retrieved, results),
            "sources": [f.get("source", "") for f in all_retrieved[:3]],
            "duration_ms": int(time.time() * 1000) - start,
        }

    async def _retrieve_with_timeout(
        self,
        query: str,
        retriever,
    ) -> List[Dict[str, Any]]:
        try:
            results = retriever(query)
            # Handle both sync and async retrievers
            if hasattr(results, "__await__"):
                results = await results
            if results:
                return results
        except Exception as e:
            logger.error("Retrieval failed for query: %s", e)

        return []

    def _refine_query(
        self,
        current_query: str,
        all_retrieved: List[Dict[str, Any]],
        iteration: int,
    ) -> Optional[str]:
        if self.strategy == IterationStrategy.EXPAND:
            return self._expand_query(current_query, all_retrieved)
        elif self.strategy == IterationStrategy.FOCUS:
            return self._focus_query(current_query, all_retrieved)
        elif self.strategy == IterationStrategy.REWRITE:
            return self._rewrite_query(current_query, all_retrieved)
        elif self.strategy == IterationStrategy.DECOMPOSE:
            return self._decompose_query(current_query, all_retrieved)

        return None

    def _expand_query(
        self,
        query: str,
        retrieved: List[Dict[str, Any]],
    ) -> Optional[str]:
        terms = set(query.lower().split())

        for fact in retrieved[:3]:
            content = fact.get("content", "")
            new_terms = [
                w for w in content.lower().split() if len(w) > 4 and w not in terms
            ]
            if new_terms:
                terms.update(new_terms[:2])

        expanded = " ".join(sorted(terms))
        return expanded if expanded != query else None

    def _focus_query(
        self,
        query: str,
        retrieved: List[Dict[str, Any]],
    ) -> Optional[str]:
        if retrieved:
            top_fact = retrieved[0]
            content = top_fact.get("content", "")
            words = content.split()

            if words:
                return " ".join(words[:10])

        return None

    def _rewrite_query(
        self,
        query: str,
        retrieved: List[Dict[str, Any]],
    ) -> Optional[str]:
        if self._query_expander:
            try:
                expansions = self._query_expander(query, retrieved)
                if expansions and len(expansions) > 1:
                    return expansions[1]
            except Exception as e:
                logger.error("Query expansion failed: %s", e)

        return None

    def _decompose_query(
        self,
        query: str,
        retrieved: List[Dict[str, Any]],
    ) -> Optional[str]:
        words = query.split()

        if len(words) > 5:
            midpoint = len(words) // 2
            subset = words[midpoint:]
            return " ".join(subset)

        return None

    def _calculate_confidence(
        self,
        new_facts: List[Dict[str, Any]],
        all_facts: List[Dict[str, Any]],
        iteration: int,
    ) -> float:
        if not new_facts:
            return 0.0

        new_score = sum(f.get("score", 0) for f in new_facts) / max(len(new_facts), 1)

        quantity_bonus = min(len(all_facts) / 10.0, 0.3)

        iteration_penalty = min(iteration * 0.1, 0.3)

        return max(0.0, min(1.0, new_score + quantity_bonus - iteration_penalty))

    def _calculate_final_confidence(
        self,
        facts: List[Dict[str, Any]],
        results: List[IterationResult],
    ) -> float:
        if not facts:
            return 0.0

        avg_score = sum(f.get("score", 0) for f in facts) / max(len(facts), 1)

        if results:
            last_confidence = results[-1].confidence
            return (avg_score + last_confidence) / 2

        return avg_score

    def _synthesize_answer(
        self,
        query: str,
        facts: List[Dict[str, Any]],
    ) -> str:
        if not facts:
            return "No relevant information found."

        parts = []
        for fact in facts[:3]:
            content = fact.get("content", "")
            if content:
                parts.append(content[:200])

        return " | ".join(parts[:2]) if parts else "No answer found."


_iterative_reasoner: Optional[IterativeRetrievalReasoner] = None


def get_iterative_reasoning_engine(
    max_iterations: int = 3,
) -> IterativeRetrievalReasoner:
    global _iterative_reasoner
    if _iterative_reasoner is None:
        _iterative_reasoner = IterativeRetrievalReasoner(max_iterations=max_iterations)
    return _iterative_reasoner
