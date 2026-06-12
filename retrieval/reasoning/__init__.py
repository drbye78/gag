"""
Entity-Aware Reasoning Module.

Provides reasoning capabilities that leverage entity graphs and
relationship information for context-aware answer synthesis.
"""

from enum import Enum
from typing import Any, Dict, List, Optional


class ReasoningMode(str, Enum):
    DIRECT = "direct"
    CHAIN_OF_THOUGHTS = "chain_of_thoughts"
    TREE_OF_THOUGHTS = "tree_of_thoughts"
    REFLECT = "reflect"
    CRITIQUE = "critique"


class ReasoningEngine:
    """Default reasoning engine that synthesises answers from retrieved facts.

    Supports multiple reasoning modes.  When no LLM backend is available,
    falls back to deterministic concatenation of the top facts.
    """

    def __init__(self, mode: ReasoningMode = ReasoningMode.CHAIN_OF_THOUGHTS):
        self.mode = mode

    async def reason(
        self,
        query: str,
        facts: List[Dict[str, Any]],
        entity_graph: Optional[Dict[str, List[Any]]] = None,
    ) -> Dict[str, Any]:
        """Synthesise an answer from retrieved facts.

        When an ``entity_graph`` is supplied, delegates to
        :class:`EntityAwareReasoningEngine` for richer graph-based
        reasoning; otherwise performs direct fact synthesis.
        """
        if entity_graph:
            from retrieval.reasoning.entity_aware import EntityAwareReasoningEngine

            engine = EntityAwareReasoningEngine()
            return await engine.reason(query, facts, entity_graph)

        return await self._direct_reason(query, facts)

    async def _direct_reason(
        self,
        query: str,
        facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Fallback: concatenate top facts into a basic answer."""
        if not facts:
            return {
                "query": query,
                "answer": "No relevant information found.",
                "reasoning_mode": self.mode.value,
                "confidence": 0.0,
                "steps": [],
                "duration_ms": 0,
            }

        import time

        start = int(time.time() * 1000)

        top_facts = facts[:3]
        answer_parts = [f.get("content", "")[:200] for f in top_facts if f.get("content")]
        answer = " | ".join(answer_parts) if answer_parts else "Insufficient information."

        confidence = sum(f.get("score", 0.0) for f in top_facts) / max(len(top_facts), 1)
        confidence = min(max(confidence, 0.0), 1.0)

        return {
            "query": query,
            "answer": answer,
            "reasoning_mode": self.mode.value,
            "confidence": confidence,
            "steps": [
                {
                    "step_id": "0",
                    "thought": f"Analyzing query: {query}",
                    "action": "synthesize",
                    "observation": f"Based on {len(facts)} retrieved facts",
                }
            ],
            "sources": [f.get("source", "") for f in top_facts],
            "duration_ms": int(time.time() * 1000) - start,
        }


def get_reasoning_engine(mode: ReasoningMode = ReasoningMode.CHAIN_OF_THOUGHTS) -> ReasoningEngine:
    """Factory: return a :class:`ReasoningEngine` configured with *mode*."""
    return ReasoningEngine(mode=mode)


from retrieval.reasoning.entity_aware import (
    EntityAwareReasoningEngine,
    EntityRelation,
    GraphPathType,
)

__all__ = [
    "ReasoningEngine",
    "EntityAwareReasoningEngine",
    "GraphPathType",
    "EntityRelation",
    "ReasoningMode",
    "get_reasoning_engine",
]
