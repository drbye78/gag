from typing import Any, Optional
from pydantic import BaseModel
from models.ir import IRFeature
from core.patterns.schema import (
    Pattern,
    PatternCondition,
    PatternMatchResult,
    PatternLibrary,
    get_pattern_library,
)


class ConstraintViolation(BaseModel):
    constraint_id: str
    actual_value: Any
    expected_value: Any
    severity: str
    message: str
    fix_hint: str


class PatternMatcher:
    def __init__(self, library: Optional[PatternLibrary] = None):
        self.library = library or get_pattern_library()
    
    def match(self, features: IRFeature) -> list[PatternMatchResult]:
        candidates = self._get_candidates(features)
        
        results = []
        for pattern in candidates:
            match_result = self._evaluate_pattern(pattern, features)
            if match_result.match_score > 0.3:
                results.append(match_result)
        
        return sorted(results, key=lambda r: r.match_score, reverse=True)
    
    def _get_candidates(self, features: IRFeature) -> list[Pattern]:
        candidates = set()
        feature_dict = features.model_dump()
        feature_str = str(feature_dict).lower()
        
        for trigger, pattern_ids in self.library._index_by_trigger.items():
            if trigger.lower() in feature_str:
                candidates.update(pattern_ids)
        
        if not candidates:
            return self.library.all()[:5]
        
        return [self.library._patterns[pid] for pid in candidates if pid in self.library._patterns]
    
    def _evaluate_pattern(self, pattern: Pattern, features: IRFeature) -> PatternMatchResult:
        matched = []
        unmatched = []
        total_score = 0.0
        
        feature_dict = features.model_dump()
        
        for condition in pattern.conditions:
            score = self._evaluate_condition(condition, feature_dict)
            if score > 0:
                matched.append(condition.feature)
                total_score += score
            else:
                unmatched.append(condition.feature)
        
        boost = pattern.priority / 10.0
        final_score = min(1.0, total_score + boost)
        
        return PatternMatchResult(
            pattern=pattern,
            match_score=final_score,
            matched_conditions=matched,
            unmatched_conditions=unmatched,
            confidence_boost=boost,
        )
    
    def _evaluate_condition(self, condition: PatternCondition, features: dict) -> float:
        actual = features.get(condition.feature)
        
        if actual is None:
            return 0.0
        
        op = condition.operator
        expected = condition.value
        
        if op == "eq":
            return 1.0 if actual == expected else 0.0
        elif op == "ne":
            return 0.0 if actual == expected else 1.0
        elif op == "gt":
            return 1.0 if actual > expected else 0.0
        elif op == "lt":
            return 1.0 if actual < expected else 0.0
        elif op == "in":
            return 1.0 if actual in expected else 0.0
        elif op == "contains":
            return 1.0 if expected in str(actual) else 0.0
        
        return 0.0


class PatternScorer:
    def score(self, match: PatternMatchResult, constraints: list["ConstraintViolation"] = None) -> float:
        base = match.match_score
        boost = match.pattern.priority / 10.0
        
        penalty = 0.0
        if constraints:
            hard_violations = [c for c in constraints if c.severity == "error"]
            penalty = len(hard_violations) * 0.15
        
        return max(0.0, min(1.0, base + boost - penalty))