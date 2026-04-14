"""Tests for UISuggestionTool - UI sketch understanding MCP tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.base import ToolInput
from ui.suggestion_tool import UISuggestionTool


@pytest.fixture
def mock_retriever():
    retriever = MagicMock()
    retriever.find_similar_structural = AsyncMock(return_value=[
        {"b.sketch_id": "sk_003", "b.title": "Similar Dashboard", "overlap": 4},
        {"b.sketch_id": "sk_004", "b.title": "Form Page", "overlap": 2},
    ])
    return retriever


@pytest.fixture
def mock_catalog():
    catalog = MagicMock()
    mock_component = MagicMock()
    mock_component.name = "sap.m.Table"
    mock_component.library = "sap.m"
    mock_component.complexity = 2
    mock_component.properties = ["items", "columns", "growing", "mode", "fixedLayout", "busy"]
    catalog.find_for_element_type = MagicMock(return_value=[mock_component])
    return catalog


class TestValidateInput:
    def test_with_sketch_id_returns_true(self):
        tool = UISuggestionTool()
        assert tool.validate_input({"ui_sketch_id": "sk_001"}) is True

    def test_with_image_url_returns_true(self):
        tool = UISuggestionTool()
        assert tool.validate_input({"image_url": "https://example.com/sketch.png"}) is True

    def test_with_neither_returns_false(self):
        tool = UISuggestionTool()
        assert tool.validate_input({"detail_level": 2}) is False


class TestExecute:
    @pytest.mark.asyncio
    async def test_execute_with_sketch_id(self, mock_retriever, mock_catalog):
        with patch("ui.suggestion_tool.get_ui_retriever", return_value=mock_retriever), \
             patch("ui.suggestion_tool.get_sap_catalog", return_value=mock_catalog):
            tool = UISuggestionTool()
            result = await tool.execute(ToolInput(args={"ui_sketch_id": "sk_001"}))

        assert result.error is None
        assert result.result["sketch_id"] == "sk_001"
        assert result.result["image_url"] is None
        assert len(result.result["suggestions"]) == 2
        assert result.result["suggestions"][0]["type"] == "similar_uis"
        assert result.result["suggestions"][1]["type"] == "sap_components"
        mock_retriever.find_similar_structural.assert_called_once_with("sk_001", limit=3)

    @pytest.mark.asyncio
    async def test_execute_with_image_url(self, mock_retriever, mock_catalog):
        with patch("ui.suggestion_tool.get_ui_retriever", return_value=mock_retriever), \
             patch("ui.suggestion_tool.get_sap_catalog", return_value=mock_catalog):
            tool = UISuggestionTool()
            result = await tool.execute(ToolInput(args={"image_url": "https://example.com/sketch.png"}))

        assert result.error is None
        assert result.result["sketch_id"] is None
        assert result.result["image_url"] == "https://example.com/sketch.png"
        # No similar_uis since no sketch_id
        suggestions = result.result["suggestions"]
        assert any(s["type"] == "sap_components" for s in suggestions)

    @pytest.mark.asyncio
    async def test_execute_detail_level_99_clamped_to_3(self, mock_retriever, mock_catalog):
        with patch("ui.suggestion_tool.get_ui_retriever", return_value=mock_retriever), \
             patch("ui.suggestion_tool.get_sap_catalog", return_value=mock_catalog):
            tool = UISuggestionTool()
            result = await tool.execute(ToolInput(args={"ui_sketch_id": "sk_001", "detail_level": 99}))

        assert result.result["detail_level"] == 3

    @pytest.mark.asyncio
    async def test_execute_detail_level_0_clamped_to_1(self, mock_retriever, mock_catalog):
        with patch("ui.suggestion_tool.get_ui_retriever", return_value=mock_retriever), \
             patch("ui.suggestion_tool.get_sap_catalog", return_value=mock_catalog):
            tool = UISuggestionTool()
            result = await tool.execute(ToolInput(args={"ui_sketch_id": "sk_001", "detail_level": 0}))

        assert result.result["detail_level"] == 1

    @pytest.mark.asyncio
    async def test_execute_missing_both_returns_result_with_nones(self, mock_retriever, mock_catalog):
        with patch("ui.suggestion_tool.get_ui_retriever", return_value=mock_retriever), \
             patch("ui.suggestion_tool.get_sap_catalog", return_value=mock_catalog):
            tool = UISuggestionTool()
            result = await tool.execute(ToolInput(args={"detail_level": 2}))

        assert result.error is None
        assert result.result["sketch_id"] is None
        assert result.result["image_url"] is None
        assert result.result["detail_level"] == 2
