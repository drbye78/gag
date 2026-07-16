"""
README claim: "it doesn\'t just search; it plans, retrieves from multiple sources,
reasons with a knowledge graph, and validates its own answers"
Source: README.md line 14
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.claim
@pytest.mark.asyncio
async def test_orchestration_response_includes_validation():
    """The orchestration engine must include validation in its response."""
    from agents.orchestration import OrchestrationEngine

    engine = OrchestrationEngine()

    with patch.object(engine.retriever, "retrieve_single", new=AsyncMock(
        return_value={"source": "docs", "results": [{"content": "Auth uses JWT", "score": 0.9}], "total": 1}
    )):
        with patch.object(engine.reasoner, "generate_answer", new=AsyncMock(
            return_value="Authentication uses JWT tokens."
        )):
            response = await engine.execute("How does auth work?")

    assert "answer" in response, "Response must include an answer"
    assert "validation" in response, "Response must include validation result -- ValidatorAgent is not wired in"
    assert response.get("validation", {}).get("valid") in [True, False], "Validation must have a valid flag"
    assert "confidence" in response.get("validation", {}), "Validation must include confidence"
    assert "issues" in response.get("validation", {}), "Validation must include issues list"


@pytest.mark.claim
def test_validator_agent_is_registered():
    """ValidatorAgent must be in the AgentType enum."""
    from agents.types import AgentType
    assert hasattr(AgentType, "VALIDATOR"), "AgentType.VALIDATOR does not exist -- validator is disconnected"


@pytest.mark.claim
def test_orchestration_has_validate_executor():
    """The orchestration engine must have a validate step executor."""
    from agents.orchestration import OrchestrationEngine
    engine = OrchestrationEngine()
    assert "validate" in engine._executors, "No 'validate' executor in orchestration engine"
