"""
README claim: "11 sources: Docs, Code, Graph, Code Graph, Tickets, Telemetry, Diagram,
UI Sketch, ColBERT, Knowledge Graph, Multimodal"
Source: README.md line 79
"""
import pytest


@pytest.mark.claim
def test_eleven_retrieval_sources_exist():
    from models.retrieval import RetrievalSource
    sources = [s for s in RetrievalSource]
    assert len(sources) == 11, f"Expected 11 retrieval sources, got {len(sources)}: {[s.value for s in sources]}"


@pytest.mark.claim
@pytest.mark.parametrize("source_name", [
    "DOCS", "CODE", "GRAPH", "CODE_GRAPH", "TICKETS", "TELEMETRY",
    "DIAGRAM", "UI_SKETCH", "COLBERT", "KNOWLEDGE", "MULTIMODAL"
])
def test_specific_retrieval_source_exists(source_name):
    from models.retrieval import RetrievalSource
    assert hasattr(RetrievalSource, source_name), f"RetrievalSource.{source_name} does not exist"


@pytest.mark.claim
@pytest.mark.asyncio
async def test_orchestrator_handles_all_sources():
    from retrieval.orchestrator import RetrievalOrchestrator
    orchestrator = RetrievalOrchestrator()
    expected_methods = [
        "_retrieve_docs", "_retrieve_code", "_retrieve_graph", "_retrieve_code_graph",
        "_retrieve_tickets", "_retrieve_telemetry", "_retrieve_diagram", "_retrieve_ui",
        "_retrieve_colbert", "_retrieve_knowledge",
    ]
    for method_name in expected_methods:
        assert hasattr(orchestrator, method_name), f"Orchestrator missing method: {method_name}"
