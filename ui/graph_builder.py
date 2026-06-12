"""Graph builder for UI sketch understanding - constructs FalkorDB graph nodes and relationships.

Uses parameterized Cypher queries to prevent injection attacks.
"""

import json
import logging
from typing import Any, Dict, List, Tuple

from ui.models import UIExtractionResult

logger = logging.getLogger(__name__)

CypherStatement = Tuple[str, Dict[str, Any]]


class UIGraphBuilder:
    """Builds Cypher queries for UI sketch graph construction."""

    def build_cypher(self, result: UIExtractionResult) -> List[CypherStatement]:
        """Build complete Cypher for all nodes and relationships.

        Returns a list of (query, params) tuples for parameterized execution.
        """
        from ui.issue_tracker import get_issue_tracker
        from ui.pattern_matcher import get_pattern_matcher

        matcher = get_pattern_matcher()
        tracker = get_issue_tracker()
        matches = matcher.match_patterns(result)

        statements: List[CypherStatement] = []
        statements.extend(self._build_sketch_node_cypher(result))
        statements.extend(self._build_layout_node_cypher(result))
        statements.extend(self._build_element_nodes_cypher(result))
        statements.extend(matcher.build_pattern_cypher(result, matches))
        statements.extend(tracker.build_issues_cypher())
        return statements

    def _build_sketch_node_cypher(self, result: UIExtractionResult) -> List[CypherStatement]:
        """CREATE UISketch node with properties."""
        sketch = result.sketch
        props: Dict[str, Any] = {
            "sketch_id": sketch.sketch_id,
            "title": sketch.title,
            "source_url": sketch.source_url,
            "format_type": sketch.format_type,
            "ingestion_timestamp": sketch.ingestion_timestamp.isoformat(),
            "element_count": len(result.elements),
            "source_type_confidence": result.source_type_confidence,
        }

        if sketch.page_type:
            props["page_type"] = sketch.page_type

        if result.visual_embedding is not None:
            props["visual_embedding"] = json.dumps(result.visual_embedding)

        if result.ocr_text is not None:
            props["ocr_text"] = result.ocr_text

        return [("CREATE (s:UISketch $props)", {"props": props})]

    def _build_layout_node_cypher(self, result: UIExtractionResult) -> List[CypherStatement]:
        """CREATE UILayout node + HAS_LAYOUT relationship."""
        layout = result.layout
        props: Dict[str, Any] = {
            "layout_id": layout.layout_id,
            "layout_type": layout.layout_type,
            "hierarchy": json.dumps(layout.hierarchy),
            "responsive": layout.responsive,
        }

        return [
            ("CREATE (l:UILayout $props)", {"props": props}),
            (
                "MATCH (s:UISketch {sketch_id: $sketch_id}) CREATE (s)-[:HAS_LAYOUT]->(l)",
                {"sketch_id": result.sketch.sketch_id},
            ),
        ]

    def _build_element_nodes_cypher(self, result: UIExtractionResult) -> List[CypherStatement]:
        """CREATE UIElement nodes + CONTAINS_ELEMENT relationships."""
        if not result.elements:
            return []

        statements: List[CypherStatement] = []
        for idx, elem in enumerate(result.elements):
            props: Dict[str, Any] = {
                "element_id": elem.element_id,
                "element_type": elem.element_type,
                "confidence": elem.confidence,
            }

            if elem.label is not None:
                props["label"] = elem.label

            if elem.position:
                props["position"] = json.dumps(elem.position)

            if elem.attributes:
                props["attributes"] = json.dumps(elem.attributes)

            if elem.interactions:
                props["interactions"] = json.dumps(elem.interactions)

            element_alias = f"e{idx}"
            statements.append((f"CREATE ({element_alias}:UIElement $props)", {"props": props}))
            statements.append(
                (
                    f"MATCH (s:UISketch {{sketch_id: $sketch_id}}), "
                    f"({element_alias}:UIElement {{element_id: $element_id}}) "
                    f"CREATE (s)-[:CONTAINS_ELEMENT {{element_id: $element_id}}]->({element_alias})",
                    {
                        "sketch_id": result.sketch.sketch_id,
                        "element_id": elem.element_id,
                    },
                )
            )
            statements.append(
                (
                    f"MATCH (l:UILayout {{layout_id: $layout_id}}), "
                    f"({element_alias}:UIElement {{element_id: $element_id}}) "
                    f"CREATE (l)-[:CONTAINS_ELEMENT {{element_id: $element_id}}]->({element_alias})",
                    {
                        "layout_id": result.layout.layout_id,
                        "element_id": elem.element_id,
                    },
                )
            )

        return statements

    async def _execute_cypher(self, statements: List[CypherStatement]) -> Dict[str, Any]:
        """Execute parameterized Cypher statements against FalkorDB."""
        try:
            from graph.client import get_falkordb_client

            client = get_falkordb_client()
            responses = []
            for query, params in statements:
                response = await client.execute(query, params)
                responses.append(response)
            return {"success": True, "responses": responses}
        except Exception as e:
            logger.exception("Failed to execute Cypher statements")
            return {"success": False, "error": str(e)}

    async def build(self, result: UIExtractionResult) -> Dict[str, Any]:
        """Build and execute graph for a UIExtractionResult."""
        statements = self.build_cypher(result)
        return await self._execute_cypher(statements)
