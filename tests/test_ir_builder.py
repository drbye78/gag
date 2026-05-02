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
        from multimodal.ir_builder import IRBuilder
        builder = IRBuilder()
        result = builder.add_ui("test content", graph_node_id="test-123")
        assert result is not None