"""Tests for UISuggestionTool MCP tool."""

import asyncio

import pytest
from unittest.mock import patch

from tools.base import ToolInput
from ui.suggestion_tool import UISuggestionTool


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class _MockRetriever:
    async def find_similar_structural(self, *args, **kwargs):
        return getattr(self, "_similar_result", [])


class _MockCatalog:
    def find_for_element_type(self, *args):
        return getattr(self, "_elem_result", [])


class TestValidateInput:
    def test_with_sketch_id_returns_true(self):
        tool = UISuggestionTool()
        assert tool.validate_input({"ui_sketch_id": "sk_test"}) is True

    def test_with_image_url_returns_true(self):
        tool = UISuggestionTool()
        assert tool.validate_input({"image_url": "https://example.com/ui.png"}) is True

    def test_with_neither_returns_false(self):
        tool = UISuggestionTool()
        assert tool.validate_input({"detail_level": 1}) is False


class TestExecute:
    def test_execute_with_sketch_id(self):
        tool = UISuggestionTool()
        mock_retriever = _MockRetriever()
        mock_retriever._similar_result = [{"sketch_id": "sk1"}]
        mock_catalog = _MockCatalog()
        mock_catalog._elem_result = []

        with patch("ui.suggestion_tool.get_ui_retriever", return_value=mock_retriever):
            with patch("ui.suggestion_tool.get_sap_catalog", return_value=mock_catalog):
                result = _run(tool.execute(ToolInput(args={"ui_sketch_id": "sk_test", "detail_level": 1})))
                assert result.result is not None
                assert "suggestions" in result.result

    def test_execute_with_image_url(self):
        tool = UISuggestionTool()
        mock_retriever = _MockRetriever()
        mock_retriever._similar_result = []
        mock_catalog = _MockCatalog()
        mock_catalog._elem_result = []

        with patch("ui.suggestion_tool.get_ui_retriever", return_value=mock_retriever):
            with patch("ui.suggestion_tool.get_sap_catalog", return_value=mock_catalog):
                result = _run(tool.execute(ToolInput(args={"image_url": "https://example.com/ui.png", "detail_level": 1})))
                assert result.result is not None

    def test_execute_detail_level_99_clamped_to_3(self):
        tool = UISuggestionTool()
        mock_retriever = _MockRetriever()
        mock_catalog = _MockCatalog()

        with patch("ui.suggestion_tool.get_ui_retriever", return_value=mock_retriever):
            with patch("ui.suggestion_tool.get_sap_catalog", return_value=mock_catalog):
                result = _run(tool.execute(ToolInput(args={"ui_sketch_id": "sk_test", "detail_level": 99})))
                assert result.result["detail_level"] == 3

    def test_execute_detail_level_0_clamped_to_1(self):
        tool = UISuggestionTool()
        mock_retriever = _MockRetriever()
        mock_catalog = _MockCatalog()

        with patch("ui.suggestion_tool.get_ui_retriever", return_value=mock_retriever):
            with patch("ui.suggestion_tool.get_sap_catalog", return_value=mock_catalog):
                result = _run(tool.execute(ToolInput(args={"ui_sketch_id": "sk_test", "detail_level": 0})))
                assert result.result["detail_level"] == 1

    def test_execute_missing_both_returns_result_with_nones(self):
        tool = UISuggestionTool()
        mock_retriever = _MockRetriever()
        mock_catalog = _MockCatalog()

        with patch("ui.suggestion_tool.get_ui_retriever", return_value=mock_retriever):
            with patch("ui.suggestion_tool.get_sap_catalog", return_value=mock_catalog):
                result = _run(tool.execute(ToolInput(args={"detail_level": 1})))
                assert result.result["sketch_id"] is None
                assert result.result["image_url"] is None
