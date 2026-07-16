"""Tests for UI API endpoints."""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from api.main import app


class TestUIAnalyzeEndpoint:
    def test_analyze_requires_image_url(self):
        """POST /ui/analyze requires image_url."""
        client = TestClient(app)
        response = client.post("/ui/analyze", json={})
        assert response.status_code == 422  # Validation error

    def test_analyze_returns_400_on_extraction_failure(self):
        """Returns 400 when VLM extraction returns None."""
        with patch("ui.vlm_extractor.VLMUIExtractor") as mock_cls:
            mock_extractor = AsyncMock()
            mock_extractor.extract.return_value = None
            mock_cls.return_value = mock_extractor

            client = TestClient(app)
            response = client.post(
                "/ui/analyze",
                json={"image_url": "https://example.com/ui.png"}
            )
            assert response.status_code == 400


class TestUISuggestEndpoint:
    def test_suggest_requires_input(self):
        """POST /ui/suggest requires ui_sketch_id or image_url."""
        client = TestClient(app)
        response = client.post("/ui/suggest", json={})
        assert response.status_code == 400

    def test_suggest_returns_result(self):
        """Successful suggestion returns result."""
        with patch("ui.suggestion_tool.UISuggestionTool") as mock_cls:
            mock_tool = AsyncMock()
            mock_tool.execute.return_value = AsyncMock(
                result={"suggestions": [], "detail_level": 1},
                error=None
            )
            mock_cls.return_value = mock_tool

            client = TestClient(app)
            response = client.post(
                "/ui/suggest",
                json={"ui_sketch_id": "sk_test", "detail_level": 1}
            )
            assert response.status_code == 200
