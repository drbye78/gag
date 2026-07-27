"""
Reasoning Engine - Chains retrieved facts for complex answers.

Implements Chain of Thoughts, Tree of Thoughts,
Reflective reasoning for multi-step queries.
Optionally uses LLM for deep reasoning when available.
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
        self._llm_router = None
        self._llm_available = False
    
    def set_llm_router(self, router: Any) -> None:
        self._llm_router = router
        self._llm_available = True

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

        if self.use_llm and self._llm_available and self._llm_router:
            return await self._llm_reason(query, facts)
        
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
    
    def _extract_text(self, response: Any) -> str:
        """Extract text from an LLM response, handling both real and mock objects."""
        # ChatCompletionResponse has a .text property
        if hasattr(response, "text"):
            text = response.text
            if isinstance(text, str):
                return text.strip()
        # Fallback: try dict-style access
        if hasattr(response, "get"):
            try:
                content = response.get("content", "")
                if isinstance(content, str):
                    return content.strip()
            except Exception:
                pass
        # Fallback: try choices[0].message.content
        if hasattr(response, "choices"):
            try:
                choices = response.choices
                if choices and len(choices) > 0:
                    choice = choices[0]
                    if isinstance(choice, dict):
                        msg = choice.get("message", {})
                        content = msg.get("content", "")
                        if isinstance(content, str):
                            return content.strip()
            except Exception:
                pass
        return ""

    def _build_facts_text(self, facts: List[Dict[str, Any]], max_facts: int = 5, max_len: int = 200) -> str:
        """Format facts into a numbered text block for LLM prompts."""
        return "\n".join(
            f"{i+1}. {f.get('content', '')[:max_len]}"
            for i, f in enumerate(facts[:max_facts])
        )

    async def _llm_reason(
        self,
        query: str,
        facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        facts_text = self._build_facts_text(facts, max_facts=5, max_len=200)

        prompt = f"""Based on the following facts, answer the query concisely.

Query: {query}

Facts:
{facts_text}

Provide a direct answer in 2-3 sentences."""

        try:
            result = await self._llm_router.chat(
                prompt=prompt,
                temperature=0.3,
            )
            answer = self._extract_text(result)
            if not answer:
                answer = facts[0].get("content", "") if facts else "No answer found."
        except Exception:
            answer = facts[0].get("content", "") if facts else "No answer found."

        return {
            "query": query,
            "answer": answer,
            "reasoning_mode": "llm",
            "steps": [],
            "confidence": self._estimate_confidence(answer, facts, query),
            "sources": [f.get("source", "") for f in facts[:3]],
        }

    async def _llm_chain_reason(
        self,
        query: str,
        facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        facts_text = self._build_facts_text(facts, max_facts=7, max_len=250)

        prompt = f"""Think step by step about this query. Show your reasoning.

Query: {query}

Facts:
{facts_text}

Provide your reasoning steps and final answer."""

        try:
            result = await self._llm_router.chat(
                prompt=prompt,
                temperature=0.4,
            )
            answer = self._extract_text(result)
            if not answer:
                answer = " | ".join(
                    f.get("content", "")[:100] for f in facts[:2])
        except Exception:
            answer = " | ".join(
                f.get("content", "")[:100] for f in facts[:2])

        return {
            "query": query,
            "answer": answer,
            "reasoning_mode": "llm_chain",
            "steps": [],
            "confidence": self._estimate_confidence(answer, facts, query),
            "sources": [f.get("source", "") for f in facts[:3]],
        }

    async def _llm_tree_reason(
        self,
        query: str,
        facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Tree of Thoughts: generate 3 independent answers, then select the best.

        Makes 4 LLM calls: 3 exploratory (high temperature) + 1 selection.
        """
        facts_text = self._build_facts_text(facts, max_facts=5, max_len=200)
        steps: List[ReasoningStep] = []

        # Generate 3 independent answers at high temperature for diversity
        branches = []
        for i in range(3):
            prompt = f"""Answer the following query from a different perspective.

Query: {query}

Facts:
{facts_text}

Provide a direct answer (perspective {i+1} of 3)."""
            try:
                result = await self._llm_router.chat(
                    prompt=prompt,
                    temperature=0.9,
                )
                answer = self._extract_text(result)
            except Exception:
                answer = facts[i % len(facts)].get("content", "") if facts else ""

            branches.append(answer)
            steps.append(ReasoningStep(
                step_id=f"branch_{i}",
                thought=f"Exploring perspective {i+1}",
                action="explore",
                observation=answer[:100],
                score=0.0,
                parent_id="root",
            ))

        # Selection call: ask the LLM which answer is best
        selection_prompt = f"""You are evaluating 3 answers to the same query. Select the best one.

Query: {query}

Answer A: {branches[0]}

Answer B: {branches[1]}

Answer C: {branches[2]}

Which answer (A, B, or C) is the best? Respond with the letter, then provide the full text of that answer."""

        try:
            selection_result = await self._llm_router.chat(
                prompt=selection_prompt,
                temperature=0.2,
            )
            selection_text = self._extract_text(selection_result)
            # Extract the best answer based on the LLM's selection
            best_answer = self._select_best_branch(branches, selection_text)
            confidence = 0.8
        except Exception:
            # Fallback: pick the longest answer
            best_answer = max(branches, key=len) if branches else "No answer found."
            confidence = self._estimate_confidence(best_answer, facts, query)

        steps.append(ReasoningStep(
            step_id="select",
            thought="Selecting best answer from branches",
            action="select",
            observation=best_answer[:100],
            score=confidence,
            parent_id="root",
        ))

        return {
            "query": query,
            "answer": best_answer,
            "reasoning_mode": "llm_tree",
            "steps": steps,
            "confidence": confidence,
            "sources": [f.get("source", "") for f in facts[:3]],
            "explored_paths": 3,
        }

    def _select_best_branch(self, branches: List[str], selection_text: str) -> str:
        """Extract the best branch based on LLM selection text."""
        selection_lower = selection_text.lower()
        # Check which letter the LLM selected
        for i, letter in enumerate(["a", "b", "c"]):
            if f"answer {letter}" in selection_lower or f"answer {letter.upper()}" in selection_text:
                if i < len(branches):
                    return branches[i]
        # Fallback: return the selection text itself (it may contain the full answer)
        if selection_text:
            return selection_text
        return max(branches, key=len) if branches else "No answer found."

    async def _llm_reflect_reason(
        self,
        query: str,
        facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Reflect: generate answer, critique it, then refine.

        Makes 2-3 LLM calls: initial answer + critique + refinement.
        """
        facts_text = self._build_facts_text(facts, max_facts=5, max_len=200)
        steps: List[ReasoningStep] = []

        # Step 1: Generate initial answer
        initial_prompt = f"""Answer the following query based on the facts.

Query: {query}

Facts:
{facts_text}

Provide a direct answer."""
        try:
            result = await self._llm_router.chat(
                prompt=initial_prompt,
                temperature=0.4,
            )
            initial_answer = self._extract_text(result)
        except Exception:
            initial_answer = facts[0].get("content", "") if facts else "No answer found."

        steps.append(ReasoningStep(
            step_id="0",
            thought="Initial answer generated",
            action="answer",
            observation=initial_answer[:100],
        ))

        # Step 2: Critique the answer
        critique_prompt = f"""Critique the following answer. What is wrong or missing?

Query: {query}

Answer: {initial_answer}

Facts:
{facts_text}

List specific issues or say "No issues found" if the answer is correct."""
        try:
            critique_result = await self._llm_router.chat(
                prompt=critique_prompt,
                temperature=0.3,
            )
            critique = self._extract_text(critique_result)
        except Exception:
            critique = "Critique unavailable"

        steps.append(ReasoningStep(
            step_id="1",
            thought="Critiquing initial answer",
            action="critique",
            observation=critique[:100],
            parent_id="0",
        ))

        # Step 3: Refine based on critique (only if issues found)
        if "no issues" in critique.lower() or not critique:
            final_answer = initial_answer
            confidence = 0.8
        else:
            refine_prompt = f"""Improve your answer based on the critique.

Query: {query}

Original answer: {initial_answer}

Critique: {critique}

Facts:
{facts_text}

Provide the improved answer."""
            try:
                refine_result = await self._llm_router.chat(
                    prompt=refine_prompt,
                    temperature=0.4,
                )
                final_answer = self._extract_text(refine_result)
                confidence = 0.82
            except Exception:
                final_answer = initial_answer
                confidence = self._estimate_confidence(final_answer, facts, query)

        steps.append(ReasoningStep(
            step_id="2",
            thought="Refined answer based on critique",
            action="refine",
            observation=final_answer[:100],
            score=confidence,
            parent_id="1",
        ))

        return {
            "query": query,
            "answer": final_answer,
            "reasoning_mode": "llm_reflect",
            "steps": steps,
            "confidence": confidence,
            "sources": [f.get("source", "") for f in facts[:3]],
        }

    async def _llm_critique_reason(
        self,
        query: str,
        facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Critique: generate answer, then self-evaluate against a rubric.

        Makes 2 LLM calls: answer + self-evaluation.
        """
        facts_text = self._build_facts_text(facts, max_facts=5, max_len=200)
        steps: List[ReasoningStep] = []

        # Step 1: Generate answer
        answer_prompt = f"""Answer the following query based on the facts.

Query: {query}

Facts:
{facts_text}

Provide a comprehensive answer."""
        try:
            result = await self._llm_router.chat(
                prompt=answer_prompt,
                temperature=0.4,
            )
            answer = self._extract_text(result)
        except Exception:
            answer = facts[0].get("content", "") if facts else "No answer found."

        steps.append(ReasoningStep(
            step_id="0",
            thought="Initial answer generated",
            action="answer",
            observation=answer[:100],
        ))

        # Step 2: Self-evaluate against rubric
        eval_prompt = f"""Evaluate the following answer against these criteria:
- Correctness: Is it factually accurate based on the facts?
- Completeness: Does it address all parts of the query?
- Relevance: Is it relevant to the query?

Query: {query}

Answer: {answer}

Facts:
{facts_text}

Rate each criterion from 0.0 to 1.0 and provide an overall confidence score.
Format: Correctness: X.X, Completeness: X.X, Relevance: X.X, Overall: X.X"""
        confidence = 0.7
        try:
            eval_result = await self._llm_router.chat(
                prompt=eval_prompt,
                temperature=0.2,
            )
            eval_text = self._extract_text(eval_result)
            # Try to extract a confidence score from the evaluation
            confidence = self._extract_confidence(eval_text)
        except Exception:
            eval_text = "Evaluation unavailable"

        steps.append(ReasoningStep(
            step_id="1",
            thought="Self-evaluating against rubric",
            action="evaluate",
            observation=eval_text[:100] if eval_text else "",
            score=confidence,
            parent_id="0",
        ))

        return {
            "query": query,
            "answer": answer,
            "reasoning_mode": "llm_critique",
            "steps": steps,
            "confidence": confidence,
            "sources": [f.get("source", "") for f in facts[:3]],
            "evaluation": eval_text if eval_text else "",
        }

    def _extract_confidence(self, text: str) -> float:
        """Extract a confidence score from evaluation text."""
        import re
        # Look for "Overall: X.X" pattern
        match = re.search(r'overall[:\s]+([0-9]*\.?[0-9]+)', text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                if 0.0 <= val <= 1.0:
                    return val
            except ValueError:
                pass
        # Fallback: look for any decimal between 0 and 1
        matches = re.findall(r'([0-9]*\.?[0-9]+)', text)
        for m in matches:
            try:
                val = float(m)
                if 0.0 <= val <= 1.0:
                    return val
            except ValueError:
                continue
        return 0.7

    async def _chain_reason(
        self,
        query: str,
        facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if self.use_llm and self._llm_available and self._llm_router:
            return await self._llm_chain_reason(query, facts)
        
        steps: Dict[str, ReasoningStep] = {}

        current_step = ReasoningStep(
            step_id="0",
            thought=f"Analyzing query: {query}",
            action="analyze",
            observation=f"Query requires understanding of {len(facts)} facts",
        )
        steps["0"] = current_step

        for i, fact in enumerate(facts[: self.max_steps], 1):
            step = ReasoningStep(
                step_id=str(i),
                thought=f"Fact {i}: {fact.get('content', '')[:100]}",
                action="retrieve",
                observation=f"Relevant: {fact.get('source', 'unknown')}",
                score=fact.get("score", 0.0),
                parent_id=str(i - 1),
            )
            steps[str(i)] = step

        answer = self._build_chain_answer(facts, query)

        return {
            "query": query,
            "answer": answer,
            "reasoning_mode": self.mode.value,
            "steps": list(steps.values()),
            "confidence": sum(f.get("score", 0) for f in facts) / max(len(facts), 1),
            "sources": [f.get("source", "") for f in facts[:3]],
        }

    async def _tree_reason(
        self,
        query: str,
        facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if self.use_llm and self._llm_available and self._llm_router:
            return await self._llm_tree_reason(query, facts)

        steps: Dict[str, ReasoningStep] = {}
        root = ReasoningStep(
            step_id="root",
            thought=f"Query: {query}",
            action="decompose",
            observation=f"Exploring {len(facts)} facts across branches",
        )
        steps["root"] = root

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
            steps[step.step_id] = step
            branch_paths[branch_idx].append(step.step_id)

        best_path = max(
            branch_paths, key=lambda p: self._calculate_path_score(p, facts)
        )
        answer = self._build_tree_answer(facts, query)

        return {
            "query": query,
            "answer": answer,
            "reasoning_mode": self.mode.value,
            "steps": list(steps.values()),
            "confidence": self._calculate_path_score(best_path, facts),
            "sources": [f.get("source", "") for f in facts[:3]],
            "explored_paths": len(branch_paths),
        }

    async def _reflect_reason(
        self,
        query: str,
        facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if self.use_llm and self._llm_available and self._llm_router:
            return await self._llm_reflect_reason(query, facts)

        steps: Dict[str, ReasoningStep] = {}

        analyze_step = ReasoningStep(
            step_id="0",
            thought="Initial analysis of retrieved facts",
            action="analyze",
            observation=f"Found {len(facts)} potentially relevant facts",
        )
        steps["0"] = analyze_step

        critique_step = ReasoningStep(
            step_id="1",
            thought="Critiquing each fact for relevance",
            action="critique",
            observation="Evaluating fact quality",
            parent_id="0",
        )
        steps["1"] = critique_step

        valid_facts = [f for f in facts if f.get("score", 0) > 0.3]

        refine_step = ReasoningStep(
            step_id="2",
            thought="Refining answer based on valid facts",
            action="refine",
            observation=f"Using {len(valid_facts)} high-quality facts",
            parent_id="1",
        )
        steps["2"] = refine_step

        answer = self._build_chain_answer(valid_facts if valid_facts else facts, query)

        return {
            "query": query,
            "answer": answer,
            "reasoning_mode": self.mode.value,
            "steps": list(steps.values()),
            "confidence": sum(f.get("score", 0) for f in valid_facts)
            / max(len(valid_facts), 1),
            "sources": [f.get("source", "") for f in (valid_facts or facts)[:3]],
        }

    async def _critique_reason(
        self,
        query: str,
        facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if self.use_llm and self._llm_available and self._llm_router:
            return await self._llm_critique_reason(query, facts)

        steps: Dict[str, ReasoningStep] = {}

        claim_step = ReasoningStep(
            step_id="0",
            thought="Making initial claim based on facts",
            action="claim",
            observation=f"Formed claim from {len(facts)} facts",
        )
        steps["0"] = claim_step

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
        steps["1"] = step

        return {
            "query": query,
            "answer": answer,
            "reasoning_mode": self.mode.value,
            "steps": list(steps.values()),
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
    if isinstance(mode, str):
        mode = ReasoningMode(mode)
    needs_new = (
        _reasoning_engine is None
        or isinstance(_reasoning_engine.mode, str)
    )
    if not isinstance(mode, ReasoningMode):
        mode = ReasoningMode.CHAIN_OF_THOUGHTS
    if needs_new or _reasoning_engine.mode != mode:
        _reasoning_engine = ReasoningEngine(mode=mode)
    return _reasoning_engine
