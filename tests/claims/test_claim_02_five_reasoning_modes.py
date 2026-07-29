"""
README claim: "Reasoner -- Direct, chain-of-thought, tree-of-thoughts, reflection, and critique modes"
Source: README.md line 93

Tests the REAL reasoning engine at agents/reasoning.py — not the dead retrieval/reasoning.py.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agents.reasoning import ReasonMode, ReasoningAgent


@pytest.mark.claim
@pytest.mark.parametrize("mode", ["DIRECT", "CHAIN_OF_THOUGHT", "TREE_OF_THOUGHTS", "REFLECT", "CRITIQUE"])
def test_reasoning_mode_exists(mode):
    assert hasattr(ReasonMode, mode), f"ReasonMode.{mode} does not exist"


@pytest.mark.claim
@pytest.mark.asyncio
async def test_reasoning_uses_llm_not_string_concat():
    mock_router = MagicMock()
    mock_router.chat = AsyncMock(return_value=MagicMock(
        choices=[{"message": {"content": "LLM-generated answer"}}],
    ))

    with patch("agents.reasoning.get_router", return_value=mock_router):
        agent = ReasoningAgent(mode=ReasonMode.CHAIN_OF_THOUGHT)

    retrieved_data = {
        "results": [
            {"source": "docs", "results": [
                {"content": "Fact 1: JWT tokens are used"},
                {"content": "Fact 2: OAuth 2.0 is supported"},
            ]},
        ],
    }

    result = await agent.generate_answer(
        query="How does auth work?",
        retrieved_data=retrieved_data,
        intent="explain",
    )

    assert mock_router.chat.called, "LLM router was not called -- reasoning is using string concatenation"
    assert "LLM-generated answer" in result.answer, (
        f"Answer should come from LLM, got: {result.answer}"
    )


@pytest.mark.claim
@pytest.mark.asyncio
async def test_tree_of_thoughts_makes_multiple_llm_calls():
    mock_router = MagicMock()
    mock_router.chat = AsyncMock(return_value=MagicMock(
        choices=[{"message": {"content": "Answer from branch"}}],
    ))

    with patch("agents.reasoning.get_router", return_value=mock_router):
        agent = ReasoningAgent(mode=ReasonMode.TREE_OF_THOUGHTS)

    retrieved_data = {
        "results": [
            {"source": "docs", "results": [{"content": "Fact 1"}]},
        ],
    }

    await agent.generate_answer(
        query="test query",
        retrieved_data=retrieved_data,
        intent="explain",
    )

    # ToT: 3 parallel perspective calls + 1 synthesis call = 4 total calls
    assert mock_router.chat.call_count >= 3, (
        f"ToT made only {mock_router.chat.call_count} call(s) -- should make 4 (3 perspectives + 1 synthesis)"
    )
