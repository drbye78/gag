"""Tests for UIRetriever - graph-first UI sketch retrieval."""

import asyncio

from ui.retriever import UIRetriever, get_ui_retriever


def _run(coro):
    """Run async coroutine in sync test context."""
    return asyncio.new_event_loop().run_until_complete(coro)


async def _make_results(results):
    return results


class TestSearchByElementType:
    def test_returns_list_of_sketches(self):
        retriever = UIRetriever()
        mock_results = [
            {"s.sketch_id": "sk_001", "s.title": "Dashboard", "s.element_count": 12},
        ]

        async def mock_execute(*args, **kwargs):
            return mock_results

        retriever._execute_cypher = mock_execute
        results = _run(retriever.search_by_element_type("button"))
        assert len(results) == 1
        assert results[0]["s.sketch_id"] == "sk_001"

    def test_empty_returns_empty_list(self):
        retriever = UIRetriever()

        async def mock_execute(*args, **kwargs):
            return []

        retriever._execute_cypher = mock_execute
        results = _run(retriever.search_by_element_type("nonexistent"))
        assert results == []


class TestFindSimilarStructural:
    def test_returns_list_with_overlap_counts(self):
        retriever = UIRetriever()
        mock_results = [
            {"b.sketch_id": "sk_003", "b.title": "Dashboard", "overlap": 4},
        ]

        async def mock_execute(*args, **kwargs):
            return mock_results

        retriever._execute_cypher = mock_execute
        results = _run(retriever.find_similar_structural("sk_test"))
        assert len(results) == 1
        assert results[0]["overlap"] == 4


class TestFindSapCandidates:
    def test_returns_sap_components(self):
        retriever = UIRetriever()
        mock_results = [
            {"sc.name": "sap.m.Table", "sc.library": "sap.m", "sc.complexity": 2},
        ]

        async def mock_execute(*args, **kwargs):
            return mock_results

        retriever._execute_cypher = mock_execute
        results = _run(retriever.find_sap_candidates("table"))
        assert len(results) == 1
        assert results[0]["sc.name"] == "sap.m.Table"


class TestSearchCombined:
    def test_returns_matching_sketches(self):
        retriever = UIRetriever()
        mock_results = [
            {"s.sketch_id": "sk_001", "s.title": "Dashboard"},
        ]

        async def mock_execute(*args, **kwargs):
            return mock_results

        retriever._execute_cypher = mock_execute
        results = _run(retriever.search_combined(["table", "button"]))
        assert len(results) == 1


class TestSingleton:
    def test_same_instance_returned_twice(self):
        r1 = get_ui_retriever()
        r2 = get_ui_retriever()
        assert r1 is r2


class TestExecuteCypherException:
    def test_returns_empty_list_on_failure(self):
        # Test that _execute_cypher catches import errors when graph.client unavailable
        import sys
        original = sys.modules.get("graph.client")
        sys.modules["graph.client"] = None

        try:
            retriever = UIRetriever()
            results = _run(retriever._execute_cypher("MATCH (n) RETURN n"))
            assert results == []
        finally:
            if original is not None:
                sys.modules["graph.client"] = original
            else:
                sys.modules.pop("graph.client", None)
