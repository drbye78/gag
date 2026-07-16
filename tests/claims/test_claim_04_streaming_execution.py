"""
README claim: "Streaming execution with step-by-step progress yields"
Source: README.md line 100
"""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.claim
@pytest.mark.asyncio
async def test_streaming_yields_expected_events():
    from agents.orchestration import OrchestrationEngine

    engine = OrchestrationEngine()

    with patch.object(engine.retriever, "retrieve_single", new=AsyncMock(
        return_value={"source": "docs", "results": [{"content": "test", "score": 0.9}], "total": 1}
    )):
        with patch.object(engine.reasoner, "generate_answer", new=AsyncMock(
            return_value="test answer"
        )):
            events = []
            async for event in engine.execute_streaming("test query"):
                events.append(event)

    event_types = [e.get("type") for e in events]
    assert "start" in event_types, f"Missing 'start' event in: {event_types}"
    assert "complete" in event_types, f"Missing 'complete' event in: {event_types}"
    assert events[-1]["type"] == "complete", "Last event must be 'complete'"
    assert "answer" in events[-1], "Complete event must include answer"
