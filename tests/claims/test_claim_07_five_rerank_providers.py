"""
README claim: "5 rerank providers: Cohere, BGE, SentenceTransformers, Jina, LlamaIndex"
Source: README.md line 85
"""
import pytest


@pytest.mark.claim
@pytest.mark.parametrize("provider", ["COHERE", "BGE", "SENTENCE_TRANSFORMER", "JINA", "LLAMA_INDEX"])
def test_rerank_provider_exists(provider):
    from retrieval.rerank.base import RerankProvider
    assert hasattr(RerankProvider, provider), f"RerankProvider.{provider} does not exist"


@pytest.mark.claim
def test_rerank_provider_classes_exist():
    from retrieval.rerank import providers
    assert hasattr(providers, "CohereReranker"), "CohereReranker class missing"
    assert hasattr(providers, "BGEReranker"), "BGEReranker class missing"
    assert hasattr(providers, "SentenceTransformerReranker"), "SentenceTransformerReranker class missing"
    assert hasattr(providers, "JinaReranker"), "JinaReranker class missing"
    assert hasattr(providers, "LlamaIndexReranker"), "LlamaIndexReranker class missing"
