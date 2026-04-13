"""
Result Fusion - Combines results from multiple retrieval sources.

Implements Reciprocal Rank Fusion (RRF), score-based fusion,
and learning-to-rank fusion for hybrid retrieval.

Uses a template method pattern to eliminate duplicated
metadata collection, sorting, and result assembly code.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from enum import Enum


class FusionMethod(str, Enum):
    RRF = "rrf"
    SCORE_NORMALIZED = "score_normalized"
    WEIGHTED = "weighted"
    COMBINED = "combined"


class ResultFusion:
    def __init__(
        self,
        method: FusionMethod = FusionMethod.RRF,
        rrf_k: int = 60,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.method = method
        self.rrf_k = rrf_k
        self.weights = weights or {
            "graph": 0.4,
            "code": 0.3,
            "docs": 0.3,
        }

    def fuse(
        self,
        source_results: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        if self.method == FusionMethod.RRF:
            return self._rrf_fusion(source_results)
        elif self.method == FusionMethod.SCORE_NORMALIZED:
            return self._score_normalized_fusion(source_results)
        elif self.method == FusionMethod.WEIGHTED:
            return self._weighted_fusion(source_results)
        else:
            return self._combined_fusion(source_results)

    # ------------------------------------------------------------------
    # Template method — handles all common boilerplate
    # ------------------------------------------------------------------

    def _fuse_template(
        self,
        source_results: Dict[str, List[Dict[str, Any]]],
        score_fn: Callable[[Dict[str, Any], str, int, int], Tuple[float, float]],
    ) -> List[Dict[str, Any]]:
        """Template for all fusion methods.

        Args:
            source_results: dict of source_name → list of result dicts
            score_fn: callable(result, source, rank, rrf_k) → (fused_score, raw_score)

        Returns:
            sorted list of fused result dicts
        """
        fused_scores: Dict[str, float] = {}
        result_metadata: Dict[str, Dict[str, Any]] = {}

        for source, results in source_results.items():
            if not results:
                continue

            for rank, result in enumerate(results, 1):
                key = self._get_result_key(result, source)
                fused_score, raw_score = score_fn(result, source, rank, self.rrf_k)

                weight = self.weights.get(source, 1.0)
                fused_scores[key] = fused_scores.get(key, 0.0) + (fused_score * weight)

                if key not in result_metadata:
                    result_metadata[key] = {
                        "content": result.get("content", ""),
                        "source": source,
                        "original_score": raw_score,
                        "rank": rank,
                    }

        sorted_keys = sorted(
            fused_scores.keys(), key=lambda k: fused_scores[k], reverse=True
        )

        fused = []
        for key in sorted_keys:
            metadata = result_metadata[key]
            fused.append(
                {
                    "content": metadata["content"],
                    "source": metadata["source"],
                    "score": fused_scores[key],
                    "original_score": metadata["original_score"],
                    "rank": metadata.get("rank", 0),
                    "fused": True,
                }
            )

        return fused

    # ------------------------------------------------------------------
    # Concrete fusion methods — each passes a unique scoring lambda
    # ------------------------------------------------------------------

    def _rrf_fusion(
        self,
        source_results: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        return self._fuse_template(
            source_results,
            lambda _result, _source, rank, k: (1.0 / (k + rank), 0.0),
        )

    def _score_normalized_fusion(
        self,
        source_results: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        # Pre-compute normalization ranges per source
        ranges: Dict[str, Tuple[float, float]] = {}
        for source, results in source_results.items():
            if results:
                scores = [r.get("score", 0) for r in results]
                min_s = min(scores)
                max_s = max(scores)
                ranges[source] = (min_s, max(max_s - min_s, 1e-9))
            else:
                ranges[source] = (0.0, 1.0)

        def score_fn(result: Dict, source: str, rank: int, k: int) -> Tuple[float, float]:
            raw_score = result.get("score", 0)
            min_s, range_s = ranges.get(source, (0.0, 1.0))
            normalized = (raw_score - min_s) / range_s
            return normalized, raw_score

        return self._fuse_template(source_results, score_fn)

    def _weighted_fusion(
        self,
        source_results: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        def score_fn(result: Dict, source: str, rank: int, k: int) -> Tuple[float, float]:
            raw_score = result.get("score", 0)
            return raw_score, raw_score

        return self._fuse_template(source_results, score_fn)

    def _combined_fusion(
        self,
        source_results: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        # Run RRF and score-normalized independently, then merge
        rrf_results = self._rrf_fusion(source_results)
        score_results = self._score_normalized_fusion(source_results)

        combined_scores: Dict[str, float] = {}
        result_metadata: Dict[str, Dict[str, Any]] = {}

        for result in rrf_results:
            key = self._get_result_key(result, result.get("source", ""))
            combined_scores[key] = combined_scores.get(key, 0.0) + result.get("score", 0)
            if key not in result_metadata:
                result_metadata[key] = {
                    "content": result.get("content", ""),
                    "source": result.get("source", ""),
                }

        for result in score_results:
            key = self._get_result_key(result, result.get("source", ""))
            combined_scores[key] = combined_scores.get(key, 0.0) + result.get("score", 0)
            if key not in result_metadata:
                result_metadata[key] = {
                    "content": result.get("content", ""),
                    "source": result.get("source", ""),
                }

        sorted_keys = sorted(
            combined_scores.keys(), key=lambda k: combined_scores[k], reverse=True
        )

        fused = []
        for key in sorted_keys:
            metadata = result_metadata[key]
            fused.append(
                {
                    "content": metadata["content"],
                    "source": metadata["source"],
                    "score": combined_scores[key],
                    "fused": True,
                }
            )

        return fused

    def _get_result_key(self, result: Dict[str, Any], source: str) -> str:
        content = result.get("content", "")
        doc_id = result.get("id", result.get("source_id", ""))
        return f"{source}:{doc_id}:{hash(content[:100])}"


_fusion: Optional[ResultFusion] = None


def get_result_fusion(
    method: FusionMethod = FusionMethod.RRF,
    weights: Optional[Dict[str, float]] = None,
) -> ResultFusion:
    global _fusion
    if _fusion is None or _fusion.method != method:
        _fusion = ResultFusion(method=method, weights=weights)
    return _fusion
