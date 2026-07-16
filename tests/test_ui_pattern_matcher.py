"""Tests for UIPatternMatcher - pattern matching and Cypher generation."""

from datetime import datetime

from ui.pattern_matcher import (
    UIPatternMatcher,
    get_pattern_matcher,
    _STANDARD_PATTERNS,
)
from ui.models import UIElement, UILayout, UISketch, UIExtractionResult


def _make_sample_result(elements=None):
    """Create a sample UIExtractionResult for testing."""
    sketch = UISketch(
        sketch_id="sk_001",
        title="Test UI",
        source_url="https://example.com/test.png",
        format_type="screenshot",
        ingestion_timestamp=datetime(2026, 4, 14, 10, 0, 0),
    )
    layout = UILayout(
        layout_id="l_001",
        layout_type="single-column",
        responsive=True,
    )
    if elements is None:
        elements = []

    return UIExtractionResult(
        sketch=sketch,
        layout=layout,
        elements=elements,
    )


class TestStandardPatterns:
    def test_standard_patterns_exist(self):
        """_STANDARD_PATTERNS includes list-report, master-detail, form-detail."""
        pattern_names = {p["name"] for p in _STANDARD_PATTERNS}
        assert "list-report" in pattern_names
        assert "master-detail" in pattern_names
        assert "form-detail" in pattern_names


class TestMatchPatterns:
    def test_match_list_report(self):
        """table + filter + button elements match list-report."""
        elements = [
            UIElement(element_id="e1", element_type="table", confidence=0.9),
            UIElement(element_id="e2", element_type="filter", confidence=0.85),
            UIElement(element_id="e3", element_type="button", confidence=0.95),
        ]
        result = _make_sample_result(elements=elements)
        matcher = UIPatternMatcher()
        matches = matcher.match_patterns(result)

        matched_names = {m.pattern_name for m in matches}
        assert "list-report" in matched_names

    def test_no_match_empty_elements(self):
        """No patterns match when no elements."""
        result = _make_sample_result(elements=[])
        matcher = UIPatternMatcher()
        matches = matcher.match_patterns(result)

        assert matches == []

    def test_match_master_detail(self):
        """navigation + table elements match master-detail."""
        elements = [
            UIElement(element_id="e1", element_type="navigation", confidence=0.9),
            UIElement(element_id="e2", element_type="table", confidence=0.85),
        ]
        result = _make_sample_result(elements=elements)
        matcher = UIPatternMatcher()
        matches = matcher.match_patterns(result)

        matched_names = {m.pattern_name for m in matches}
        assert "master-detail" in matched_names

    def test_match_multiple_patterns(self):
        """Elements can match multiple patterns simultaneously."""
        elements = [
            UIElement(element_id="e1", element_type="table", confidence=0.9),
            UIElement(element_id="e2", element_type="filter", confidence=0.85),
            UIElement(element_id="e3", element_type="input", confidence=0.9),
        ]
        result = _make_sample_result(elements=elements)
        matcher = UIPatternMatcher()
        matches = matcher.match_patterns(result)

        matched_names = {m.pattern_name for m in matches}
        assert "list-report" in matched_names
        assert "table-edit" in matched_names


class TestBuildPatternCypher:
    def test_build_pattern_cypher(self):
        """Generates Cypher with UIPattern, MATCHES_PATTERN, list-report."""
        elements = [
            UIElement(element_id="e1", element_type="table", confidence=0.9),
            UIElement(element_id="e2", element_type="filter", confidence=0.85),
        ]
        result = _make_sample_result(elements=elements)
        matcher = UIPatternMatcher()
        matches = matcher.match_patterns(result)
        cypher = matcher.build_pattern_cypher(result, matches)

        assert "UIPattern" in cypher
        assert "MATCHES_PATTERN" in cypher
        assert "list-report" in cypher

    def test_build_pattern_cypher_empty_matches(self):
        """Returns empty string when no matches."""
        result = _make_sample_result(elements=[])
        matcher = UIPatternMatcher()
        cypher = matcher.build_pattern_cypher(result, [])

        assert cypher == ""

    def test_build_pattern_cypher_contains_pattern_id(self):
        """Cypher contains pattern_id MERGE."""
        elements = [
            UIElement(element_id="e1", element_type="chart", confidence=0.9),
        ]
        result = _make_sample_result(elements=elements)
        matcher = UIPatternMatcher()
        matches = matcher.match_patterns(result)
        cypher = matcher.build_pattern_cypher(result, matches)

        assert "p_dashboard" in cypher
        assert "MERGE" in cypher


class TestBuildFullCypherIntegration:
    def test_build_full_cypher_integration(self):
        """Pattern Cypher combines with graph builder."""
        from ui.graph_builder import UIGraphBuilder

        elements = [
            UIElement(element_id="e1", element_type="table", confidence=0.9),
            UIElement(element_id="e2", element_type="filter", confidence=0.85),
            UIElement(element_id="e3", element_type="button", confidence=0.95),
        ]
        result = _make_sample_result(elements=elements)
        builder = UIGraphBuilder()
        cypher = builder.build_cypher(result)

        assert "UISketch" in cypher
        assert "UIElement" in cypher
        assert "UILayout" in cypher
        assert "UIPattern" in cypher
        assert "MATCHES_PATTERN" in cypher


class TestSAPMappingCypher:
    def test_build_sap_mapping_cypher(self):
        """Returns USES_PATTERN Cypher."""
        matcher = UIPatternMatcher()
        cypher = matcher.build_sap_mapping_cypher()

        assert "USES_PATTERN" in cypher
        assert "SAPComponent" in cypher
        assert "UIPattern" in cypher
        assert "supported_element_types" in cypher


class TestGetPatternMatcher:
    def test_get_pattern_matcher_returns_singleton(self):
        """get_pattern_matcher returns same instance."""
        m1 = get_pattern_matcher()
        m2 = get_pattern_matcher()
        assert m1 is m2
