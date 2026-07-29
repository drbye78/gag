"""Graph builder for UI sketch understanding - constructs FalkorDB graph nodes and relationships."""

import json
import re
from typing import Any, Dict, Tuple

from ui.models import UIExtractionResult


def _escape_cypher_string(value: str) -> str:
    """Escape string for Cypher to prevent injection."""
    if not isinstance(value, str):
        value = str(value)
    if not re.match(r'^[A-Za-z0-9_\-]+$', value):
        raise ValueError(f"Invalid characters in identifier: {value!r}")
    return value.replace("\\", "\\\\").replace("'", "\\'")


class UIGraphBuilder:
    """Builds Cypher queries for UI sketch graph construction."""

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
        """Build and execute graph for a UIExtractionResult.

        Uses parameterized Cypher to prevent injection.
        """
        from ui.issue_tracker import get_issue_tracker
        from ui.pattern_matcher import get_pattern_matcher

        matcher = get_pattern_matcher()
        tracker = get_issue_tracker()
        matches = matcher.match_patterns(result)

        sketch = result.sketch
        layout = result.layout

        # Build parameterized Cypher for sketch node
        sketch_props = {
            "sketch_id": sketch.sketch_id,
            "title": sketch.title,
            "source_url": sketch.source_url,
            "format_type": sketch.format_type,
            "element_count": len(result.elements),
            "source_type_confidence": result.source_type_confidence,
        }
        if sketch.page_type:
            sketch_props["page_type"] = sketch.page_type

        cypher_parts = []
        params = {"sketch_props": sketch_props}

        cypher_parts.append(
            "CREATE (s:UISketch $sketch_props)"
        )

        # Build parameterized Cypher for layout
        layout_props = {
            "layout_id": layout.layout_id,
            "layout_type": layout.layout_type,
            "hierarchy": json.dumps(layout.hierarchy),
            "responsive": layout.responsive,
        }
        params["layout_props"] = layout_props
        params["sketch_id"] = sketch.sketch_id
        params["layout_id"] = layout.layout_id

        cypher_parts.append(
            "CREATE (l:UILayout $layout_props) "
            "WITH s, l "
            "MATCH (s:UISketch {sketch_id: $sketch_id}) "
            "CREATE (s)-[:HAS_LAYOUT]->(l)"
        )

        # Build parameterized Cypher for elements
        for elem in result.elements:
            elem_props = {
                "element_id": elem.element_id,
                "element_type": elem.element_type,
                "confidence": elem.confidence,
            }
            if elem.label is not None:
                elem_props["label"] = elem.label
            if elem.position:
                elem_props["position"] = json.dumps(elem.position)

            param_key = f"elem_props_{elem.element_id}"
            params[param_key] = elem_props

            cypher_parts.append(
                f"CREATE (e_{elem.element_id}:UIElement ${param_key}) "
                f"WITH s, l, e_{elem.element_id} "
                f"MATCH (s:UISketch {{sketch_id: $sketch_id}}) "
                f"CREATE (s)-[:CONTAINS_ELEMENT]->(e_{elem.element_id}) "
                f"MATCH (l:UILayout {{layout_id: $layout_id}}) "
                f"CREATE (l)-[:CONTAINS_ELEMENT]->(e_{elem.element_id})"
            )

        # Add pattern matches
        for pattern in matches:
            pattern_props = {
                "pattern_id": pattern.pattern_id,
                "pattern_name": pattern.pattern_name,
                "description": pattern.description,
                "complexity": pattern.complexity,
            }
            param_key = f"pattern_props_{pattern.pattern_id}"
            params[param_key] = pattern_props

            cypher_parts.append(
                f"MERGE (p:UIPattern {{pattern_id: $pattern_id_{pattern.pattern_id}}}) "
                f"SET p = ${param_key} "
                f"WITH s, p "
                f"MATCH (s:UISketch {{sketch_id: $sketch_id}}) "
                f"MERGE (s)-[:MATCHES_PATTERN]->(p)"
            )
            params[f"pattern_id_{pattern.pattern_id}"] = pattern.pattern_id

        full_cypher = "\n".join(cypher_parts)

        try:
            from graph.client import get_falkordb_client
            client = get_falkordb_client()
            response = await client.execute(full_cypher, params)
            return {"success": True, "response": response}
        except Exception as e:
            return {"success": False, "error": str(e)}
