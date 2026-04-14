"""Tests for evidence aggregator."""

import pytest

from ui.models import UILayout, UISketch
from ui.vlm_extractor import (
    LayoutSchema,
    UIElementSchema,
    UIExtractionSchema,
    UserActionSchema,
)


def make_schema(
    source_type="sketch",
    page_type="list-report",
    layout_type="two-column",
    regions=None,
    elements=None,
    user_actions=None,
):
    """Helper to build a UIExtractionSchema with sensible defaults."""
    if regions is None:
        regions = []
    if elements is None:
        elements = []
    if user_actions is None:
        user_actions = []
    return UIExtractionSchema(
        source_type=source_type,
        page_type=page_type,
        layout=LayoutSchema(type=layout_type, regions=regions),
        elements=elements,
        user_actions=user_actions,
    )


class TestEvidenceAggregator:
    IMAGE_URL = "https://example.com/sketch.png"

    @pytest.fixture
    def aggregator(self):
        from ui.evidence_aggregator import EvidenceAggregator
        return EvidenceAggregator()

    def test_aggregate_vlm_only(self, aggregator):
        """aggregate with only VLM data produces correct sketch, layout, elements."""
        schema = make_schema(
            source_type="wireframe",
            page_type="object-page",
            layout_type="header-content-footer",
            elements=[
                UIElementSchema(
                    id="e1",
                    type="form",
                    label="Customer Info",
                    position={"x": 0, "y": 0, "width": 300, "height": 200},
                    confidence=0.88,
                ),
                UIElementSchema(
                    id="e2",
                    type="button",
                    label="Submit",
                    confidence=0.95,
                ),
            ],
            user_actions=[
                UserActionSchema(trigger="click Submit", expected_result="form-submitted"),
            ],
        )

        result = aggregator.aggregate(self.IMAGE_URL, schema)

        # Sketch
        assert isinstance(result.sketch, UISketch)
        assert result.sketch.title == "object-page"
        assert result.sketch.format_type == "wireframe"
        assert result.sketch.source_url == self.IMAGE_URL
        assert result.sketch.page_type == "object-page"

        # Layout
        assert isinstance(result.layout, UILayout)
        assert result.layout.layout_type == "header-content-footer"

        # Elements
        assert len(result.elements) == 2
        assert result.elements[0].element_id == "e1"
        assert result.elements[0].element_type == "form"
        assert result.elements[0].confidence == 0.88

        # Actions
        assert len(result.actions) == 1
        assert result.actions[0].trigger == "click Submit"

        # No embedding or OCR
        assert result.visual_embedding is None
        assert result.ocr_text is None

    def test_aggregate_with_visual_embedding(self, aggregator):
        """aggregate with visual_embedding includes embedding in result."""
        schema = make_schema(
            elements=[
                UIElementSchema(id="e1", type="table", label="Orders", confidence=0.9),
            ],
        )
        embedding = [0.1, 0.2, 0.3, 0.4]

        result = aggregator.aggregate(self.IMAGE_URL, schema, visual_embedding=embedding)

        assert result.visual_embedding == embedding

    def test_aggregate_with_ocr_text(self, aggregator):
        """aggregate with ocr_text includes ocr_text in result."""
        schema = make_schema(
            elements=[
                UIElementSchema(id="e1", type="button", label="Save", confidence=0.8),
            ],
        )
        ocr = "Customer Orders\nSave\nCancel"

        result = aggregator.aggregate(self.IMAGE_URL, schema, ocr_text=ocr)

        assert result.ocr_text == ocr

    def test_low_average_confidence_warning(self, aggregator):
        """low average confidence (< 0.6) sets low_confidence_warning in metadata."""
        schema = make_schema(
            elements=[
                UIElementSchema(id="e1", type="table", confidence=0.4),
                UIElementSchema(id="e2", type="button", confidence=0.5),
            ],
        )

        result = aggregator.aggregate(self.IMAGE_URL, schema)

        # Average = (0.4 + 0.5) / 2 = 0.45
        assert result.extraction_metadata["average_confidence"] == 0.45
        assert result.extraction_metadata["low_confidence_warning"] is True
        assert result.source_type_confidence == 0.45

    def test_empty_elements_no_crash(self, aggregator):
        """empty elements produces empty list, no crash."""
        schema = make_schema()

        result = aggregator.aggregate(self.IMAGE_URL, schema)

        assert result.elements == []
        assert result.extraction_metadata["element_count"] == 0
        assert result.extraction_metadata["average_confidence"] == 0.0
        assert result.source_type_confidence == 0.0
        assert "low_confidence_warning" in result.extraction_metadata
        assert result.extraction_metadata["low_confidence_warning"] is True
