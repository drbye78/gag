"""
README claim: "GraphRAG pipeline with entity extraction, relationship inference, community detection"
Source: README.md line 88 (GraphRAG pipeline)
"""
import pytest
import inspect


@pytest.mark.claim
def test_graphrag_pipeline_exists():
    from ingestion.graphrag.pipeline import GraphRAGPipeline
    assert GraphRAGPipeline is not None


@pytest.mark.claim
def test_graphrag_uses_llm_entity_extraction():
    from ingestion.graphrag.entity_extractor import get_entity_extractor
    extractor = get_entity_extractor(use_llm=True)
    assert extractor.__class__.__name__ == "DocumentEntityExtractor", \
        f"Expected DocumentEntityExtractor, got {extractor.__class__.__name__}"


@pytest.mark.claim
def test_community_detection_uses_louvain_or_leiden():
    from ingestion.graphrag.community_detector import CommunityDetector
    source = inspect.getsource(CommunityDetector._build_communities)
    has_louvain = "louvain" in source.lower() or "best_partition" in source.lower()
    has_leiden = "leiden" in source.lower()
    assert has_louvain or has_leiden, \
        "Community detection uses BFS connected components, not Louvain/Leiden"


@pytest.mark.claim
def test_relationship_inferrer_no_silent_cap():
    from ingestion.graphrag.relationship_inferrer import RelationshipInferrer
    source = inspect.getsource(RelationshipInferrer._create_entity_pairs)
    assert "[:50]" not in source, "Relationship inferrer silently caps at 50 pairs"
    assert "i + 1 : i + 10" not in source, "Relationship inferrer uses sliding window of 9, not all pairs"
