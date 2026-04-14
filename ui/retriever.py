"""UI Retriever - Graph-first retrieval for UI sketches."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class UIRetriever:
    async def _execute_cypher(self, cypher: str) -> List[Dict[str, Any]]:
        """Execute Cypher query and return results."""
        try:
            from graph.client import get_falkordb_client
            client = get_falkordb_client()
            result = await client.query(cypher)
            return result.get("results", [])
        except Exception as e:
            logger.error("UI retriever Cypher failed: %s", e)
            return []

    async def search_by_element_type(self, element_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find sketches containing elements of a given type."""
        cypher = (
            f"MATCH (s:UISketch)-[:CONTAINS_ELEMENT]->(e:UIElement {{element_type: '{element_type}'}}) "
            f"RETURN s.sketch_id, s.title, s.element_count ORDER BY s.element_count DESC LIMIT {limit}"
        )
        return await self._execute_cypher(cypher)

    async def find_similar_structural(self, sketch_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find structurally similar sketches by element type overlap."""
        cypher = (
            f"MATCH (a:UISketch {{sketch_id: '{sketch_id}'}})-[:CONTAINS_ELEMENT]->(ae) "
            f"MATCH (b:UISketch)-[:CONTAINS_ELEMENT]->(be) "
            f"WHERE a.sketch_id <> b.sketch_id AND ae.element_type = be.element_type "
            f"WITH b, count(DISTINCT be.element_type) AS overlap "
            f"RETURN b.sketch_id, b.title, overlap ORDER BY overlap DESC LIMIT {limit}"
        )
        return await self._execute_cypher(cypher)

    async def find_sap_candidates(self, element_type: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find SAP components that support a given element type."""
        cypher = (
            f"MATCH (sc:SAPComponent) WHERE sc.supported_element_types CONTAINS '{element_type}' "
            f"RETURN sc.name, sc.library, sc.complexity ORDER BY sc.complexity ASC LIMIT {limit}"
        )
        return await self._execute_cypher(cypher)

    async def search_combined(self, element_types: List[str], layout_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Find sketches matching element types and optionally layout type."""
        type_filters = " OR ".join(f"e.element_type = '{t}'" for t in element_types)
        cypher = f"MATCH (s:UISketch)-[:CONTAINS_ELEMENT]->(e:UIElement) WHERE {type_filters}"

        if layout_type:
            cypher += f" AND s.layout_type = '{layout_type}'"

        cypher += f" RETURN s.sketch_id, s.title, s.element_count ORDER BY s.element_count DESC LIMIT {limit}"

        return await self._execute_cypher(cypher)


_retriever: Optional[UIRetriever] = None


def get_ui_retriever() -> UIRetriever:
    global _retriever
    if _retriever is None:
        _retriever = UIRetriever()
    return _retriever
