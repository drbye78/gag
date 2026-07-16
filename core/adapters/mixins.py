"""Shared mixins for platform adapters."""

from typing import Any, Dict, List


class RecommendationMixin:
    """Shared recommendation building logic for all adapters."""

    def _build_recommendations(
        self,
        pattern_results: List[Any],
        features: Any,
        violations: List[Any]
    ) -> List[Dict[str, Any]]:
        recommendations = []
        
        for pattern_result in pattern_results[:3]:
            pattern = getattr(pattern_result, "pattern", None)
            if pattern:
                recommendations.append({
                    "name": pattern.name,
                    "reason": f"Matched {len(pattern_result.matched_conditions)} conditions",
                    "score": pattern_result.match_score,
                })
        
        for violation in violations:
            recommendations.append({
                "name": "Fix Required",
                "reason": violation.message,
                "severity": violation.severity,
                "fix": violation.fix_hint,
            })
        
        return recommendations
    
    def _explain(
        self,
        recommendations: List[Dict[str, Any]],
        violations: List[Any]
    ) -> str:
        parts = []
        
        if recommendations:
            best = recommendations[0]
            parts.append(f"Recommended: {best.get('name', 'Unknown')}")
        
        if violations:
            errors = [v for v in violations if v.severity == "error"]
            if errors:
                parts.append(f"Blocking issues: {len(errors)}")
        
        return " | ".join(parts) if parts else "Analysis complete"
