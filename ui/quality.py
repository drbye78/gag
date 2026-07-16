from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class VisualEmbedding:
    embeddings: Any
    model: str = "colpali"
    dimensions: int = 768


@dataclass
class QualityMetrics:
    overall_score: float
    extraction_confidence: float = 0.0
    element_quality: float = 0.0
    layout_quality: float = 0.0
    pattern_quality: float = 0.0
    indexing_quality: float = 0.0
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def calculate(
        extraction_confidence: float,
        element_count: int,
        indexing_success: bool,
        pattern_matches: List[str],
    ) -> "QualityMetrics":
        scores = []

        extraction_score = extraction_confidence
        scores.append(extraction_score)

        if element_count > 0:
            element_quality = min(1.0, element_count / 30)
        else:
            element_quality = 0.0
        scores.append(element_quality * 0.8)

        layout_quality = min(1.0, element_count / 50)
        scores.append(layout_quality * 0.5)

        if pattern_matches:
            pattern_quality = min(1.0, len(pattern_matches) / 5)
        else:
            pattern_quality = 0.3
        scores.append(pattern_quality * 0.2)

        if indexing_success:
            indexing_quality = 1.0
        else:
            indexing_quality = 0.0
        scores.append(indexing_quality * 0.3)

        overall = sum(scores) / len(scores) if scores else 0.0

        warnings = []
        if extraction_confidence < 0.5:
            warnings.append("Low extraction confidence")
        if element_count == 0:
            warnings.append("No elements detected")
        if element_count > 100:
            warnings.append("Excessive elements - may affect quality")

        return QualityMetrics(
            overall_score=overall,
            extraction_confidence=extraction_confidence,
            element_quality=element_quality,
            layout_quality=layout_quality,
            pattern_quality=pattern_quality,
            indexing_quality=indexing_quality,
            warnings=warnings,
            details={"element_count": element_count, "pattern_count": len(pattern_matches)},
        )


def calculate_quality_score(
    extraction_confidence: float,
    element_count: int,
    indexing_success: bool,
    pattern_matches: List[str],
) -> float:
    metrics = QualityMetrics.calculate(
        extraction_confidence=extraction_confidence,
        element_count=element_count,
        indexing_success=indexing_success,
        pattern_matches=pattern_matches,
    )
    return metrics.overall_score