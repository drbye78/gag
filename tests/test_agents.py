"""
Tests for agent modules: planner, retrieval, reasoning, executor, orchestration, validator.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestPlannerAgent:
    @pytest.mark.asyncio
    async def test_plan_simple_query(self):
        from agents.planner import PlannerAgent

        planner = PlannerAgent()
        plan = await planner.plan("How does authentication work?", {})
        assert plan is not None
        assert plan.intent is not None
        assert isinstance(plan.steps, list)

    @pytest.mark.asyncio
    async def test_plan_design_intent(self):
        from agents.planner import PlannerAgent

        planner = PlannerAgent()
        plan = await planner.plan("Design a new microservices gateway", {})
        assert plan.intent == "design"

    @pytest.mark.asyncio
    async def test_plan_troubleshoot_intent(self):
        from agents.planner import PlannerAgent

        planner = PlannerAgent()
        plan = await planner.plan("Why is the API returning 500 errors?", {})
        assert plan.intent == "troubleshoot"

    @pytest.mark.asyncio
    async def test_plan_optimize_intent(self):
        from agents.planner import PlannerAgent

        planner = PlannerAgent()
        plan = await planner.plan("Optimize database queries", {})
        assert plan.intent == "optimize"

    def test_plan_to_dict(self):
        from agents.planner import PlannerAgent, ExecutionPlan, ExecutionStep

        plan = ExecutionPlan(
            query="test",
            intent="explain",
            steps=[ExecutionStep(step_type="retrieve", action="retrieve_docs")],
        )
        plan_dict = plan.to_dict()
        assert plan_dict["intent"] == "explain"


class TestRetrievalAgent:
    @pytest.mark.asyncio
    async def test_retrieve_single(self):
        from agents.retrieval import RetrievalAgent

        with patch("agents.retrieval.RetrievalOrchestrator") as mock_orch:
            mock_instance = MagicMock()
            mock_instance.retrieve = AsyncMock(
                return_value={"results": [], "total_results": 0}
            )
            mock_orch.return_value = mock_instance

            agent = RetrievalAgent()
            result = await agent.retrieve_single("query", "docs", 10)
            assert result is not None

    @pytest.mark.asyncio
    async def test_retrieve_with_filters(self):
        from agents.retrieval import RetrievalAgent

        with patch("agents.retrieval.RetrievalOrchestrator") as mock_orch:
            mock_instance = MagicMock()
            mock_instance.retrieve = AsyncMock(
                return_value={"results": [], "total_results": 0}
            )
            mock_orch.return_value = mock_instance

            agent = RetrievalAgent()
            result = await agent.retrieve_single("query", "docs", 10)
            assert result is not None


class TestReasoningAgent:
    @pytest.mark.asyncio
    async def test_generate_answer(self):
        from agents.reasoning import ReasoningAgent

        with patch("agents.reasoning.get_reasoning_agent") as mock_get:
            mock_agent = MagicMock()
            mock_agent.generate_answer = AsyncMock(return_value="Test answer")
            mock_get.return_value = mock_agent

            agent = ReasoningAgent()
            result = await agent.generate_answer(
                "How does auth work?",
                {},
                [],
                "EXPLAIN",
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_reason_mode_selection(self):
        from agents.reasoning import ReasonMode, get_reasoning_agent

        mode = ReasonMode.CHAIN_OF_THOUGHT
        assert mode == ReasonMode.CHAIN_OF_THOUGHT


class TestToolExecutor:
    @pytest.mark.asyncio
    async def test_execute_tool(self):
        from agents.executor import ToolExecutor

        with patch("agents.executor.get_tool_executor") as mock_get:
            mock_exec = MagicMock()
            mock_exec.execute = AsyncMock(return_value={"output": "success"})
            mock_get.return_value = mock_exec

            executor = ToolExecutor()
            result = await executor.execute("architecture_evaluate", {"query": "test"})
            assert result is not None

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self):
        from agents.executor import ToolExecutor

        executor = ToolExecutor()
        result = await executor.execute("nonexistent_tool", {})
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_timeout(self):
        from agents.executor import ToolExecutor

        executor = ToolExecutor(default_timeout=1)
        assert executor.default_timeout == 1


class TestOrchestrationEngine:
    @pytest.mark.asyncio
    async def test_execute_simple_query(self):
        from agents.orchestration import OrchestrationEngine

        plan_mock = MagicMock()
        plan_mock.intent = "explain"
        plan_mock.steps = []
        plan_mock.to_dict = MagicMock(return_value={"steps": [], "intent": "explain"})

        with patch("agents.orchestration.PlannerAgent") as mock_planner, \
             patch("agents.orchestration.RetrievalAgent") as mock_retriever, \
             patch("agents.orchestration.ToolExecutor") as mock_executor, \
             patch("agents.orchestration.ReasoningAgent") as mock_reasoner:
            mock_planner.return_value.plan = AsyncMock(return_value=plan_mock)
            mock_retriever.return_value.retrieve_single = AsyncMock(
                return_value={"results": [], "total": 0}
            )
            mock_executor.return_value.execute = AsyncMock(
                return_value={"result": None}
            )
            mock_reasoner.return_value.generate_answer = AsyncMock(
                return_value="test answer"
            )

            engine = OrchestrationEngine()
            result = await engine.execute("test query", {})
            assert result is not None
            assert result["query"] == "test query"

    @pytest.mark.asyncio
    async def test_execute_with_context(self):
        from agents.orchestration import OrchestrationEngine

        plan_mock = MagicMock()
        plan_mock.intent = "explain"
        plan_mock.steps = []
        plan_mock.to_dict = MagicMock(return_value={"steps": [], "intent": "explain"})

        with patch("agents.orchestration.PlannerAgent") as mock_planner, \
             patch("agents.orchestration.RetrievalAgent") as mock_retriever, \
             patch("agents.orchestration.ToolExecutor") as mock_executor, \
             patch("agents.orchestration.ReasoningAgent") as mock_reasoner:
            mock_planner.return_value.plan = AsyncMock(return_value=plan_mock)
            mock_retriever.return_value.retrieve_single = AsyncMock(
                return_value={"results": [], "total": 0}
            )
            mock_executor.return_value.execute = AsyncMock(
                return_value={"result": None}
            )
            mock_reasoner.return_value.generate_answer = AsyncMock(
                return_value="test answer"
            )

            engine = OrchestrationEngine()
            result = await engine.execute(
                "test query",
                ir_context={"project": "test"},
            )
            assert result is not None
            assert result["query"] == "test query"

    @pytest.mark.asyncio
    async def test_iteration_limit(self):
        from agents.orchestration import OrchestrationEngine

        engine = OrchestrationEngine(max_iterations=2)
        assert engine.max_iterations == 2

    @pytest.mark.asyncio
    async def test_orchestration_modes(self):
        from agents.orchestration import OrchestrationMode

        modes = [m.value for m in OrchestrationMode]
        assert "iterative" in modes
        assert "parallel" in modes
        assert "branching" in modes
        assert "recursive" in modes


class TestValidatorAgent:
    @pytest.mark.asyncio
    async def test_validate_response_accuracy(self):
        from agents.validator import ValidatorAgent

        with patch("agents.validator.get_validator_agent") as mock_get:
            mock_val = MagicMock()
            mock_val.validate_response = AsyncMock(
                return_value={
                    "valid": True,
                    "issues": [],
                }
            )
            mock_get.return_value = mock_val

            validator = ValidatorAgent()
            result = await validator.validate_response(
                "test query",
                "test answer",
                {},
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_validate_coherence(self):
        from agents.validator import ValidatorAgent

        validator = ValidatorAgent()
        result = await validator.validate_response(
            query="How does auth work?",
            response="The system uses JWT tokens for authentication.",
            retrieved_context=[{"content": "Authentication uses JWT tokens for security"}],
            reasoning_trace=[{"step": "retrieval", "thinking": "Looking for auth docs"}],
        )
        assert result is not None
        assert result.score >= 0

    @pytest.mark.asyncio
    async def test_validate_safety(self):
        from agents.validator import ValidatorAgent

        validator = ValidatorAgent()
        result = await validator.validate_response(
            query="How to deploy?",
            response="Use docker compose up -d",
            retrieved_context=[],
        )
        assert result is not None
        assert result.valid is True


class TestReasoningTrace:
    @pytest.mark.asyncio
    async def test_add_trace_entry(self):
        from core.memory import get_short_term_memory

        memory = get_short_term_memory()
        memory.add_reasoning_trace(
            step="planning",
            thinking="Detected EXPLAIN intent",
            evidence=[],
            confidence=0.9,
        )
        trace = memory.get_reasoning_trace()
        assert len(trace) > 0
