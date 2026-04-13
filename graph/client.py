"""FalkorDB graph database client with parameterized queries."""

import re
from typing import Any, Dict, List, Optional

import httpx

from core.config import get_settings

# Allowlisted node/edge types to prevent Cypher injection
ALLOWED_NODE_TYPES = frozenset({
    "Component", "Service", "API", "Endpoint", "Database",
    "Function", "Class", "Module", "File", "Entity",
    "Incident", "Requirement", "Architecture",
})

ALLOWED_EDGE_TYPES = frozenset({
    "CALLS", "DEFINES", "IMPORTS", "RETURNS", "CONTAINS",
    "INHERITS", "IMPLEMENTS", "DEPENDS_ON", "RELATED_TO",
    "DOCUMENTED_BY", "TRIGGERS", "AFFECTS",
})

_MAX_DEPTH = 10
_MAX_LIMIT = 10000


def _safe_identifier(value: str, allowed: frozenset, default: str = "Entity") -> str:
    """Validate that a value is a safe Cypher identifier."""
    if value in allowed:
        return value
    # Allow alphanumeric + underscore only
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", value):
        return value
    return default


def _safe_int(value: Any, default: int) -> int:
    """Safely convert to int with bounds checking."""
    try:
        v = int(value)
        return max(1, min(v, _MAX_LIMIT))
    except (TypeError, ValueError):
        return default


class FalkorDBClient:
    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 7379,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        settings = get_settings()
        self.host = host or settings.falkordb_host
        self.port = port
        self.username = username or settings.falkordb_user
        self.password = password or settings.falkordb_pass
        self.base_url = f"http://{self.host}:{self.port}"

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.username and self.password:
            import base64
            auth = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers["Authorization"] = f"Basic {auth}"
        return headers

    async def execute(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        payload = {"query": query}
        if params:
            payload["params"] = params

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/query", headers=self._get_headers(), json=payload
            )
            response.raise_for_status()
            return response.json()

    async def add_node(
        self, node_type: str, name: str, properties: Optional[Dict[str, Any]] = None
    ) -> str:
        safe_type = _safe_identifier(node_type, ALLOWED_NODE_TYPES)
        props = properties or {}
        props["name"] = name
        props["type"] = safe_type

        query = "CREATE (n:$node_type $props) RETURN id(n)"
        result = await self.execute(
            query, {"node_type": safe_type, "props": props}
        )

        if result.get("results"):
            return result["results"][0][0]
        raise RuntimeError("Failed to create node")

    async def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> str:
        safe_type = _safe_identifier(edge_type, ALLOWED_EDGE_TYPES, "RELATED_TO")
        props = properties or {}
        props["type"] = safe_type

        query = f"""
        MATCH (a), (b)
        WHERE id(a) = $source AND id(b) = $target
        CREATE (a)-[r:{safe_type} $props]->(b)
        RETURN id(r)
        """
        result = await self.execute(
            query, {"source": int(source_id), "target": int(target_id), "props": props}
        )

        if result.get("results"):
            return result["results"][0][0]
        raise RuntimeError("Failed to create edge")

    async def query_subgraph(
        self, node_type: str, limit: int = 100, depth: int = 2
    ) -> Dict[str, Any]:
        safe_type = _safe_identifier(node_type, ALLOWED_NODE_TYPES)
        safe_depth = _safe_int(depth, 2)
        safe_limit = _safe_int(limit, 100)

        query = f"""
        MATCH (a:`{safe_type}`)-[r*1..{safe_depth}]->(b)
        RETURN a, r, b
        LIMIT {safe_limit}
        """
        return await self.execute(query)

    async def find_related(
        self, node_id: str, edge_types: Optional[List[str]] = None, limit: int = 100
    ) -> Dict[str, Any]:
        edge_filter = ""
        if edge_types:
            safe_types = [_safe_identifier(e, ALLOWED_EDGE_TYPES, "RELATED_TO") for e in edge_types]
            edge_str = "|".join(f"`{e}`" for e in safe_types)
            edge_filter = f":{edge_str}"

        safe_limit = _safe_int(limit, 100)
        safe_node_id = int(node_id)

        query = f"""
        MATCH (a)-[r{edge_filter}]->(b)
        WHERE id(a) = $node_id
        RETURN b, r
        LIMIT {safe_limit}
        """
        return await self.execute(query, {"node_id": safe_node_id})


_default_client: Optional[FalkorDBClient] = None


def get_falkordb_client() -> FalkorDBClient:
    global _default_client
    if _default_client is None:
        _default_client = FalkorDBClient()
    return _default_client
