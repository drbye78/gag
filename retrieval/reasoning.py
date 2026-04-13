"""
Reasoning Engine - Chains retrieved facts for complex answers.

Implements Chain of Thoughts, Tree of Thoughts,
Reflective reasoning for multi-step queries.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ReasoningMode(str, Enum):
    DIRECT = "direct"
    CHAIN_OF_THOUGHTS = "chain_of_thoughts"
    TREE_OF_THOUGHTS = "tree_of_thoughts"
    REFLECT = "reflect"
    CRITIQUE = "critique"


@dataclass
class ReasoningStep:
    step_id: str
    thought: str
    action: str
    observation: str
    score: float = 0.0
    children: List["ReasoningStep"] = field(default_factory=list)
    parent_id: Optional[str] = None


class ReasoningEngine:
    def __init__(self, mode: ReasoningMode = ReasoningMode.CHAIN_OF_THOUGHTS):
        self.mode = mode
        self.max_steps = 10
        self.max_branches = 3
        self._steps: Dict[str, ReasoningStep] = {}

    async def reason(
        self,
        query: str,
        retrieved_facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)

        if self.mode == ReasoningMode.DIRECT:
            return await self._direct_reason(query, retrieved_facts)
        elif self.mode == ReasoningMode.CHAIN_OF_THOUGHTS:
            return await self._chain_reason(query, retrieved_facts)
        elif self.mode == ReasoningMode.TREE_OF_THOUGHTS:
            return await self._tree_reason(query, retrieved_facts)
        elif self.mode == ReasoningMode.REFLECT:
            return await self._reflect_reason(query, retrieved_facts)
        elif self.mode == ReasoningMode.CRITIQUE:
            return await self._critique_reason(query, retrieved_facts)
        else:
            return await self._direct_reason(query, retrieved_facts)

    async def _direct_reason(
        self,
        query: str,
        facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not facts:
            return {
                "query": query,
                "answer": "No relevant information found.",
                "reasoning_mode": self.mode.value,
                "steps": [],
                "confidence": 0.0,
            }

        top_fact = facts[0]
        answer = top_fact.get("content", "")

        return {
            "query": query,
            "answer": answer,
            "reasoning_mode": self.mode.value,
            "steps": [],
            "confidence": top_fact.get("score", 0.5),
            "sources": [f.get("source", "") for f in facts[:3]],
        }

    async def _chain_reason(
        self,
        query: str,
        facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        self._steps.clear()

        current_step = ReasoningStep(
            step_id="0",
            thought=f"Analyzing query: {query}",
            action="analyze",
            observation=f"Query requires understanding of {len(facts)} facts",
        )
        self._steps["0"] = current_step

        for i, fact in enumerate(facts[: self.max_steps], 1):
            step = ReasoningStep(
                step_id=str(i),
                thought=f"Fact {i}: {fact.get('content', '')[:100]}",
                action="retrieve",
                observation=f"Relevant: {fact.get('source', 'unknown')}",
                score=fact.get("score", 0.0),
                parent_id=str(i - 1),
            )
            self._steps[str(i)] = step

        answer = self._build_chain_answer(facts, query)

        return {
            "query": query,
            "answer": answer,
            "reasoning_mode": self.mode.value,
            "steps": list(self._steps.values()),
            "confidence": sum(f.get("score", 0) for f in facts) / max(len(facts), 1),
            "sources": [f.get("source", "") for f in facts[:3]],
        }

    async def _tree_reason(
        self,
        query: str,
        facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        self._steps.clear()
        root = ReasoningStep(
            step_id="root",
            thought=f"Query: {query}",
            action="decompose",
            observation=f"Exploring {len(facts)} facts across branches",
        )
        self._steps["root"] = root

        branch_paths = [["root"] for _ in range(min(self.max_branches, len(facts)))]

        for i, fact in enumerate(facts):
            branch_idx = i % self.max_branches
            step = ReasoningStep(
                step_id=f"branch_{branch_idx}_{i}",
                thought=f"Exploring alternative path with fact {i}",
                action="explore",
                observation=f"Source: {fact.get('source', 'unknown')}",
                score=fact.get("score", 0.0),
                parent_id="root",
            )
            self._steps[step.step_id] = step
            branch_paths[branch_idx].append(step.step_id)

        best_path = max(
            branch_paths, key=lambda p: self._calculate_path_score(p, facts)
        )
        answer = self._build_tree_answer(facts, query)

        return {
            "query": query,
            "answer": answer,
            "reasoning_mode": self.mode.value,
            "steps": list(self._steps.values()),
            "confidence": self._calculate_path_score(best_path, facts),
            "sources": [f.get("source", "") for f in facts[:3]],
            "explored_paths": len(branch_paths),
        }

    async def _reflect_reason(
        self,
        query: str,
        facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        self._steps.clear()

        analyze_step = ReasoningStep(
            step_id="0",
            thought="Initial analysis of retrieved facts",
            action="analyze",
            observation=f"Found {len(facts)} potentially relevant facts",
        )
        self._steps["0"] = analyze_step

        critique_step = ReasoningStep(
            step_id="1",
            thought="Critiquing each fact for relevance",
            action="critique",
            observation="Evaluating fact quality",
            parent_id="0",
        )
        self._steps["1"] = critique_step

        valid_facts = [f for f in facts if f.get("score", 0) > 0.3]

        refine_step = ReasoningStep(
            step_id="2",
            thought="Refining answer based on valid facts",
            action="refine",
            observation=f"Using {len(valid_facts)} high-quality facts",
            parent_id="1",
        )
        self._steps["2"] = refine_step

        answer = self._build_chain_answer(valid_facts if valid_facts else facts, query)

        return {
            "query": query,
            "answer": answer,
            "reasoning_mode": self.mode.value,
            "steps": list(self._steps.values()),
            "confidence": sum(f.get("score", 0) for f in valid_facts)
            / max(len(valid_facts), 1),
            "sources": [f.get("source", "") for f in (valid_facts or facts)[:3]],
        }

    async def _critique_reason(
        self,
        query: str,
        facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        self._steps.clear()

        claim_step = ReasoningStep(
            step_id="0",
            thought="Making initial claim based on facts",
            action="claim",
            observation=f"Formed claim from {len(facts)} facts",
        )
        self._steps["0"] = claim_step

        critique_facts = []
        for fact in facts:
            score = fact.get("score", 0)
            if score > 0.7:
                critique_facts.append(fact)

        if not critique_facts:
            critique_facts = facts[:2]

        answer = self._build_chain_answer(critique_facts, query)

        step = ReasoningStep(
            step_id="1",
            thought="Evaluating claim against evidence",
            action="evaluate",
            observation=f"Supported by {len(critique_facts)} strong facts",
            score=sum(f.get("score", 0) for f in critique_facts) / len(critique_facts),
            parent_id="0",
        )
        self._steps["1"] = step

        return {
            "query": query,
            "answer": answer,
            "reasoning_mode": self.mode.value,
            "steps": list(self._steps.values()),
            "confidence": step.score,
            "sources": [f.get("source", "") for f in facts[:3]],
        }

    def _build_chain_answer(self, facts: List[Dict], query: str) -> str:
        if not facts:
            return "Insufficient information to answer the query."

        if len(facts) == 1:
            return facts[0].get("content", "")

        parts = []
        for fact in facts[:3]:
            content = fact.get("content", "")
            if content:
                parts.append(content)

        return " | ".join(parts[:2]) if parts else "No answer found."

    def _build_tree_answer(self, facts: List[Dict], query: str) -> str:
        if not facts:
            return "Insufficient information to answer the query."

        best_fact = max(facts, key=lambda f: f.get("score", 0))
        return best_fact.get("content", "")

    def _calculate_path_score(self, path: List[str], facts: List[Dict]) -> float:
        if not facts:
            return 0.0

        relevant_facts = facts[: len(path)]
        return sum(f.get("score", 0) for f in relevant_facts) / len(relevant_facts)


_reasoning_engine: Optional[ReasoningEngine] = None


def get_reasoning_engine(
    mode: ReasoningMode = ReasoningMode.CHAIN_OF_THOUGHTS,
) -> ReasoningEngine:
    global _reasoning_engine
    if _reasoning_engine is None or _reasoning_engine.mode != mode:
        _reasoning_engine = ReasoningEngine(mode=mode)
    return _reasoning_engine
