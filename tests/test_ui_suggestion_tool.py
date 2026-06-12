"""Tests for UI Suggestion Tool."""

from unittest.mock import MagicMock, patch

import pytest

from tools.base import ToolInput

pytestmark = pytest.mark.asyncio


class _MockRegistry:
    def all_domains(self):
        return ["sap", "aws", "azure"]

    def find_components(self, element_type):
        if element_type == "button":
            return [
                (
                    "sap",
                    MagicMock(
                        name="sap.m.Button", library="sap.m", complexity=1, properties=[], events=[]
                    ),
                ),
                (
                    "aws",
                    MagicMock(
                        name="AmplifyButton",
                        library="@aws-amplify",
                        complexity=1,
                        properties=[],
                        events=[],
                    ),
                ),
            ]
        return []


class TestExecute:
    async def test_execute_with_sketch_id(self):
        from ui.suggestion_tool import UISuggestionTool

        tool = UISuggestionTool()
        with patch("ui.suggestion_tool.get_ui_knowledge_registry", return_value=_MockRegistry()):
            result = await tool.execute(
                ToolInput(args={"ui_sketch_id": "sk_test", "detail_level": 1})
            )
            assert result.result is not None
            assert "domains" in result.metadata
            assert "sap" in result.metadata["domains"]

    async def test_execute_with_image_url(self):
        from ui.suggestion_tool import UISuggestionTool

        tool = UISuggestionTool()
        with patch("ui.suggestion_tool.get_ui_knowledge_registry", return_value=_MockRegistry()):
            result = await tool.execute(
                ToolInput(args={"image_url": "https://example.com/ui.png", "detail_level": 1})
            )
            assert result.result is not None


class TestValidation:
    def test_validate_input_with_sketch_id(self):
        from ui.suggestion_tool import UISuggestionTool

        tool = UISuggestionTool()
        assert tool.validate_input({"ui_sketch_id": "test"}) is True

    def test_validate_input_with_image_url(self):
        from ui.suggestion_tool import UISuggestionTool

        tool = UISuggestionTool()
        assert tool.validate_input({"image_url": "http://example.com"}) is True

    def test_validate_input_missing_both(self):
        from ui.suggestion_tool import UISuggestionTool

        tool = UISuggestionTool()
        assert tool.validate_input({}) is False
