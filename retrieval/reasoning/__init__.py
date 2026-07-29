"""
Reasoning Module.

Provides reasoning capabilities powered by agents/reasoning.py (the real engine).
Backward-compatible wrappers for consumers that still import from retrieval.reasoning.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from agents.reasoning import ReasonMode, ReasoningAgent, AnswerWithCitations


class ReasoningMode(str, Enum):
    """Backward-compatible reasoning mode enum (maps to agents.reasoning.ReasonMode)."""
    DIRECT = "direct"
    CHAIN_OF_THOUGHTS = "chain_of_thoughts"
    TREE_OF_THOUGHTS = "tree_of_thoughts"
    REFLECT = "reflect"
    CRITIQUE = "critique"


_MODE_MAP = {
    ReasoningMode.DIRECT: ReasonMode.DIRECT,
    ReasoningMode.CHAIN_OF_THOUGHTS: ReasonMode.CHAIN_OF_THOUGHT,
    ReasoningMode.TREE_OF_THOUGHTS: ReasonMode.TREE_OF_THOUGHTS,
    ReasoningMode.REFLECT: ReasonMode.REFLECT,
    ReasoningMode.CRITIQUE: ReasonMode.CRITIQUE,
}


class ReasoningEngine:
    """Backward-compatible wrapper around agents.reasoning.ReasoningAgent.

    Presents the old .reason(query, facts) → dict API using the real LLM-backed
    reasoning engine under the hood.
    """

    def __init__(
        self,
        mode: ReasoningMode = ReasoningMode.CHAIN_OF_THOUGHTS,
        use_llm: bool = True,
    ):
        if isinstance(mode, str):
            try:
                mode = ReasoningMode(mode)
            except ValueError:
                mode = ReasoningMode.CHAIN_OF_THOUGHTS
        self.mode = mode
        self.use_llm = use_llm
        self.max_steps = 10
        self.max_branches = 3
        self._agent = ReasoningAgent(mode=_MODE_MAP.get(mode, ReasonMode.CHAIN_OF_THOUGHT))

    @property
    def _llm_router(self):
        """Backward-compat: expose the underlying router."""
        return self._agent.router

    @_llm_router.setter
    def _llm_router(self, router):
        self._agent.router = router

    @property
    def _llm_available(self):
        return True

    @_llm_available.setter
    def _llm_available(self, value):
        pass  # no-op; always available via real router

    def _estimate_confidence(self, answer: str, sources: List[Dict[str, Any]], query: str) -> float:
        """Estimate confidence based on source count and answer length."""
        if not sources:
            return 0.3
        source_score = min(len(sources) / 5.0, 1.0) * 0.3
        length_score = min(len(answer) / 500.0, 1.0) * 0.2
        return round(min(0.5 + source_score + length_score, 1.0), 2)

    async def reason(
        self,
        query: str,
        retrieved_facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Reason over retrieved facts. Backward-compatible with old API."""
        if not retrieved_facts:
            return {
                "query": query,
                "answer": "No relevant information found.",
                "reasoning_mode": self.mode.value,
                "steps": [],
                "confidence": 0.0,
            }

        retrieved_data = {
            "results": [{"source": "facts", "results": retrieved_facts}],
        }

        result: AnswerWithCitations = await self._agent.generate_answer(
            query=query,
            retrieved_data=retrieved_data,
            intent="explain",
        )

        sources = [f.get("source", "") for f in retrieved_facts[:3]]
        confidence = self._estimate_confidence(result.answer, retrieved_facts, query)

        return {
            "query": query,
            "answer": result.answer,
            "reasoning_mode": self.mode.value,
            "steps": [],
            "confidence": confidence,
            "sources": sources,
        }


def get_reasoning_engine(
    mode: ReasoningMode = ReasoningMode.CHAIN_OF_THOUGHTS,
) -> ReasoningEngine:
    """Factory for backward-compatible ReasoningEngine."""
    return ReasoningEngine(mode=mode)


# Re-export entity-aware and iterative reasoning
from retrieval.reasoning.entity_aware import (
    EntityAwareReasoningEngine,
    GraphPathType,
    EntityRelation,
)


__all__ = [
    "EntityAwareReasoningEngine",
    "GraphPathType",
    "EntityRelation",
    "ReasoningMode",
    "ReasoningEngine",
    "get_reasoning_engine",
]
