"""Evidence aggregator for UI sketch understanding.

Merges VLM extraction schema, ColPali embedding, and OCR text
into a unified UIExtractionResult with confidence scoring.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from .models import UIElement, UIExtractionResult, UILayout, UISketch, UserAction
from .vlm_extractor import UIExtractionSchema


class EvidenceAggregator:
    """Aggregates multiple evidence sources into a single extraction result."""

    def aggregate(
        self,
        image_url: str,
        vlm_schema: UIExtractionSchema,
        visual_embedding: Optional[List[float]] = None,
        ocr_text: Optional[str] = None,
    ) -> UIExtractionResult:
        """Merge VLM schema, embedding, and OCR into extraction result."""
        # 1. Create UISketch from vlm_schema
        sketch = UISketch(
            sketch_id=str(uuid.uuid4()),
            title=vlm_schema.page_type or "unknown",
            source_url=image_url,
            format_type=vlm_schema.source_type,
            ingestion_timestamp=datetime.now(),
            page_type=vlm_schema.page_type,
        )

        # 2. Create UILayout from vlm_schema.layout
        layout = UILayout(
            layout_id=str(uuid.uuid4()),
            layout_type=vlm_schema.layout.type,
            hierarchy=[region.name for region in vlm_schema.layout.regions],
        )

        # 3. Create UIElement list from vlm_schema.elements
        elements = [
            UIElement(
                element_id=elem.id,
                element_type=elem.type,
                label=elem.label,
                position=elem.position,
                attributes=elem.attributes,
                interactions=elem.interactions,
                confidence=elem.confidence,
            )
            for elem in vlm_schema.elements
        ]

        # 4. Create UserAction list from vlm_schema.user_actions
        actions = [
            UserAction(
                action_id=str(uuid.uuid4()),
                trigger=action.trigger,
                expected_result=action.expected_result,
            )
            for action in vlm_schema.user_actions
        ]

        # 5. Calculate average confidence across elements
        if elements:
            avg_confidence = sum(e.confidence for e in elements) / len(elements)
        else:
            avg_confidence = 0.0

        # 6. Set source_type_confidence to average confidence
        source_type_confidence = avg_confidence

        # 7. Add metadata
        metadata = {
            "element_count": len(elements),
            "average_confidence": avg_confidence,
        }
        if avg_confidence < 0.6:
            metadata["low_confidence_warning"] = True

        return UIExtractionResult(
            sketch=sketch,
            layout=layout,
            elements=elements,
            actions=actions,
            visual_embedding=visual_embedding,
            ocr_text=ocr_text,
            source_type_confidence=source_type_confidence,
            extraction_metadata=metadata,
        )
