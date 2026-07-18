"""
Orchestration Engine - Iterative agent loop with state tracking.

Coordinates Plan → Retrieve → Reason → Execute loop with parallel/sequential
execution, retry logic, and metrics.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional, cast

from agents.planner import ExecutionPlan, ExecutionStep, PlannerAgent
from agents.retrieval import RetrievalAgent
from agents.reasoning import ReasoningAgent
from agents.executor import ToolExecutor
from agents.validator import ValidatorAgent
from agents.registry import _registry as _agent_registry
from agents.types import AgentType
from core.memory import (
    get_memory_system,
    MemoryScope,
    MemoryTier,
    get_short_term_memory,
)

logger = logging.getLogger(__name__)


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ReasoningTraceEntry:
    step: str
    thinking: str
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class ExecutionState:
    step: ExecutionStep
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    reasoning_trace: List[ReasoningTraceEntry] = field(default_factory=list)

    @property
    def duration_ms(self) -> int:
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at) * 1000)
        return 0

    def add_reasoning_trace(
        self,
        step: str,
        thinking: str,
        evidence: Optional[List[str]] = None,
        confidence: float = 0.0,
    ) -> None:
        self.reasoning_trace.append(
            ReasoningTraceEntry(
                step=step,
                thinking=thinking,
                evidence=evidence or [],
                confidence=confidence,
            )
        )


class PlanRevision(Exception):
    def __init__(self, reason: str, new_steps: List[ExecutionStep]):
        self.reason = reason
        self.new_steps = new_steps


class OrchestrationMode(str, Enum):
    ITERATIVE = "iterative"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    BRANCHING = "branching"
    RECURSIVE = "recursive"


class StepExecutor(ABC):
    @abstractmethod
    async def execute(self, state: ExecutionState, context: Dict[str, Any]) -> Any:
        pass


class RetrieveStepExecutor(StepExecutor):
    def __init__(self, retriever: RetrievalAgent):
        self.retriever = retriever

    async def execute(self, state: ExecutionState, context: Dict[str, Any]) -> Any:
        source = state.step.source or "auto"
        query = context.get("query", "")
        limit = state.step.params.get("limit", 10)
        return await self.retriever.retrieve_single(query, source, limit)


class ToolStepExecutor(StepExecutor):
    def __init__(self, executor: ToolExecutor):
        self.executor = executor

    async def execute(self, state: ExecutionState, context: Dict[str, Any]) -> Any:
        tools = state.step.params.get("tools", [])
        args = context.get("tool_args", {})
        results = []
        for tool in tools:
            result = await self.executor.execute(tool, args)
            results.append(result)
        return results


class ReasonStepExecutor(StepExecutor):
    def __init__(self, reasoner: ReasoningAgent):
        self.reasoner = reasoner

    async def execute(self, state: ExecutionState, context: Dict[str, Any]) -> Any:
        query = context.get("query", "")
        retrieved = context.get("retrieval_results", {})
        tools = context.get("tool_results", [])
        intent = context.get("intent", "explain")
        return await self.reasoner.generate_answer(query, retrieved, tools, intent)


class ValidateStepExecutor(StepExecutor):
    """Validates the reasoning result against retrieved context.

    Runs accuracy, coherence, completeness, and safety checks.
    If validation fails with ERROR severity, the orchestrator can re-plan.
    """

    def __init__(self, validator: "ValidatorAgent"):
        self.validator = validator

    async def execute(self, state: ExecutionState, context: Dict[str, Any]) -> Any:
        query = context.get("query", "")
        answer = context.get("reason_result", "") or ""
        retrieval_results = context.get("retrieval_results", {})
        retrieved_context: List[Dict[str, Any]] = []

        # Flatten retrieval results into a list of context items
        if isinstance(retrieval_results, dict):
            for source, source_data in retrieval_results.items():
                if isinstance(source_data, dict):
                    for item in source_data.get("results", []):
                        if isinstance(item, dict):
                            retrieved_context.append(item)
                elif isinstance(source_data, list):
                    retrieved_context.extend(
                        item for item in source_data if isinstance(item, dict)
                    )
        elif isinstance(retrieval_results, list):
            retrieved_context = [
                item for item in retrieval_results if isinstance(item, dict)
            ]

        # Get reasoning trace from execution states
        reasoning_trace = [
            {"step": s.step.step_type, "thinking": str(s.result or "")[:200]}
            for s in context.get("_all_states", [])
            if s.status == StepStatus.COMPLETED and s.result
        ]

        result = await self.validator.validate_response(
            query=query,
            response=answer,
            retrieved_context=retrieved_context,
            reasoning_trace=reasoning_trace,
        )

        # Return as dict for JSON serialization
        return {
            "valid": result.valid,
            "score": result.score,
            "confidence": result.confidence,
            "issues": [
                {
                    "category": issue.category,
                    "severity": issue.severity,
                    "message": issue.message,
                    "evidence": issue.evidence,
                    "suggestion": issue.suggestion,
                }
                for issue in result.issues
            ],
            "metadata": result.metadata,
        }


class AnalyzeStepExecutor(StepExecutor):
    """Analyze step executor that integrates with actual analysis tools."""

    def __init__(self):
        self._analyzers: Dict[str, Any] = {}

    async def execute(self, state: ExecutionState, context: Dict[str, Any]) -> Any:
        action = state.step.action

        if action == "analyze_ir":
            return await self._analyze_ir(context)
        elif action == "analyze_logs":
            return await self._analyze_logs(context)
        elif action == "analyze_architecture":
            return await self._analyze_architecture(context)

        logger.warning("Unknown analyze action: %s", action)
        return {"analysis": None, "error": f"Unknown action: {action}"}

    async def _analyze_ir(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze intermediate representation from the context."""
        ir_context = context.get("ir_context", {})
        return {
            "ir_analysis": {
                "components_found": len(ir_context.get("components", [])),
                "relationships_found": len(ir_context.get("relationships", [])),
                "completeness": self._calculate_ir_completeness(ir_context),
            },
        }

    async def _analyze_logs(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze log data from telemetry sources."""
        retrieval = context.get("retrieval_results", {})
        telemetry_data = retrieval.get("telemetry", {})
        return {
            "log_analysis": {
                "entries_analyzed": len(telemetry_data.get("results", [])),
                "error_patterns": self._extract_error_patterns(telemetry_data),
                "summary": "Log analysis completed" if telemetry_data else "No log data available",
            },
        }

    async def _analyze_architecture(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze architecture data from graph and doc sources."""
        retrieval = context.get("retrieval_results", {})
        graph_data = retrieval.get("graph", {})
        return {
            "architecture_analysis": {
                "services_found": len(graph_data.get("results", [])),
                "relationships_mapped": len(graph_data.get("edges", [])),
            },
        }

    @staticmethod
    def _calculate_ir_completeness(ir: Dict[str, Any]) -> float:
        """Calculate how complete the IR is (0.0 to 1.0)."""
        score = 0.0
        if ir.get("components"):
            score += 0.4
        if ir.get("relationships"):
            score += 0.3
        if ir.get("data_flows"):
            score += 0.3
        return min(score, 1.0)

    @staticmethod
    def _extract_error_patterns(telemetry: Dict[str, Any]) -> List[str]:
        """Extract error patterns from telemetry data."""
        patterns = []
        for result in telemetry.get("results", []):
            content = result.get("content", "").lower()
            if any(kw in content for kw in ["error", "exception", "fail", "critical"]):
                patterns.append(result.get("content", "")[:200])
        return patterns[:10]


def _refine_query_from_tool_results(
    query: str,
    tool_results: List[Dict[str, Any]],
    retrieved: Dict[str, Any],
) -> str:
    if not tool_results:
        return query

    refinements = []
    for result in tool_results:
        if isinstance(result, dict):
            tool_name = result.get("tool_name", "")
            output = result.get("output", {})

            if tool_name == "architecture_evaluate":
                score = output.get("score", 0)
                if score < 0.7:
                    refinements.append(f"architectural issues found (score: {score})")
            elif tool_name == "security_validate":
                issues = output.get("issues", [])
                if issues:
                    refinements.append(f"security issues: {len(issues)} found")
            elif tool_name == "cost_estimate":
                cost = output.get("estimated_cost", 0)
                refinements.append(f"cost estimate: ${cost}")

    if refinements:
        return f"{query} [Analysis: {'; '.join(refinements)}]"
    return query


class OrchestrationEngine:
    def __init__(
        self,
        max_iterations: int = 3,
        max_retries: int = 2,
        parallel_execution: bool = True,
    ):
        self.max_iterations = max_iterations
        self.max_retries = max_retries
        self.parallel_execution = parallel_execution

        # Use the agent registry for agent creation; fall back to direct instantiation
        try:
            # Ensure built-in agents are registered
            import agents._register  # noqa: F401

            self.planner = _agent_registry.get_factory(AgentType.PLANNER)()
            self.retriever = _agent_registry.get_factory(AgentType.RETRIEVAL)()
            self.reasoner = _agent_registry.get_factory(AgentType.REASONING)()
            self.executor = _agent_registry.get_factory(AgentType.EXECUTOR)()
            self.validator = _agent_registry.get_factory(AgentType.VALIDATOR)()
        except (KeyError, ImportError):
            # Fallback if registry not populated or import fails
            self.planner = PlannerAgent()
            self.retriever = RetrievalAgent()
            self.reasoner = ReasoningAgent()
            self.executor = ToolExecutor()
            self.validator = ValidatorAgent()

        self._executors = self._init_executors()
        self._initialize_metrics()

    def _init_executors(self) -> Dict[str, StepExecutor]:
        return {
            "retrieve": RetrieveStepExecutor(self.retriever),
            "tool": ToolStepExecutor(self.executor),
            "reason": ReasonStepExecutor(self.reasoner),
            "validate": ValidateStepExecutor(self.validator),
            "analyze": AnalyzeStepExecutor(),
        }

    def _initialize_metrics(self):
        self.metrics = {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "total_steps_executed": 0,
            "total_retries": 0,
            "avg_execution_time_ms": 0.0,
        }

    async def _execute_step(
        self,
        state: ExecutionState,
        context: Dict[str, Any],
    ) -> ExecutionState:
        step_type = state.step.step_type
        executor = self._executors.get(step_type)

        if not executor:
            state.status = StepStatus.SKIPPED
            state.error = f"No executor for step type: {step_type}"
            return state

        # Retry loop: actually re-execute on failure
        for attempt in range(self.max_retries + 1):
            state.status = StepStatus.RUNNING
            state.started_at = time.time()

            try:
                state.result = await executor.execute(state, context)
                state.status = StepStatus.COMPLETED
                break  # Success — exit retry loop
            except Exception as e:
                from core.errors import OrchestrationError
                if attempt < self.max_retries:
                    state.retry_count += 1
                    self.metrics["total_retries"] += 1
                    logger.warning(
                        "Step %s failed (attempt %d/%d): %s — retrying",
                        step_type,
                        attempt + 1,
                        self.max_retries,
                        e,
                    )
                    import random as _random
                    delay = min(2 ** attempt + _random.uniform(0, 1), 30.0)
                    await asyncio.sleep(delay)  # Exponential backoff with jitter
                else:
                    state.status = StepStatus.FAILED
                    state.error = f"{type(e).__name__}: {str(e)}"
                    logger.error(
                        "Step %s failed permanently after %d attempts: %s",
                        step_type,
                        self.max_retries,
                        e,
                    )
            finally:
                state.completed_at = time.time()

        return state

    async def _execute_plan_parallel(
        self,
        plan: ExecutionPlan,
        context: Dict[str, Any],
    ) -> List[ExecutionState]:
        states = []

        for step in plan.steps:
            state = ExecutionState(step=step)
            states.append(state)

        tasks = [self._execute_step(s, context) for s in states]
        await asyncio.gather(*tasks, return_exceptions=True)

        for step, state in zip(plan.steps, states):
            if state.result is not None:
                context[f"{step.step_type}_result"] = state.result

        return states

    async def _execute_plan_sequential(
        self,
        plan: ExecutionPlan,
        context: Dict[str, Any],
    ) -> List[ExecutionState]:
        states = []

        for step in plan.steps:
            state = ExecutionState(step=step)
            state = await self._execute_step(state, context)
            states.append(state)

            if state.status == StepStatus.FAILED:
                break

            context[f"{step.step_type}_result"] = state.result

        return states

    async def _execute_plan_waves(
        self,
        plan: ExecutionPlan,
        context: Dict[str, Any],
    ) -> List[ExecutionState]:
        """Execute plan in dependency-ordered waves.

        Wave 0: retrieve + tool (independent, run in parallel)
        Wave 1: analyze (needs retrieval)
        Wave 2: reason (needs retrieval + analyze)
        Wave 3: validate (needs reason)

        Each wave runs its steps in parallel; results propagate to the
        next wave via the context dict.
        """
        tier_map = {
            "retrieve": 0,
            "tool": 0,
            "analyze": 1,
            "reason": 2,
            "validate": 3,
        }

        # Group steps by tier
        tiers: Dict[int, List[ExecutionStep]] = {}
        for step in plan.steps:
            tier = tier_map.get(step.step_type, 0)
            tiers.setdefault(tier, []).append(step)

        all_states = []
        for tier_num in sorted(tiers.keys()):
            tier_steps = tiers[tier_num]
            states = []
            for step in tier_steps:
                state = ExecutionState(step=step)
                states.append(state)

            # Run all steps in this tier in parallel
            tasks = [self._execute_step(s, context) for s in states]
            await asyncio.gather(*tasks, return_exceptions=True)

            # Propagate results into context for the next tier
            for step, state in zip(tier_steps, states):
                context[f"{step.step_type}_result"] = state.result
                if step.step_type == "retrieve":
                    # Aggregate retrieval results for downstream steps
                    if "retrieval_results" not in context:
                        context["retrieval_results"] = {}
                    if state.result and isinstance(state.result, dict):
                        source = state.result.get("source", step.source or "unknown")
                        context["retrieval_results"][source] = state.result
                elif step.step_type == "reason":
                    context["reason_result"] = state.result or ""
                elif step.step_type == "validate":
                    context["validation_result"] = state.result

            all_states.extend(states)

        return all_states

    async def _should_revise(
        self,
        states: List[ExecutionState],
        plan: ExecutionPlan,
    ) -> Optional[str]:
        failed = [s for s in states if s.status == StepStatus.FAILED]
        if failed:
            return f"Step failed: {failed[0].error}"

        completed = [s for s in states if s.status == StepStatus.COMPLETED]
        if len(completed) < len(plan.steps) / 2:
            return "Less than 50% steps completed"

        return None

    async def _revision_needed(
        self,
        states: List[ExecutionState],
        context: Dict[str, Any],
    ) -> bool:
        for state in states:
            if state.status == StepStatus.FAILED:
                return True
            if state.status == StepStatus.COMPLETED and state.result:
                if isinstance(state.result, dict):
                    if state.result.get("needs_revision"):
                        return True
        return False

    async def execute(
        self,
        query: str,
        ir_context: Optional[Dict[str, Any]] = None,
        max_iterations: Optional[int] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()
        max_iterations = max_iterations or self.max_iterations

        context = {
            "query": query,
            "ir_context": ir_context or {},
            "retrieval_results": {},
            "tool_results": [],
        }

        memory = get_memory_system()
        session_context = memory.get_context(max_entries=5)
        if session_context:
            context["session_history"] = session_context

        plan = await self.planner.plan(query, ir_context)
        context["intent"] = plan.intent

        all_states = []

        for iteration in range(max_iterations):
            context["iteration"] = iteration

            if self.parallel_execution:
                states = await self._execute_plan_waves(plan, context)
            else:
                states = await self._execute_plan_sequential(plan, context)

            all_states.extend(states)

            context["retrieval_results"] = self._aggregate_results(states)

            tool_results = context.get("tool_results", [])
            if tool_results:
                refined_query = _refine_query_from_tool_results(
                    query,
                    tool_results,
                    context["retrieval_results"],
                )
                if refined_query != query:
                    context["query"] = refined_query

            if not await self._revision_needed(states, context):
                break

            should_revise = await self._should_revise(states, plan)
            if should_revise and iteration < max_iterations - 1:
                new_plan = await self.planner.plan(query, context)
                plan = new_plan

        reasoning_state = ExecutionState(
            step=ExecutionStep(step_type="reason", action="generate_answer")
        )
        reasoning_state = await self._execute_step(reasoning_state, context)

        # Store the reasoning result so the validate executor can access it
        context["reason_result"] = reasoning_state.result or ""

        # Run validation after reasoning
        validation_state = ExecutionState(
            step=ExecutionStep(step_type="validate", action="validate_response")
        )
        validation_state = await self._execute_step(validation_state, context)

        execution_time = int((time.time() - start_time) * 1000)

        has_errors = any(s.error for s in all_states) or reasoning_state.error or validation_state.error
        self._update_metrics(not has_errors, len(all_states), execution_time)

        memory = get_memory_system()
        await memory.remember(
            key=f"execution:{int(start_time)}",
            value={
                "query": query,
                "intent": plan.intent,
                "iterations": len(all_states),
                "tool_results": context.get("tool_results", []),
            },
            tier=MemoryTier.PROJECT,
        )

        # Extract validation result for the response
        validation_result = validation_state.result if validation_state.result else {
            "valid": True,
            "score": 0.0,
            "confidence": 0.0,
            "issues": [],
            "metadata": {},
        }

        return {
            "query": query,
            "answer": reasoning_state.result or "No response",
            "intent": plan.intent,
            "plan": plan.to_dict(),
            "execution": {
                "iterations": len(all_states),
                "steps": [s.__dict__ for s in all_states],
                "took_ms": execution_time,
            },
            "validation": validation_result,
            "metrics": self.metrics,
        }

    def _aggregate_results(
        self,
        states: List[ExecutionState],
    ) -> Dict[str, Any]:
        results = {}
        for state in states:
            if state.status == StepStatus.COMPLETED and state.result:
                results[state.step.step_type] = state.result
        return results

    def _update_metrics(
        self,
        success: bool,
        steps: int,
        time_ms: int,
    ) -> None:
        self.metrics["total_runs"] += 1
        if success:
            self.metrics["successful_runs"] += 1
        else:
            self.metrics["failed_runs"] += 1
        self.metrics["total_steps_executed"] += steps

        # Running mean (not exponential moving average)
        total_runs = self.metrics["total_runs"]
        prev_avg = self.metrics["avg_execution_time_ms"]
        self.metrics["avg_execution_time_ms"] = (
            prev_avg * (total_runs - 1) + time_ms
        ) / total_runs

    async def execute_streaming(
        self,
        query: str,
        ir_context: Optional[Dict[str, Any]] = None,
        max_iterations: Optional[int] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Streaming execution that yields step-by-step progress updates."""
        start_time = time.time()
        max_iterations = max_iterations or self.max_iterations

        context = {
            "query": query,
            "ir_context": ir_context or {},
            "retrieval_results": {},
            "tool_results": [],
        }

        yield {"type": "start", "query": query}

        plan = await self.planner.plan(query, ir_context)
        context["intent"] = plan.intent
        yield {"type": "plan", "plan": plan.to_dict()}

        all_states = []

        for iteration in range(max_iterations):
            context["iteration"] = iteration
            yield {"type": "iteration_start", "iteration": iteration}

            states = []
            for step in plan.steps:
                state = ExecutionState(step=step)
                state = await self._execute_step(state, context)
                states.append(state)

                yield {
                    "type": "step_complete",
                    "step_type": step.step_type,
                    "status": state.status.value,
                    "result": str(state.result)[:500] if state.result else None,
                    "error": state.error,
                }

                if state.status == StepStatus.FAILED:
                    break

                context[f"{step.step_type}_result"] = state.result

            all_states.extend(states)
            context["retrieval_results"] = self._aggregate_results(states)

            if not await self._revision_needed(states, context):
                break

            should_revise = await self._should_revise(states, plan)
            if should_revise and iteration < max_iterations - 1:
                new_plan = await self.planner.plan(query, context)
                plan = new_plan
                yield {"type": "plan_revised", "plan": plan.to_dict()}

        reasoning_state = ExecutionState(
            step=ExecutionStep(step_type="reason", action="generate_answer")
        )
        reasoning_state = await self._execute_step(reasoning_state, context)

        execution_time = int((time.time() - start_time) * 1000)
        self._update_metrics(True, len(all_states), execution_time)

        yield {
            "type": "complete",
            "query": query,
            "answer": reasoning_state.result or "No response",
            "intent": plan.intent,
            "execution": {
                "iterations": len(all_states),
                "took_ms": execution_time,
            },
        }

    async def execute_branching(
        self,
        query: str,
        ir_context: Optional[Dict[str, Any]] = None,
        branches: int = 3,
    ) -> Dict[str, Any]:
        start_time = time.time()

        context = {
            "query": query,
            "ir_context": ir_context or {},
            "retrieval_results": {},
            "tool_results": [],
            "branch_results": [],
        }

        branch_queries = await self._decompose_query_branches(query, branches)
        branch_tasks = []

        for branch_query in branch_queries:
            task = self._execute_branch(branch_query, context)
            branch_tasks.append(task)

        branch_outcomes = await asyncio.gather(*branch_tasks, return_exceptions=True)

        valid_results = [
            cast(Dict[str, Any], r) 
            for r in branch_outcomes 
            if not isinstance(r, Exception)
        ]

        merged_context = self._merge_branch_results(valid_results, context)

        final_result = await self.execute(
            merged_context.get("merged_query", query), ir_context
        )

        execution_time = int((time.time() - start_time) * 1000)

        return {
            "query": query,
            "answer": final_result.get("answer", ""),
            "branch_results": valid_results,
            "strategy": "branching",
            "took_ms": execution_time,
        }

    async def _execute_branch(
        self,
        branch_query: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        plan = await self.planner.plan(branch_query, context.get("ir_context", {}))

        branch_context = context.copy()
        branch_context["retrieval_results"] = {}

        states = await self._execute_plan_parallel(plan, branch_context)

        return {
            "query": branch_query,
            "states": [s.__dict__ for s in states],
            "result": self._aggregate_results(states),
        }

    async def _decompose_query_branches(
        self,
        query: str,
        branches: int,
    ) -> List[str]:
        """Decompose query into branches using LLM, with keyword fallback."""
        # Try LLM-based decomposition
        try:
            from llm.router import get_router
            from core.llm_utils import extract_json_from_response
            router = get_router()
            prompt = f"""Decompose this query into {branches} independent sub-queries for parallel analysis.
Query: {query}
Return a JSON array of {branches} sub-query strings, each exploring a different aspect."""
            response = await router.chat(prompt=prompt, temperature=0.5, max_tokens=500)
            result = extract_json_from_response(response)
            if isinstance(result, list) and len(result) >= 2:
                return [str(q) for q in result[:branches]]
        except Exception:
            pass

        # Fallback: simple keyword-based decomposition
        return self._decompose_query_branches_fallback(query, branches)

    def _decompose_query_branches_fallback(
        self,
        query: str,
        branches: int,
    ) -> List[str]:
        question_words = {"how", "what", "why", "when", "where", "which"}
        query_lower = query.lower()

        words = query_lower.split()
        topics = [w for w in words if len(w) > 3]

        branch_queries = []

        if " vs " in query_lower:
            sides = query.split(" vs ")
            for side in sides:
                branch_queries.append(f"{side} pros cons")
        elif any(qw in query_lower for qw in question_words):
            branch_queries.append(f"{query} detailed explanation")
            branch_queries.append(f"{query} practical examples")
            branch_queries.append(f"{query} common issues solutions")
        else:
            for i, topic in enumerate(topics[:branches]):
                branch_queries.append(f"{topic} {query}")

        while len(branch_queries) < branches:
            branch_queries.append(query)

        return branch_queries[:branches]

    def _merge_branch_results(
        self,
        results: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        all_contents = []

        for result in results:
            agg = result.get("result", {})
            for val in agg.values():
                if isinstance(val, list):
                    all_contents.extend(val)
                elif isinstance(val, str):
                    all_contents.append(val)

        merged_query = " ".join(all_contents[:5])

        return {
            "merged_query": merged_query,
            "all_results": results,
        }

    async def execute_recursive(
        self,
        query: str,
        ir_context: Optional[Dict[str, Any]] = None,
        depth: int = 3,
    ) -> Dict[str, Any]:
        start_time = time.time()

        context = {
            "query": query,
            "ir_context": ir_context or {},
            "retrieval_results": {},
            "tool_results": [],
            "recursive_depth": 0,
        }

        final_result = await self._recursive_execute(query, context, depth)

        execution_time = int((time.time() - start_time) * 1000)

        return {
            "query": query,
            "answer": final_result.get("answer", ""),
            "strategy": "recursive",
            "depth": depth,
            "took_ms": execution_time,
        }

    async def _recursive_execute(
        self,
        query: str,
        context: Dict[str, Any],
        remaining_depth: int,
    ) -> Dict[str, Any]:
        if remaining_depth <= 0:
            return {"answer": "Maximum recursion depth reached"}

        plan = await self.planner.plan(query, context.get("ir_context", {}))

        context["recursive_depth"] += 1

        states = await self._execute_plan_sequential(plan, context)

        aggregated = self._aggregate_results(states)

        if aggregated:
            sub_queries = await self._extract_sub_queries(aggregated, query)

            if sub_queries and remaining_depth > 1:
                sub_results = []
                for sq in sub_queries[:2]:
                    sub_result = await self._recursive_execute(
                        sq, context, remaining_depth - 1
                    )
                    sub_results.append(sub_result)

                return {
                    "answer": f"{aggregated} {' '.join([r.get('answer', '') for r in sub_results])}",
                    "sub_results": sub_results,
                }

        return {
            "answer": str(aggregated) if aggregated else "No result",
            "depth": context["recursive_depth"],
        }

    async def _extract_sub_queries(
        self,
        aggregated: Dict[str, Any],
        original_query: str = "",
    ) -> List[str]:
        """Extract sub-queries using LLM, with truncation fallback."""
        # Build context from aggregated results
        context_parts = []
        for key, value in aggregated.items():
            if isinstance(value, str) and len(value) > 20:
                context_parts.append(f"{key}: {value[:200]}")
            elif isinstance(value, dict):
                content = value.get("content", value.get("answer", ""))
                if content:
                    context_parts.append(str(content)[:200])

        if not context_parts:
            return []

        # Try LLM-based decomposition
        try:
            from llm.router import get_router
            from core.llm_utils import extract_json_from_response
            router = get_router()
            context = "\n".join(context_parts[:3])
            prompt = f"""Break this query into 2-3 simpler sub-queries based on the retrieved context.
Original query: {original_query or "N/A"}
Context:
{context}

Return a JSON array of 2-3 sub-query strings."""
            response = await router.chat(prompt=prompt, temperature=0.3, max_tokens=300)
            result = extract_json_from_response(response)
            if isinstance(result, list) and len(result) >= 1:
                return [str(q) for q in result[:3]]
        except Exception:
            pass

        # Fallback: truncation-based
        queries = []
        for part in context_parts:
            words = part.split()
            if len(words) > 10:
                queries.append(" ".join(words[:10]))
        return queries[:3]


_orchestration_engine: Optional[OrchestrationEngine] = None


def get_orchestration_engine() -> OrchestrationEngine:
    global _orchestration_engine
    if _orchestration_engine is None:
        _orchestration_engine = OrchestrationEngine()
    return _orchestration_engine
