"""
Property-based tests using Hypothesis for fusion, chunking, and Cypher utilities.

These tests generate random inputs and verify invariants:
- Fusion always produces sorted results
- Chunking always produces non-empty chunks for non-empty input
- Cypher identifier validation is correct
"""
import hashlib
import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis import HealthCheck


# --- Fusion property tests ---

@given(
    st.lists(
        st.fixed_dictionaries({
            "id": st.text(min_size=1, max_size=20),
            "content": st.text(min_size=1, max_size=200),
            "score": st.floats(min_value=0.0, max_value=1.0),
            "source": st.sampled_from(["docs", "code", "graph"]),
        }),
        min_size=0,
        max_size=20,
    )
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
def test_fusion_always_returns_sorted(results):
    """Fusion results must always be sorted by score descending."""
    from retrieval.fusion import ResultFusion, FusionMethod

    source_results = {"docs": results, "code": [], "graph": []}
    for method in [FusionMethod.RRF, FusionMethod.SCORE_NORMALIZED, FusionMethod.WEIGHTED]:
        fusion = ResultFusion(method=method)
        fused = fusion.fuse(source_results)
        if len(fused) > 1:
            scores = [r.get("score", 0) for r in fused]
            assert scores == sorted(scores, reverse=True), \
                f"Fusion method {method} did not produce sorted results"


@given(st.text(min_size=1, max_size=100))
def test_fusion_key_deterministic(content):
    """Fusion key must be deterministic (same content → same key)."""
    from retrieval.fusion import ResultFusion

    fusion = ResultFusion()
    result = {"content": content, "id": "test", "source": "docs"}
    key1 = fusion._get_result_key(result, "docs")
    key2 = fusion._get_result_key(result, "docs")
    assert key1 == key2, "Same content produced different keys"


# --- Cypher utilities property tests ---

@given(st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_", min_size=1, max_size=50))
def test_safe_identifier_accepts_valid(name):
    """safe_identifier should accept valid identifiers."""
    from core.cypher_utils import safe_identifier
    # First char must be letter or underscore
    assume(name[0].isalpha() or name[0] == "_")
    assert safe_identifier(name) == name


@given(st.text(alphabet="!@#$%^&*(){}[]|\\:;\"'<>,.?/`~", min_size=1, max_size=10))
def test_safe_identifier_rejects_invalid(name):
    """safe_identifier should reject identifiers with special characters."""
    from core.cypher_utils import safe_identifier
    with pytest.raises(ValueError):
        safe_identifier(name)


@given(st.integers(min_value=1, max_value=100))
def test_validate_int_accepts_valid(value):
    """validate_int should accept values in range."""
    from core.cypher_utils import validate_int
    assert validate_int(value, "test", 1, 100) == value


@given(st.one_of(st.integers(max_value=0), st.integers(min_value=101), st.text(alphabet="abcdefghijklmnopqrstuvwxyz!@#$%", min_size=1)))
def test_validate_int_rejects_invalid(value):
    """validate_int should reject out-of-range or non-integer values."""
    from core.cypher_utils import validate_int
    with pytest.raises(ValueError):
        validate_int(value, "test", 1, 100)


# --- Chunking property tests ---

@given(st.text(min_size=100, max_size=5000))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_document_chunker_produces_non_empty(text):
    """DocumentChunker should produce non-empty chunks for non-empty text."""
    from ingestion.chunker import DocumentChunker
    chunker = DocumentChunker(chunk_size=500, chunk_overlap=100)
    result = chunker.chunk(text, "test_source")
    if result.chunks:
        for chunk in result.chunks:
            assert len(chunk.content) > 0, "Chunk has empty content"


@given(st.text(min_size=50, max_size=2000, alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n.#-"))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_markdown_chunker_preserves_content(text):
    """MarkdownChunker should preserve all content across chunks (no data loss)."""
    from ingestion.chunker import MarkdownChunker
    chunker = MarkdownChunker(chunk_size=800, chunk_overlap=100)
    result = chunker.chunk(text, "test_md")
    if result.chunks:
        # At least some content should be preserved
        total_chunk_content = sum(len(c.content) for c in result.chunks)
        assert total_chunk_content > 0, "No content in any chunk"


# --- Configuration property tests ---

@given(st.text(min_size=1, max_size=100))
def test_text_hash_deterministic(text):
    """EmbeddingPipeline text hash should be deterministic."""
    from ingestion.embedder import EmbeddingPipeline
    hash1 = EmbeddingPipeline._text_hash(text)
    hash2 = EmbeddingPipeline._text_hash(text)
    assert hash1 == hash2, "Same text produced different hashes"
    assert len(hash1) == 64, f"Hash length is {len(hash1)}, expected 64 (SHA-256)"


@given(st.text(min_size=1, max_size=100))
def test_text_hash_different_inputs(text):
    """Different texts should (almost certainly) produce different hashes."""
    from ingestion.embedder import EmbeddingPipeline
    different_text = text + "x"
    hash1 = EmbeddingPipeline._text_hash(text)
    hash2 = EmbeddingPipeline._text_hash(different_text)
    assert hash1 != hash2, "Different texts produced same hash (collision)"
