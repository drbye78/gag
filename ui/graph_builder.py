"""Graph builder for UI sketch understanding - constructs FalkorDB graph nodes and relationships."""

import json
from typing import Any, Dict

from ui.models import UIExtractionResult


class UIGraphBuilder:
    """Builds Cypher queries for UI sketch graph construction."""

    def build_cypher(self, result: UIExtractionResult) -> str:
        """Build complete Cypher for all nodes and relationships."""
        from ui.issue_tracker import get_issue_tracker
        from ui.pattern_matcher import get_pattern_matcher

        matcher = get_pattern_matcher()
        tracker = get_issue_tracker()
        matches = matcher.match_patterns(result)

        parts = []
        parts.append(self._build_sketch_node_cypher(result))
        parts.append(self._build_layout_node_cypher(result))
        parts.append(self._build_element_nodes_cypher(result))
        parts.append(matcher.build_pattern_cypher(result, matches))
        parts.append(tracker.build_issues_cypher())
        return "\n".join(parts)

    def _build_sketch_node_cypher(self, result: UIExtractionResult) -> str:
        """CREATE UISketch node with properties."""
        sketch = result.sketch
        props = {
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

        props_str = json.dumps(props)
        return f"CREATE (s:UISketch {props_str})"

    def _build_layout_node_cypher(self, result: UIExtractionResult) -> str:
        """CREATE UILayout node + HAS_LAYOUT relationship."""
        layout = result.layout
        props = {
            "layout_id": layout.layout_id,
            "layout_type": layout.layout_type,
            "hierarchy": json.dumps(layout.hierarchy),
            "responsive": layout.responsive,
        }
        props_str = json.dumps(props)
        return (
            f"CREATE (l:UILayout {props_str})\n"
            f"MATCH (s:UISketch {{sketch_id: '{result.sketch.sketch_id}'}})\n"
            f"CREATE (s)-[:HAS_LAYOUT]->(l)"
        )

    def _build_element_nodes_cypher(self, result: UIExtractionResult) -> str:
        """CREATE UIElement nodes + CONTAINS_ELEMENT relationships."""
        if not result.elements:
            return ""

        parts = []
        for elem in result.elements:
            props = {
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

            props_str = json.dumps(props)
            parts.append(
                f"CREATE (e_{elem.element_id}:UIElement {props_str})\n"
                f"MATCH (s:UISketch {{sketch_id: '{result.sketch.sketch_id}'}})\n"
                f"CREATE (s)-[:CONTAINS_ELEMENT {{element_id: '{elem.element_id}'}}]->(e_{elem.element_id})\n"
                f"MATCH (l:UILayout {{layout_id: '{result.layout.layout_id}'}})\n"
                f"CREATE (l)-[:CONTAINS_ELEMENT {{element_id: '{elem.element_id}'}}]->(e_{elem.element_id})"
            )

        return "\n".join(parts)

    async def _execute_cypher(self, cypher: str) -> Dict[str, Any]:
        """Execute Cypher against FalkorDB."""
        try:
            from graph.client import get_falkordb_client

            client = get_falkordb_client()
            response = await client.execute(cypher)
            return {"success": True, "response": response}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def build(self, result: UIExtractionResult) -> Dict[str, Any]:
        """Build and execute graph for a UIExtractionResult."""
        cypher = self.build_cypher(result)
        return await self._execute_cypher(cypher)
