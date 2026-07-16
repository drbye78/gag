"""
README claim: "5 execution modes: Iterative, Parallel, Sequential, Branching, Recursive"
Source: README.md line 98
"""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.claim
@pytest.mark.parametrize("mode", ["ITERATIVE", "PARALLEL", "SEQUENTIAL", "BRANCHING", "RECURSIVE"])
def test_execution_mode_exists(mode):
    from agents.orchestration import OrchestrationMode
    assert hasattr(OrchestrationMode, mode), f"OrchestrationMode.{mode} does not exist"


@pytest.mark.claim
@pytest.mark.asyncio
async def test_execute_branching_works():
    from agents.orchestration import OrchestrationEngine

    engine = OrchestrationEngine()

    with patch.object(engine, "_execute_branch", new=AsyncMock(
        return_value={"answer": "branch result", "branch_id": 0}
    )):
        with patch.object(engine, "execute", new=AsyncMock(
            return_value={"answer": "merged result", "query": "test"}
        )):
            result = await engine.execute_branching("test query", branches=2)

    assert "answer" in result, "execute_branching must return an answer"
    assert "branch_results" in result, "execute_branching must return branch results"


@pytest.mark.claim
def test_execute_recursive_exists():
    from agents.orchestration import OrchestrationEngine
    engine = OrchestrationEngine()
    assert hasattr(engine, "execute_recursive"), "execute_recursive method does not exist"
    import inspect
    assert inspect.iscoroutinefunction(engine.execute_recursive), "execute_recursive must be async"
