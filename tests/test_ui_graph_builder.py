"""Tests for UIGraphBuilder - Cypher generation for UI sketch graphs."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from ui.graph_builder import UIGraphBuilder
from ui.models import UIElement, UILayout, UISketch, UIExtractionResult


def _make_sample_result(
    elements=None,
    visual_embedding=None,
    ocr_text=None,
    page_type=None,
):
    """Create a sample UIExtractionResult for testing."""
    sketch = UISketch(
        sketch_id="sk_001",
        title="Order Management",
        source_url="https://example.com/order-ui.png",
        format_type="screenshot",
        ingestion_timestamp=datetime(2026, 4, 14, 10, 0, 0),
        page_type=page_type,
    )
    layout = UILayout(
        layout_id="l_001",
        layout_type="header-content-footer",
        hierarchy=["header", "sidebar", "content", "footer"],
        responsive=True,
    )
    if elements is None:
        elements = [
            UIElement(
                element_id="e1",
                element_type="table",
                label="Orders",
                position={"row": 0, "col": 1},
                attributes={"columns": 5, "has_filter": True},
                interactions=["click-row-navigates"],
                confidence=0.92,
            ),
            UIElement(
                element_id="e2",
                element_type="button",
                label="Save",
                position={"row": 1, "col": 0},
                confidence=0.88,
            ),
        ]

    return UIExtractionResult(
        sketch=sketch,
        layout=layout,
        elements=elements,
        visual_embedding=visual_embedding,
        ocr_text=ocr_text,
        source_type_confidence=0.85,
    )


class TestSketchNodeCypher:
    def test_build_sketch_node_cypher(self):
        builder = UIGraphBuilder()
        result = _make_sample_result()
        cypher = builder._build_sketch_node_cypher(result)

        assert "CREATE" in cypher
        assert "UISketch" in cypher
        assert "sk_001" in cypher
        assert "screenshot" in cypher

    def test_sketch_node_contains_sketch_id(self):
        builder = UIGraphBuilder()
        result = _make_sample_result()
        cypher = builder._build_sketch_node_cypher(result)

        assert '"sketch_id"' in cypher
        assert "sk_001" in cypher

    def test_sketch_node_contains_format_type(self):
        builder = UIGraphBuilder()
        result = _make_sample_result()
        cypher = builder._build_sketch_node_cypher(result)

        assert '"format_type"' in cypher
        assert "screenshot" in cypher

    def test_sketch_node_with_page_type(self):
        builder = UIGraphBuilder()
        result = _make_sample_result(page_type="list-report")
        cypher = builder._build_sketch_node_cypher(result)

        assert "list-report" in cypher

    def test_sketch_node_with_visual_embedding(self):
        builder = UIGraphBuilder()
        embedding = [0.1, 0.2, 0.3, 0.4]
        result = _make_sample_result(visual_embedding=embedding)
        cypher = builder._build_sketch_node_cypher(result)

        assert "visual_embedding" in cypher

    def test_sketch_node_with_ocr_text(self):
        builder = UIGraphBuilder()
        result = _make_sample_result(ocr_text="Order Management UI")
        cypher = builder._build_sketch_node_cypher(result)

        assert "ocr_text" in cypher
        assert "Order Management UI" in cypher

    def test_sketch_node_without_optional_fields(self):
        builder = UIGraphBuilder()
        result = _make_sample_result()
        cypher = builder._build_sketch_node_cypher(result)

        assert "visual_embedding" not in cypher
        assert "ocr_text" not in cypher


class TestElementNodesCypher:
    def test_build_element_nodes_cypher(self):
        builder = UIGraphBuilder()
        result = _make_sample_result()
        cypher = builder._build_element_nodes_cypher(result)

        assert "CREATE" in cypher
        assert "UIElement" in cypher
        assert "CONTAINS_ELEMENT" in cypher

    def test_element_nodes_contain_element_types(self):
        builder = UIGraphBuilder()
        result = _make_sample_result()
        cypher = builder._build_element_nodes_cypher(result)

        assert "table" in cypher
        assert "button" in cypher

    def test_element_nodes_have_relationships(self):
        builder = UIGraphBuilder()
        result = _make_sample_result()
        cypher = builder._build_element_nodes_cypher(result)

        assert "s)-[:CONTAINS_ELEMENT" in cypher
        assert "l)-[:CONTAINS_ELEMENT" in cypher

    def test_element_nodes_empty_elements(self):
        builder = UIGraphBuilder()
        result = _make_sample_result(elements=[])
        cypher = builder._build_element_nodes_cypher(result)

        assert cypher == ""


class TestLayoutNodeCypher:
    def test_build_layout_node_cypher(self):
        builder = UIGraphBuilder()
        result = _make_sample_result()
        cypher = builder._build_layout_node_cypher(result)

        assert "UILayout" in cypher
        assert "HAS_LAYOUT" in cypher

    def test_layout_node_contains_layout_type(self):
        builder = UIGraphBuilder()
        result = _make_sample_result()
        cypher = builder._build_layout_node_cypher(result)

        assert "layout_type" in cypher
        assert "header-content-footer" in cypher

    def test_layout_node_has_relationship(self):
        builder = UIGraphBuilder()
        result = _make_sample_result()
        cypher = builder._build_layout_node_cypher(result)

        assert "CREATE (s)-[:HAS_LAYOUT]->(l)" in cypher


class TestFullBuildCypher:
    def test_full_cypher_contains_all_node_types(self):
        builder = UIGraphBuilder()
        result = _make_sample_result()
        cypher = builder.build_cypher(result)

        assert "UISketch" in cypher
        assert "UIElement" in cypher
        assert "UILayout" in cypher

    def test_full_cypher_contains_relationships(self):
        builder = UIGraphBuilder()
        result = _make_sample_result()
        cypher = builder.build_cypher(result)

        assert "CONTAINS_ELEMENT" in cypher
        assert "HAS_LAYOUT" in cypher

    def test_full_cypher_with_embedding(self):
        builder = UIGraphBuilder()
        embedding = [0.1, 0.2, 0.3]
        result = _make_sample_result(visual_embedding=embedding)
        cypher = builder.build_cypher(result)

        assert "visual_embedding" in cypher

    def test_full_cypher_with_empty_elements(self):
        builder = UIGraphBuilder()
        result = _make_sample_result(elements=[])
        cypher = builder.build_cypher(result)

        assert "UISketch" in cypher
        assert "UILayout" in cypher
        assert "UIElement" not in cypher
        assert "CONTAINS_ELEMENT" not in cypher


class TestBuild:
    @pytest.mark.asyncio
    async def test_build_with_mocked_execute(self):
        builder = UIGraphBuilder()
        mock_client = MagicMock()
        mock_client.execute = AsyncMock(return_value={"results": []})
        with patch("graph.client.get_falkordb_client", return_value=mock_client):
            result = _make_sample_result()
            response = await builder.build(result)
        assert response["success"] is True

    @pytest.mark.asyncio
    async def test_build_calls_execute_with_cypher(self):
        builder = UIGraphBuilder()
        mock_client = MagicMock()
        mock_client.execute = AsyncMock(return_value={"results": []})
        with patch("graph.client.get_falkordb_client", return_value=mock_client):
            result = _make_sample_result()
            await builder.build(result)
        # Verify execute was called
        mock_client.execute.assert_called_once()
        # Check the Cypher contains expected node types
        call_args = mock_client.execute.call_args
        cypher_str = str(call_args)
        assert "UISketch" in cypher_str
        assert "UIElement" in cypher_str
        assert "UILayout" in cypher_str

    @pytest.mark.asyncio
    async def test_build_failure(self):
        builder = UIGraphBuilder()
        mock_client = MagicMock()
        mock_client.execute = AsyncMock(side_effect=Exception("Connection refused"))
        with patch("graph.client.get_falkordb_client", return_value=mock_client):
            result = _make_sample_result()
            response = await builder.build(result)
        assert response["success"] is False
        assert "error" in response
        assert response["error"] == "Connection refused"
