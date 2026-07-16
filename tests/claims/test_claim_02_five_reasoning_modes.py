"""
README claim: "Reasoner -- Direct, chain-of-thought, tree-of-thoughts, reflection, and critique modes"
Source: README.md line 93
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.claim
@pytest.mark.parametrize("mode", ["DIRECT", "CHAIN_OF_THOUGHTS", "TREE_OF_THOUGHTS", "REFLECT", "CRITIQUE"])
def test_reasoning_mode_exists(mode):
    from retrieval.reasoning import ReasoningMode
    assert hasattr(ReasoningMode, mode), f"ReasoningMode.{mode} does not exist"


@pytest.mark.claim
@pytest.mark.asyncio
async def test_reasoning_uses_llm_not_string_concat():
    from retrieval.reasoning import ReasoningEngine, ReasoningMode

    llm_router = MagicMock()
    llm_router.chat = AsyncMock(return_value=MagicMock(
        text="LLM-generated answer",
        choices=[{"message": {"content": "LLM-generated answer"}}],
    ))

    engine = ReasoningEngine(mode=ReasoningMode.CHAIN_OF_THOUGHTS)
    engine._llm_router = llm_router
    engine._llm_available = True

    facts = [
        {"content": "Fact 1: JWT tokens are used", "score": 0.9, "source": "docs"},
        {"content": "Fact 2: OAuth 2.0 is supported", "score": 0.85, "source": "docs"},
    ]

    result = await engine.reason("How does auth work?", facts)

    assert llm_router.chat.called, "LLM router was not called -- reasoning is using string concatenation"
    assert "LLM-generated answer" in result.get("answer", ""), "Answer should come from LLM, not string concat"


@pytest.mark.claim
@pytest.mark.asyncio
async def test_tree_of_thoughts_makes_multiple_llm_calls():
    from retrieval.reasoning import ReasoningEngine, ReasoningMode

    llm_router = MagicMock()
    llm_router.chat = AsyncMock(return_value=MagicMock(
        text="Answer from branch",
        choices=[{"message": {"content": "Answer from branch"}}],
    ))

    engine = ReasoningEngine(mode=ReasoningMode.TREE_OF_THOUGHTS)
    engine._llm_router = llm_router
    engine._llm_available = True

    facts = [{"content": "Fact 1", "score": 0.9, "source": "docs"}]
    await engine.reason("test query", facts)

    assert llm_router.chat.call_count >= 2, f"ToT made only {llm_router.chat.call_count} call(s) -- should make multiple"
