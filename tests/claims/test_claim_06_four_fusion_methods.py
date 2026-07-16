"""
README claim: "4 fusion methods: RRF, Score-normalized, Weighted, Combined"
Source: README.md line 84
"""
import pytest


@pytest.mark.claim
@pytest.mark.parametrize("method", ["RRF", "SCORE_NORMALIZED", "WEIGHTED", "COMBINED"])
def test_fusion_method_exists(method):
    from retrieval.fusion import FusionMethod
    assert hasattr(FusionMethod, method), f"FusionMethod.{method} does not exist"


@pytest.mark.claim
@pytest.mark.parametrize("method", ["RRF", "SCORE_NORMALIZED", "WEIGHTED", "COMBINED"])
def test_fusion_produces_sorted_results(method, seeded_retrieval_results):
    from retrieval.fusion import ResultFusion, FusionMethod
    fusion = ResultFusion(method=FusionMethod[method])
    fused = fusion.fuse(seeded_retrieval_results)
    assert isinstance(fused, list), "Fusion must return a list"
    assert len(fused) > 0, "Fusion must produce non-empty results from non-empty input"
    scores = [r.get("score", 0) for r in fused]
    assert scores == sorted(scores, reverse=True), "Fusion results must be sorted by score descending"


@pytest.mark.claim
def test_fusion_key_is_deterministic(seeded_retrieval_results):
    from retrieval.fusion import ResultFusion, FusionMethod
    fusion = ResultFusion(method=FusionMethod.RRF)
    fused1 = fusion.fuse(seeded_retrieval_results)
    fused2 = fusion.fuse(seeded_retrieval_results)
    keys1 = [f.get("content", "")[:50] for f in fused1]
    keys2 = [f.get("content", "")[:50] for f in fused2]
    assert keys1 == keys2, "Fusion ordering must be deterministic across runs"
