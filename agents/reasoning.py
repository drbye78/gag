"""
Reasoning Agent - LLM-based reasoning with multiple modes.

Supports DIRECT, CHAIN_OF_THOUGHT, TREE_OF_THOUGHTS, REFLECT,
and CRITIQUE modes. Integrates with multi-source retrieval results.
"""

import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from agents.prompts import (
    OUTPUT_FORMAT,
    REASONING_PROTOCOL,
    SYSTEM_PERSONA,
    TOOL_USAGE,
)
from core.middleware import sanitize_prompt_input
from llm.router import get_router

logger = logging.getLogger(__name__)


class ReasonMode(str, Enum):
    DIRECT = "direct"
    CHAIN_OF_THOUGHT = "cot"
    TREE_OF_THOUGHTS = "tot"
    REFLECT = "reflect"
    CRITIQUE = "critique"
    DOC = "doc"


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
        # Clamp temperature to valid range [0.0, 2.0]
        if temperature < 0.0 or temperature > 2.0:
            logger.warning("Temperature %.2f out of bounds [0.0, 2.0]; clamping", temperature)
        self.temperature = max(0.0, min(2.0, temperature))

        self.system_prompt = f"""{SYSTEM_PERSONA}

{REASONING_PROTOCOL}

{TOOL_USAGE}

{OUTPUT_FORMAT}

Think step-by-step in your reasoning.
State assumptions explicitly when uncertain.
Prefer SAP BTP context over generic best practices."""

        self._metrics = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "avg_latency_ms": 0,
            "total_char_estimate": 0,
        }

    def _build_prompt(
        self,
        query: str,
        context: Dict[str, Any],
        intent: str,
    ) -> str:
        reasoning_instruction = ""

        if self.mode == ReasonMode.CHAIN_OF_THOUGHT:
            reasoning_instruction = """Think step by step:
1. What is being asked?
2. What context do we have?
3. How does it map to SAP BTP?
4. What is the answer?"""

        elif self.mode == ReasonMode.CRITIQUE:
            reasoning_instruction = """After your answer, briefly evaluate:
- Is it correct?
- Is it relevant to SAP BTP?
- Any risks?"""

        elif self.mode == ReasonMode.TREE_OF_THOUGHTS:
            reasoning_instruction = """Explore multiple perspectives for SAP BTP:
- What would an architect say?
- What would developer need?
- What would support advise?
Then provide the best answer."""

        base_prompt = f"""Query: {sanitize_prompt_input(query)}

Context:
{sanitize_prompt_input(self._format_context(context))}
"""

        if tool_results := context.get("tool_results"):
            base_prompt += f"""

Tool Results:
{sanitize_prompt_input(self._format_tool_results(tool_results))}
"""

        if reasoning_instruction:
            base_prompt += f"\n\n{reasoning_instruction}"

        base_prompt += f"\n\nIntent: {sanitize_prompt_input(str(intent))}"

        return base_prompt

    def _format_context(self, context: Dict[str, Any]) -> str:
        sections = []

        for result in context.get("retrieval_results", []):
            source = result.get("source", "unknown")
            results_list = result.get("results", [])
            if results_list:
                sections.append(f"### {source.upper()}")
                for item in results_list[:5]:
                    if isinstance(item, dict):
                        content = item.get("content", "") or item.get("title", "")
                        if content:
                            sections.append(f"- {content[:300]}")
                    elif isinstance(item, str):
                        sections.append(f"- {item[:300]}")

        return "\n".join(sections) if sections else "No context found"

    def _format_tool_results(self, tool_results: List[Dict]) -> str:
        sections = []
        for result in tool_results:
            tool_name = result.get("tool", "unknown")
            sections.append(f"### {tool_name}")
            output = result.get("output", {})
            sections.append(f"Result: {output}")
            error = result.get("error")
            if error:
                # Sanitize: only include short error summary, no stack traces
                sanitized = str(error).split("\n")[0][:200]
                sections.append(f"Error: {sanitized}")
        return "\n".join(sections)

    async def generate_answer(
        self,
        query: str,
        retrieved_data: Dict[str, Any],
        tool_results: Optional[List[Dict]] = None,
        intent: str = "explain",
    ) -> str:
        start_time = time.time()

        context = {
            "retrieval_results": retrieved_data.get("results", []),
            "tool_results": tool_results or [],
            "intent": intent,
        }

        prompt = self._build_prompt(query, context, intent)

        for attempt in range(self.max_retries + 1):
            try:
                response = await self.router.chat(
                    prompt=prompt,
                    system_prompt=self.system_prompt,
                    temperature=self.temperature,
                )

                if response.choices:
                    answer = (
                        response.choices[0]
                        .get("message", {})
                        .get("content", "No response generated")
                    )
                    # Approximate token count: ~4 chars per token for English
                    token_estimate = len(answer) // 4
                    self._update_metrics(True, token_estimate)
                    return answer

            except Exception:
                if attempt == self.max_retries:
                    self._update_metrics(False, 0)
                    return f"Error: Reasoning failed after {self.max_retries + 1} attempts"

        self._update_metrics(False, 0)
        return "Max retries exceeded"

    def _update_metrics(self, success: bool, response_length: int):
        self._metrics["total_requests"] += 1
        if success:
            self._metrics["successful"] += 1
        else:
            self._metrics["failed"] += 1
        self._metrics["total_char_estimate"] += response_length

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
