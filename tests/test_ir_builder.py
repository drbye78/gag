"""Tests for IRBuilder, including UI graph integration."""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from multimodal.ir_builder import IRBuilder
from ui.models import UISketch, UIElement, UILayout, UIExtractionResult


class TestIRBuilderAddUI:
    def test_add_ui_returns_uiir(self):
        builder = IRBuilder()
        result = builder.add_ui("test content", title="Test UI")
        assert result is not None
        assert result.title == "Test UI"
        assert result.artifact_type.value == "ui"

    def test_add_ui_deduplicates(self):
        builder = IRBuilder()
        r1 = builder.add_ui("same content")
        r2 = builder.add_ui("same content")
        assert r2 is None

    def test_add_ui_with_extraction_result(self):
        """add_ui with extraction_result triggers graph build and populates fields."""
        sketch = UISketch(
            sketch_id="sk_test", title="Test", source_url="",
            format_type="screenshot", ingestion_timestamp=datetime.utcnow()
        )
        layout = UILayout(layout_id="l1", layout_type="single-column")
        elem = UIElement(element_id="e1", element_type="button", confidence=0.9)
        er = UIExtractionResult(sketch=sketch, layout=layout, elements=[elem])

        builder = IRBuilder()

        mock_matcher = MagicMock()
        mock_matcher.match_patterns.return_value = []

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = {"success": True}
            with patch("ui.graph_builder.UIGraphBuilder") as mock_builder_cls:
                mock_builder = MagicMock()
                mock_builder.build = MagicMock(return_value={"success": True})
                mock_builder_cls.return_value = mock_builder

                with patch("ui.pattern_matcher.get_pattern_matcher", return_value=mock_matcher):
                    result = builder.add_ui("test", extraction_result=er)

                    assert result is not None
                    assert result.graph_node_id == "sk_test"
                    assert result.element_count == 1
