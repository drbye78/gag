"""
README claim: "ColBERT support: Late interaction embeddings for enhanced semantic search"
Source: README.md line 87
"""
import pytest


@pytest.mark.claim
def test_colbert_retriever_class_exists():
    from retrieval.colbert import ColBERTRetriever
    assert ColBERTRetriever is not None


@pytest.mark.claim
def test_colbert_config_exists():
    from core.config import get_settings
    settings = get_settings()
    assert hasattr(settings, "colbert_enabled"), "colbert_enabled setting missing"
    assert hasattr(settings, "colbert_model_name"), "colbert_model_name setting missing"
    assert hasattr(settings, "colbert_top_k"), "colbert_top_k setting missing"


@pytest.mark.claim
@pytest.mark.asyncio
async def test_colbert_search_returns_results():
    from retrieval.colbert import get_colbert_search_client
    client = get_colbert_search_client()
    if client is None:
        pytest.skip("ColBERT not enabled -- README should mark as optional")
    result = await client.search("test query", limit=5)
    assert "results" in result, "ColBERT search must return results key"
