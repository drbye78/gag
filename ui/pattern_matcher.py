"""UIPattern node creation and MATCHES_PATTERN relationship building.

Uses parameterized Cypher queries to prevent injection attacks.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from ui.models import UIExtractionResult, UIPattern

logger = logging.getLogger(__name__)

CypherStatement = Tuple[str, Dict[str, Any]]

# Standard UI patterns with required element composition
_STANDARD_PATTERNS = [
    {
        "name": "list-report",
        "description": "Fiori List-Report: filter bar + data table + actions",
        "required_elements": {"table", "filter"},
        "optional_elements": {"button", "navigation"},
        "complexity": "medium",
    },
    {
        "name": "master-detail",
        "description": "Master-Detail: navigation + table/form on split view",
        "required_elements": {"navigation", "table"},
        "optional_elements": {"form", "button"},
        "complexity": "medium",
    },
    {
        "name": "form-detail",
        "description": "Form with detail: input form + submit action",
        "required_elements": {"form", "button"},
        "optional_elements": {"input", "select"},
        "complexity": "low",
    },
    {
        "name": "dashboard",
        "description": "Dashboard overview: charts + cards + filters",
        "required_elements": {"chart"},
        "optional_elements": {"card", "filter", "navigation"},
        "complexity": "medium",
    },
    {
        "name": "wizard",
        "description": "Multi-step wizard: navigation + form + actions",
        "required_elements": {"navigation", "form"},
        "optional_elements": {"button", "tab"},
        "complexity": "high",
    },
    {
        "name": "table-edit",
        "description": "Editable table: table + inline editing controls",
        "required_elements": {"table", "input"},
        "optional_elements": {"button", "filter"},
        "complexity": "medium",
    },
]


class UIPatternMatcher:
    """Matches UI sketches to known patterns and builds graph relationships."""

    def match_patterns(self, result: UIExtractionResult) -> List[UIPattern]:
        """Match extracted elements against standard patterns."""
        if not result.elements:
            return []

        element_types = {e.element_type for e in result.elements}
        matches = []

        for pattern_def in _STANDARD_PATTERNS:
            required = set(pattern_def["required_elements"])
            if required.issubset(element_types):
                pattern = UIPattern(
                    pattern_id=f"p_{pattern_def['name']}",
                    pattern_name=pattern_def["name"],
                    description=pattern_def["description"],
                    complexity=pattern_def.get("complexity", "medium"),
                    required_elements=list(required),
                )
                matches.append(pattern)

        return matches

    def build_pattern_cypher(
        self, result: UIExtractionResult, matches: List[UIPattern]
    ) -> List[CypherStatement]:
        """Build parameterized Cypher for UIPattern nodes and MATCHES_PATTERN relationships."""
        if not matches:
            return []

        statements: List[CypherStatement] = []
        for pattern in matches:
            props: Dict[str, Any] = {
                "pattern_id": pattern.pattern_id,
                "pattern_name": pattern.pattern_name,
                "description": pattern.description,
                "complexity": pattern.complexity,
                "required_elements": pattern.required_elements,
            }
            statements.append(
                (
                    "MERGE (p:UIPattern {pattern_id: $pattern_id}) SET p = $props",
                    {"pattern_id": pattern.pattern_id, "props": props},
                )
            )
            statements.append(
                (
                    "MATCH (s:UISketch {sketch_id: $sketch_id}) "
                    "MERGE (s)-[:MATCHES_PATTERN {confidence: 1.0}]->(p)",
                    {"sketch_id": result.sketch.sketch_id},
                )
            )

        return statements

    def build_sap_mapping_cypher(self) -> str:
        """Build USES_PATTERN relationships between SAPComponent and UIPattern.

        No user-supplied values — safe to return as plain string.
        """
        return (
            "MATCH (sc:SAPComponent), (p:UIPattern) "
            "WHERE ANY(elem IN p.required_elements WHERE elem IN sc.supported_element_types) "
            "MERGE (sc)-[:USES_PATTERN]->(p)"
        )


_pattern_matcher: Optional[UIPatternMatcher] = None


def get_pattern_matcher() -> UIPatternMatcher:
    global _pattern_matcher
    if _pattern_matcher is None:
        _pattern_matcher = UIPatternMatcher()
    return _pattern_matcher
