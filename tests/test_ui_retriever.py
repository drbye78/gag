"""Tests for UIRetriever - graph-first UI sketch retrieval."""

from unittest.mock import AsyncMock, patch

import pytest

from ui.retriever import UIRetriever, get_ui_retriever


class TestSearchByElementType:
    @pytest.mark.asyncio
    async def test_returns_list_of_sketches(self):
        retriever = UIRetriever()
        mock_results = [
            {"s.sketch_id": "sk_001", "s.title": "Dashboard", "s.element_count": 12},
            {"s.sketch_id": "sk_002", "s.title": "Settings", "s.element_count": 8},
        ]
        retriever._execute_cypher = AsyncMock(return_value=mock_results)

        results = await retriever.search_by_element_type("button")

        assert len(results) == 2
        assert results[0]["s.sketch_id"] == "sk_001"
        assert results[0]["s.element_count"] == 12

    @pytest.mark.asyncio
    async def test_empty_returns_empty_list(self):
        retriever = UIRetriever()
        retriever._execute_cypher = AsyncMock(return_value=[])

        results = await retriever.search_by_element_type("nonexistent")

        assert results == []
        assert isinstance(results, list)


class TestFindSimilarStructural:
    @pytest.mark.asyncio
    async def test_returns_list_with_overlap_counts(self):
        retriever = UIRetriever()
        mock_results = [
            {"b.sketch_id": "sk_003", "b.title": "Similar Dashboard", "overlap": 4},
            {"b.sketch_id": "sk_004", "b.title": "Form Page", "overlap": 2},
        ]
        retriever._execute_cypher = AsyncMock(return_value=mock_results)

        results = await retriever.find_similar_structural("sk_001")

        assert len(results) == 2
        assert results[0]["overlap"] == 4
        assert results[1]["overlap"] == 2


class TestFindSapCandidates:
    @pytest.mark.asyncio
    async def test_returns_sap_components(self):
        retriever = UIRetriever()
        mock_results = [
            {"sc.name": "sap.m.Table", "sc.library": "sap.m", "sc.complexity": 2},
            {"sc.name": "sap.ui.table.Table", "sc.library": "sap.ui.table", "sc.complexity": 3},
        ]
        retriever._execute_cypher = AsyncMock(return_value=mock_results)

        results = await retriever.find_sap_candidates("table")

        assert len(results) == 2
        assert results[0]["sc.name"] == "sap.m.Table"
        assert results[0]["sc.complexity"] == 2


class TestSearchCombined:
    @pytest.mark.asyncio
    async def test_returns_matching_sketches(self):
        retriever = UIRetriever()
        mock_results = [
            {"s.sketch_id": "sk_001", "s.title": "Report Page", "s.element_count": 15},
        ]
        retriever._execute_cypher = AsyncMock(return_value=mock_results)

        results = await retriever.search_combined(
            element_types=["table", "chart"], layout_type="two-column"
        )

        assert len(results) == 1
        assert results[0]["s.sketch_id"] == "sk_001"


class TestSingleton:
    def test_same_instance_returned_twice(self):
        first = get_ui_retriever()
        second = get_ui_retriever()

        assert first is second


class TestExecuteCypherException:
    @pytest.mark.asyncio
    async def test_returns_empty_list_on_failure(self):
        # Patch get_falkordb_client via sys.modules to handle the inline import
        import sys
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_client.query = AsyncMock(side_effect=ConnectionError("DB unreachable"))

        mock_module = MagicMock()
        mock_module.get_falkordb_client = MagicMock(return_value=mock_client)

        with patch.dict(sys.modules, {"graph.client": mock_module}):
            # Force reimport by removing cached module
            if "ui.retriever" in sys.modules:
                del sys.modules["ui.retriever"]

            from ui.retriever import UIRetriever as TestRetriever
            retriever = TestRetriever()

            result = await retriever._execute_cypher("MATCH (n) RETURN n")

            assert result == []
