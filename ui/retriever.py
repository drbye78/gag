"""UI Retriever - Graph-first retrieval for UI sketches."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Allowlists for validated inputs
ALLOWED_ELEMENT_TYPES = {"button", "input", "text", "image", "link", "form", "container", "header", "footer", "navigation", "sidebar", "card", "modal", "table", "list", "icon", "checkbox", "radio", "select", "textarea", "label"}
ALLOWED_LAYOUT_TYPES = {"grid", "flex", "block", "inline", "absolute", "relative", "fixed", "sticky"}
MAX_LIMIT = 1000
MIN_LIMIT = 1


def _validate_element_type(element_type: str) -> None:
    """Validate element_type against allowlist."""
    if element_type not in ALLOWED_ELEMENT_TYPES:
        raise ValueError(f"Invalid element_type: {element_type}. Allowed: {ALLOWED_ELEMENT_TYPES}")


def _validate_limit(limit: int) -> int:
    """Validate and clamp limit to safe bounds."""
    if not isinstance(limit, int):
        raise TypeError(f"limit must be an integer, got {type(limit).__name__}")
    if limit < MIN_LIMIT:
        limit = MIN_LIMIT
    if limit > MAX_LIMIT:
        limit = MAX_LIMIT
    return limit


class UIRetriever:
    async def _execute_cypher(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute Cypher query and return results."""
        try:
            from graph.client import get_falkordb_client
            client = get_falkordb_client()
            result = await client.query(cypher, params or {})
            return result.get("results", [])
        except Exception as e:
            logger.error("UI retriever Cypher failed: %s", e)
            return []

    async def search_by_element_type(self, element_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find sketches containing elements of a given type."""
        _validate_element_type(element_type)
        limit = _validate_limit(limit)
        cypher = (
            "MATCH (s:UISketch)-[:CONTAINS_ELEMENT]->(e:UIElement {element_type: $element_type}) "
            "RETURN s.sketch_id, s.title, s.element_count ORDER BY s.element_count DESC LIMIT $limit"
        )
        return await self._execute_cypher(cypher, {"element_type": element_type, "limit": limit})

    async def find_similar_structural(self, sketch_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find structurally similar sketches by element type overlap."""
        limit = _validate_limit(limit)
        cypher = (
            "MATCH (a:UISketch {sketch_id: $sketch_id})-[:CONTAINS_ELEMENT]->(ae) "
            "MATCH (b:UISketch)-[:CONTAINS_ELEMENT]->(be) "
            "WHERE a.sketch_id <> b.sketch_id AND ae.element_type = be.element_type "
            "WITH b, count(DISTINCT be.element_type) AS overlap "
            "RETURN b.sketch_id, b.title, overlap ORDER BY overlap DESC LIMIT $limit"
        )
        return await self._execute_cypher(cypher, {"sketch_id": sketch_id, "limit": limit})

    async def find_sap_candidates(self, element_type: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find SAP components that support a given element type."""
        _validate_element_type(element_type)
        limit = _validate_limit(limit)
        cypher = (
            "MATCH (sc:SAPComponent) WHERE sc.supported_element_types CONTAINS $element_type "
            "RETURN sc.name, sc.library, sc.complexity ORDER BY sc.complexity ASC LIMIT $limit"
        )
        return await self._execute_cypher(cypher, {"element_type": element_type, "limit": limit})

    async def search_combined(
        self,
        element_types: List[str],
        layout_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find sketches matching element types and optionally layout type.

        If element_types is empty, returns all sketches (fallback to full search).
        """
        limit = _validate_limit(limit)

        for et in element_types:
            _validate_element_type(et)

        if not element_types:
            cypher = (
                "MATCH (s:UISketch) RETURN s.sketch_id, s.title, s.element_count "
                "ORDER BY s.element_count DESC LIMIT $limit"
            )
            return await self._execute_cypher(cypher, {"limit": limit})

        type_conditions = " OR ".join(f"e.element_type = $type_{i}" for i in range(len(element_types)))
        params: Dict[str, Any] = {f"type_{i}": et for i, et in enumerate(element_types)}
        params["limit"] = limit

        cypher = (
            f"MATCH (s:UISketch)-[:CONTAINS_ELEMENT]->(e:UIElement) "
            f"WHERE {type_conditions}"
        )

        if layout_type:
            if layout_type not in ALLOWED_LAYOUT_TYPES:
                raise ValueError(f"Invalid layout_type: {layout_type}. Allowed: {ALLOWED_LAYOUT_TYPES}")
            cypher += " AND s.layout_type = $layout_type"
            params["layout_type"] = layout_type

        cypher += " RETURN s.sketch_id, s.title, s.element_count ORDER BY s.element_count DESC LIMIT $limit"

        return await self._execute_cypher(cypher, params)


_retriever: Optional[UIRetriever] = None


def get_ui_retriever() -> UIRetriever:
    global _retriever
    if _retriever is None:
        _retriever = UIRetriever()
    return _retriever