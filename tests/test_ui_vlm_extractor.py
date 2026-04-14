"""Tests for structured VLM UI extractor."""

import json
import pytest
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError


VALID_EXTRACT_JSON = json.dumps({
    "source_type": "sketch",
    "page_type": "list-report",
    "layout": {
        "type": "two-column",
        "regions": [
            {"name": "sidebar", "elements": []},
            {"name": "content", "elements": []}
        ]
    },
    "elements": [
        {
            "id": "el-1",
            "type": "table",
            "label": "Sales Orders",
            "position": {"x": 10, "y": 20, "width": 200, "height": 100},
            "attributes": {"columns": 5},
            "interactions": ["click", "scroll"],
            "confidence": 0.92
        }
    ],
    "user_actions": [
        {"trigger": "click Save", "expected_result": "form-submitted"}
    ]
})


class TestUIExtractionSchema:
    def test_valid_json_roundtrip(self):
        from ui.vlm_extractor import UIExtractionSchema

        data = json.loads(VALID_EXTRACT_JSON)
        schema = UIExtractionSchema(**data)
        assert schema.source_type == "sketch"
        assert schema.page_type == "list-report"
        assert schema.layout.type == "two-column"
        assert len(schema.layout.regions) == 2
        assert len(schema.elements) == 1
        assert schema.elements[0].id == "el-1"
        assert len(schema.user_actions) == 1

    def test_invalid_source_type_raises(self):
        from ui.vlm_extractor import UIExtractionSchema

        data = json.loads(VALID_EXTRACT_JSON)
        data["source_type"] = "invalid_type"
        with pytest.raises(ValidationError):
            UIExtractionSchema(**data)

    def test_missing_required_fields_raises(self):
        from ui.vlm_extractor import UIExtractionSchema

        with pytest.raises(ValidationError):
            UIExtractionSchema()

    def test_missing_layout_raises(self):
        from ui.vlm_extractor import UIExtractionSchema

        data = {"source_type": "sketch"}
        with pytest.raises(ValidationError):
            UIExtractionSchema(**data)

    def test_all_valid_source_types(self):
        from ui.vlm_extractor import UIExtractionSchema, VALID_SOURCE_TYPES

        base = {
            "source_type": "sketch",
            "layout": {"type": "single-column", "regions": []},
            "elements": [],
            "user_actions": []
        }
        for st in VALID_SOURCE_TYPES:
            base["source_type"] = st
            schema = UIExtractionSchema(**base)
            assert schema.source_type == st

    def test_invalid_element_type_still_parsed(self):
        from ui.vlm_extractor import UIExtractionSchema

        data = json.loads(VALID_EXTRACT_JSON)
        data["elements"][0]["type"] = "weird-element"
        # Element type is not strictly validated by Pydantic (free string)
        schema = UIExtractionSchema(**data)
        assert schema.elements[0].type == "weird-element"


class TestParseVLMResponse:
    def test_valid_json_returns_schema(self):
        from ui.vlm_extractor import parse_vlm_response

        result = parse_vlm_response(VALID_EXTRACT_JSON)
        assert result is not None
        assert result.source_type == "sketch"

    def test_markdown_code_blocks_strips_and_parses(self):
        from ui.vlm_extractor import parse_vlm_response

        wrapped = f"```json\n{VALID_EXTRACT_JSON}\n```"
        result = parse_vlm_response(wrapped)
        assert result is not None
        assert result.source_type == "sketch"

    def test_markdown_backticks_no_language(self):
        from ui.vlm_extractor import parse_vlm_response

        wrapped = f"```\n{VALID_EXTRACT_JSON}\n```"
        result = parse_vlm_response(wrapped)
        assert result is not None
        assert result.source_type == "sketch"

    def test_invalid_text_returns_none(self):
        from ui.vlm_extractor import parse_vlm_response

        result = parse_vlm_response("This is not JSON at all")
        assert result is None

    def test_empty_string_returns_none(self):
        from ui.vlm_extractor import parse_vlm_response

        result = parse_vlm_response("")
        assert result is None

    def test_empty_json_object_returns_none(self):
        from ui.vlm_extractor import parse_vlm_response

        result = parse_vlm_response("{}")
        assert result is None

    def test_partial_json_missing_required_returns_none(self):
        from ui.vlm_extractor import parse_vlm_response

        # Missing layout, elements, etc.
        result = parse_vlm_response('{"source_type": "sketch"}')
        assert result is None

    def test_code_block_with_surrounding_text(self):
        from ui.vlm_extractor import parse_vlm_response

        wrapped = f"Here is the result:\n```json\n{VALID_EXTRACT_JSON}\n```\nHope this helps!"
        result = parse_vlm_response(wrapped)
        assert result is not None
        assert result.source_type == "sketch"


class TestVLMUIExtractor:
    SAMPLE_IMAGE_URL = "https://example.com/sketch.png"

    @pytest.fixture
    def extractor(self):
        from ui.vlm_extractor import VLMUIExtractor
        return VLMUIExtractor(api_key_env="DUMMY_KEY")

    @pytest.mark.asyncio
    async def test_extract_retry_success(self, extractor):
        """First call fails, second succeeds."""
        fail_response = AsyncMock()
        fail_response.status_code = 500
        fail_response.text = "Server Error"

        success_response = AsyncMock()
        success_response.status_code = 200
        success_response.json = lambda: {"choices": [{"message": {"content": VALID_EXTRACT_JSON}}]}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[fail_response, success_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ui.vlm_extractor.httpx.AsyncClient", return_value=mock_client):
            result = await extractor.extract(self.SAMPLE_IMAGE_URL, max_retries=2)

        assert result is not None
        assert result.source_type == "sketch"
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_extract_all_retries_fail(self, extractor):
        """All retries fail, returns None."""
        fail_response = AsyncMock()
        fail_response.status_code = 500
        fail_response.text = "Server Error"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=fail_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ui.vlm_extractor.httpx.AsyncClient", return_value=mock_client):
            result = await extractor.extract(self.SAMPLE_IMAGE_URL, max_retries=2)

        assert result is None
        assert mock_client.post.call_count == 3  # initial + 2 retries

    @pytest.mark.asyncio
    async def test_build_prompt_returns_string(self, extractor):
        prompt = extractor.build_extraction_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "JSON" in prompt or "json" in prompt

    @pytest.mark.asyncio
    async def test_call_vlm_success(self, extractor):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {"choices": [{"message": {"content": '{"key": "value"}'}}]}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ui.vlm_extractor.httpx.AsyncClient", return_value=mock_client):
            result = await extractor._call_vlm(self.SAMPLE_IMAGE_URL, "test prompt")

        assert result == '{"key": "value"}'

    @pytest.mark.asyncio
    async def test_call_vlm_non_200_raises(self, extractor):
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Error"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ui.vlm_extractor.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception):
                await extractor._call_vlm(self.SAMPLE_IMAGE_URL, "test prompt")

    @pytest.mark.asyncio
    async def test_extract_with_exception_retry(self, extractor):
        """Network exception triggers retry."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=[
                Exception("Connection error"),
                AsyncMock(
                    status_code=200,
                    json=lambda: {"choices": [{"message": {"content": VALID_EXTRACT_JSON}}]}
                )
            ]
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ui.vlm_extractor.httpx.AsyncClient", return_value=mock_client):
            result = await extractor.extract(self.SAMPLE_IMAGE_URL, max_retries=1)

        assert result is not None
        assert result.source_type == "sketch"
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_extract_single_attempt(self, extractor):
        """With max_retries=0, only one attempt is made."""
        success_response = AsyncMock()
        success_response.status_code = 200
        success_response.json = lambda: {"choices": [{"message": {"content": VALID_EXTRACT_JSON}}]}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=success_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ui.vlm_extractor.httpx.AsyncClient", return_value=mock_client):
            result = await extractor.extract(self.SAMPLE_IMAGE_URL, max_retries=0)

        assert result is not None
        assert mock_client.post.call_count == 1
