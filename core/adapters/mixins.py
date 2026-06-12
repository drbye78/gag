"""Shared mixins for platform adapters."""

from typing import Any, Dict, List


class RecommendationMixin:
    """Shared recommendation building logic for all adapters.

    All mutable state is initialized per-instance in __init__ to avoid
    accidental sharing across adapter instances.
    """

    def __init__(self) -> None:
        self._recommendation_cache: Dict[str, Any] = {}
        self._explanation_cache: Dict[str, str] = {}

    def _build_recommendations(
        self, pattern_results: List[Any], features: Any, violations: List[Any]
    ) -> List[Dict[str, Any]]:
        recommendations = []

        for pattern_result in pattern_results[:3]:
            pattern = getattr(pattern_result, "pattern", None)
            if pattern:
                recommendations.append(
                    {
                        "name": pattern.name,
                        "reason": f"Matched {len(pattern_result.matched_conditions)} conditions",
                        "score": pattern_result.match_score,
                        "pattern_id": pattern.id,
                    }
                )

        for violation in violations:
            recommendations.append(
                {
                    "name": "Fix Required",
                    "reason": violation.message,
                    "severity": violation.severity,
                    "fix": violation.fix_hint,
                }
            )

        return recommendations

    def _explain(self, recommendations: List[Dict[str, Any]], violations: List[Any]) -> str:
        parts = []

        if recommendations:
            best = recommendations[0]
            parts.append(f"Recommended: {best.get('name', 'Unknown')}")

        if violations:
            errors = [v for v in violations if v.severity == "error"]
            if errors:
                parts.append(f"Blocking issues: {len(errors)}")

        return " | ".join(parts) if parts else "Analysis complete"
