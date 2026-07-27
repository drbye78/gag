"""
Reasoning Agent - LLM-based reasoning with multiple modes.

Supports DIRECT, CHAIN_OF_THOUGHT, TREE_OF_THOUGHTS, REFLECT,
and CRITIQUE modes. Integrates with multi-source retrieval results.
"""

import asyncio
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from llm.router import get_router
from core.middleware import sanitize_prompt_input
from agents.prompts import (
    SYSTEM_PERSONA,
    REASONING_PROTOCOL,
    TOOL_USAGE,
    OUTPUT_FORMAT,
)


class ReasonMode(str, Enum):
    DIRECT = "direct"
    CHAIN_OF_THOUGHT = "cot"
    TREE_OF_THOUGHTS = "tot"
    REFLECT = "reflect"
    CRITIQUE = "critique"


@dataclass
class AnswerWithCitations:
    """Reasoning output with optional inline citation markers."""
    answer: str
    citations: List[str] = field(default_factory=list)
    # citations holds the raw citation strings found in the answer, e.g. ["3", "7", "12"]


class ReasoningAgent:
    def __init__(
        self,
        mode: ReasonMode = ReasonMode.CHAIN_OF_THOUGHT,
        max_retries: int = 2,
        temperature: float = 0.7,
    ):
        self.router = get_router()
        self.mode = mode
        self.max_retries = max_retries
        self.temperature = temperature

        self.system_prompt = f"""{SYSTEM_PERSONA}

{REASONING_PROTOCOL}

{TOOL_USAGE}

{OUTPUT_FORMAT}

Think step-by-step in your reasoning.
State assumptions explicitly when uncertain.
Prefer platform-specific context when available over generic best practices."""

        self._metrics = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "avg_latency_ms": 0,
            "total_tokens": 0,
        }

    def _build_prompt(
        self,
        query: str,
        context: Dict[str, Any],
        intent: str,
        numbered: bool = False,
    ) -> str:
        reasoning_instruction = ""

        if self.mode == ReasonMode.CHAIN_OF_THOUGHT:
            reasoning_instruction = """Think step by step:
1. What is being asked?
2. What context do we have?
3. How does it map to the target platform?
4. What is the answer?"""

        elif self.mode == ReasonMode.CRITIQUE:
            reasoning_instruction = """After your answer, briefly evaluate:
- Is it correct?
- Is it relevant to the target platform?
- Any risks?"""

        elif self.mode == ReasonMode.TREE_OF_THOUGHTS:
            reasoning_instruction = """Explore multiple perspectives:
- What would an architect say?
- What would developer need?
- What would support advise?
Then provide the best answer."""

        elif self.mode == ReasonMode.DIRECT:
            reasoning_instruction = (
                "Give a direct, concise answer. "
                "Lead with the answer, then optionally add one line of supporting context. "
                "No preamble, no step-by-step breakdown unless the question demands it."
            )

        elif self.mode == ReasonMode.REFLECT:
            reasoning_instruction = (
                "Reason through this carefully, then reflect on your reasoning:\n"
                "1. What approach did you take and why?\n"
                "2. What assumptions did you make?\n"
                "3. Is there a better approach you overlooked?\n"
                "4. Provide your final answer based on this reflection."
            )

        base_prompt = f"""Query: {sanitize_prompt_input(query)}

Context:
{self._format_context(context, numbered=numbered)}
"""

        if tool_results := context.get("tool_results"):
            base_prompt += f"""

Tool Results:
{self._format_tool_results(tool_results)}
"""

        if reasoning_instruction:
            base_prompt += f"\n\n{reasoning_instruction}"

        base_prompt += f"\n\nIntent: {intent}"

        return base_prompt

    def _format_context(self, context: Dict[str, Any], numbered: bool = False) -> str:
        sections = []
        item_counter = 0

        for result in context.get("retrieval_results", []):
            source = result.get("source", "unknown")
            results_list = result.get("results", [])
            if results_list:
                sections.append(f"### {source.upper()}")
                for item in results_list[:5]:
                    item_counter += 1
                    if isinstance(item, dict):
                        content = item.get("content", "") or item.get("title", "")
                        if content:
                            prefix = f"[{item_counter}] " if numbered else ""
                            sections.append(f"- {prefix}{content[:300]}")
                    elif isinstance(item, str):
                        prefix = f"[{item_counter}] " if numbered else ""
                        sections.append(f"- {prefix}{item[:300]}")

        return "\n".join(sections) if sections else "No context found"

    def _format_tool_results(self, tool_results: List[Dict]) -> str:
        sections = []
        for result in tool_results:
            tool_name = result.get("tool", "unknown")
            sections.append(f"### {tool_name}")
            sections.append(
                f"Result: {result.get('output', {})}:\n{result.get('error', '')}"
            )
        return "\n".join(sections)

    async def _tree_reason(
        self, query: str, context: Dict[str, Any], intent: str, require_citations: bool = False
    ) -> str:
        """Run 3 parallel reasoning calls from different personas, then synthesize."""
        perspectives = [
            ("architect", "You are a solution architect. Evaluate this from an architectural perspective. Consider scalability, reliability, and system design."),
            ("developer", "You are a developer. Evaluate this from an implementation perspective. Consider code structure, APIs, and developer experience."),
            ("support", "You are a support engineer. Evaluate this from an operational perspective. Consider monitoring, debugging, and production issues."),
        ]

        # Run all 3 in parallel
        tasks = []
        for role, persona_prompt in perspectives:
            prompt = self._build_prompt(query, context, intent, numbered=require_citations)
            tasks.append(self.router.chat(
                prompt=f"{persona_prompt}\n\n{prompt}",
                system_prompt=self.system_prompt,
                temperature=self.temperature,
            ))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Extract answers from each perspective
        perspectives_text = []
        for i, (role, _) in enumerate(perspectives):
            result = results[i]
            if isinstance(result, Exception):
                perspectives_text.append(f"[{role}] Error: {str(result)}")
            elif result.choices:
                text = result.choices[0].get("message", {}).get("content", "")
                perspectives_text.append(f"[{role}]\n{text}")

        # Synthesize: run a final call to merge perspectives
        synthesis_prompt = f"""Query: {query}

Three perspectives on this problem:
{chr(10).join(perspectives_text)}

Synthesize these perspectives into a single, well-reasoned answer. Acknowledge disagreements and provide your best recommendation."""

        response = await self.router.chat(
            prompt=synthesis_prompt,
            system_prompt=self.system_prompt,
            temperature=self.temperature,
        )

        if response.choices:
            answer = response.choices[0].get("message", {}).get("content", "No response")
        else:
            answer = "Synthesis failed"

        return answer

    async def _reflect_reason(
        self, query: str, context: Dict[str, Any], intent: str, require_citations: bool = False
    ) -> str:
        """First-pass answer, then self-critique, then final synthesis."""
        # Pass 1: initial reasoning
        prompt = self._build_prompt(query, context, intent, numbered=require_citations)
        prompt += "\n\nProvide your initial answer to the query above."

        response_1 = await self.router.chat(
            prompt=prompt, system_prompt=self.system_prompt, temperature=self.temperature,
        )
        initial_answer = response_1.choices[0].get("message", {}).get("content", "") if response_1.choices else ""

        # Pass 2: self-critique
        critique_prompt = f"""Original query: {query}

Your initial answer:
{initial_answer}

Now critically evaluate your own answer:
1. What assumptions did you make? Are they valid?
2. What did you miss or overlook?
3. What would you change if you had more time or data?
4. Provide a revised, improved final answer incorporating these reflections."""

        response_2 = await self.router.chat(
            prompt=critique_prompt, system_prompt=self.system_prompt, temperature=self.temperature,
        )

        if response_2.choices:
            return response_2.choices[0].get("message", {}).get("content", "No response")
        return initial_answer  # fallback to first answer

    async def _critique_reason(
        self, query: str, context: Dict[str, Any], intent: str, require_citations: bool = False
    ) -> str:
        """Answer then evaluate in a separate call."""
        prompt = self._build_prompt(query, context, intent, numbered=require_citations)

        response_1 = await self.router.chat(
            prompt=prompt, system_prompt=self.system_prompt, temperature=self.temperature,
        )
        answer = response_1.choices[0].get("message", {}).get("content", "") if response_1.choices else ""

        critique_prompt = f"""Original query: {query}
Answer to evaluate:
{answer}

Briefly evaluate this answer:
- Is it correct? [YES/NO/UNCERTAIN]
- Is it relevant? [YES/NO/PARTIAL]
- Any risks or caveats? [list if any]

Then provide the final answer (same as above if correct, or revised if issues found)."""

        response_2 = await self.router.chat(
            prompt=critique_prompt, system_prompt=self.system_prompt, temperature=self.temperature,
        )

        if response_2.choices:
            return response_2.choices[0].get("message", {}).get("content", "")
        return answer

    async def generate_answer(
        self,
        query: str,
        retrieved_data: Dict[str, Any],
        tool_results: Optional[List[Dict]] = None,
        intent: str = "explain",
        require_citations: bool = False,
    ) -> AnswerWithCitations:
        start_time = time.time()

        context = {
            "retrieval_results": retrieved_data.get("results", []),
            "tool_results": tool_results or [],
            "intent": intent,
        }

        for attempt in range(self.max_retries + 1):
            try:
                if self.mode == ReasonMode.TREE_OF_THOUGHTS:
                    raw_answer = await self._tree_reason(query, context, intent, require_citations)
                elif self.mode == ReasonMode.REFLECT:
                    raw_answer = await self._reflect_reason(query, context, intent, require_citations)
                elif self.mode == ReasonMode.CRITIQUE:
                    raw_answer = await self._critique_reason(query, context, intent, require_citations)
                else:
                    # Direct or CoT — single call
                    prompt = self._build_prompt(query, context, intent, numbered=require_citations)
                    if require_citations:
                        prompt += (
                            "\n\nIMPORTANT: Each context item above is numbered like [1], [2]... "
                            "Cite source numbers that support each claim. Format: claim [N]."
                        )
                    response = await self.router.chat(
                        prompt=prompt, system_prompt=self.system_prompt, temperature=self.temperature,
                    )
                    raw_answer = response.choices[0].get("message", {}).get("content", "No response") if response.choices else "No response"

                citations = self._extract_citations(raw_answer) if require_citations else []
                self._update_metrics(True, len(raw_answer))
                return AnswerWithCitations(answer=raw_answer, citations=citations)
            except Exception as e:
                if attempt == self.max_retries:
                    self._update_metrics(False, 0)
                    return AnswerWithCitations(answer=f"Error: {str(e)}", citations=[])

        self._update_metrics(False, 0)
        return AnswerWithCitations(answer="Max retries exceeded", citations=[])

    async def generate_answer_streaming(
        self,
        query: str,
        retrieved_data: Dict[str, Any],
        tool_results: Optional[List[Dict]] = None,
        intent: str = "explain",
        require_citations: bool = False,
    ):
        """Stream answer tokens as an async generator. Yields str tokens."""
        # Only supports DIRECT and CHAIN_OF_THOUGHT modes for streaming
        context = {
            "retrieval_results": retrieved_data.get("results", []),
            "tool_results": tool_results or [],
            "intent": intent,
        }
        prompt = self._build_prompt(query, context, intent, numbered=require_citations)

        response = await self.router.chat(
            prompt=prompt, system_prompt=self.system_prompt, temperature=self.temperature, stream=True,
        )

        async for chunk in response:
            if hasattr(chunk, 'choices') and chunk.choices:
                delta = chunk.choices[0].get("delta", {}).get("content", "")
                if delta:
                    yield delta

    def _extract_citations(self, answer: str) -> List[str]:
        """Parse numeric citation references from answer text.

        Extracts individual citation numbers from patterns like [1], [3,5], [7].
        Returns a list of unique citation strings.
        """
        matches = re.findall(r'\[(\d+(?:[,\-]\d+)*)\]', answer)
        citations: set = set()
        for match in matches:
            for part in re.split(r'[,\-]', match):
                if part.strip().isdigit():
                    citations.add(part.strip())
        return sorted(citations, key=int)

    def _update_metrics(self, success: bool, response_length: int):
        self._metrics["total_requests"] += 1
        if success:
            self._metrics["successful"] += 1
        else:
            self._metrics["failed"] += 1
        self._metrics["total_tokens"] += response_length

    def get_metrics(self) -> Dict[str, Any]:
        return {
            **self._metrics,
            "success_rate": (
                self._metrics["successful"] / self._metrics["total_requests"]
                if self._metrics["total_requests"] > 0
                else 0
            ),
        }


def get_reasoning_agent() -> ReasoningAgent:
    return ReasoningAgent()
