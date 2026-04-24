"""FalkorDB client with connection pooling, parameterized queries, and structured errors."""

import re
import logging
from typing import Any, Dict, List, Optional

import httpx

from core.config import get_settings
from core.pool import get_http_pool
from core.errors import StorageError, ServiceUnavailableError

logger = logging.getLogger(__name__)

ALLOWED_NODE_TYPES = frozenset({
    "Component", "Service", "API", "Endpoint", "Database",
    "Function", "Class", "Module", "File", "Entity",
    "Incident", "Requirement", "Architecture", "Community",
})

ALLOWED_EDGE_TYPES = frozenset({
    "CALLS", "DEFINES", "IMPORTS", "RETURNS", "CONTAINS",
    "INHERITS", "IMPLEMENTS", "DEPENDS_ON", "RELATED_TO",
    "DOCUMENTED_BY", "TRIGGERS", "AFFECTS", "IN_COMMUNITY",
})

MAX_DEPTH = 10
MAX_LIMIT = 10000


def _safe_identifier(value: str, allowed: frozenset, default: str = "Entity") -> str:
    if value in allowed:
        return value
    return default


def _safe_int(value: Any, default: int) -> int:
    try:
        v = int(value)
        return max(1, min(v, MAX_LIMIT))
    except (TypeError, ValueError):
        return default


class FalkorDBClient:
    """Production FalkorDB client with pooling, validation, and structured errors."""

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
        self._pool = get_http_pool()

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

        try:
            response = await self._pool.post(
                f"{self.base_url}/query",
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            logger.error("FalkorDB connection failed: %s:%d", self.host, self.port)
            raise ServiceUnavailableError(
                "FalkorDB unavailable",
                details={"host": self.host, "port": self.port},
                cause=e,
            )
        except httpx.HTTPStatusError as e:
            logger.error("FalkorDB query failed: %s", e.response.text)
            raise StorageError(
                f"FalkorDB query failed: {e.response.status_code}",
                details={"query": query[:200]},
                cause=e,
            )
        except Exception as e:
            logger.exception("FalkorDB unexpected error")
            raise StorageError(
                "FalkorDB operation failed",
                details={"query": query[:200]},
                cause=e,
            )

    async def health_check(self) -> bool:
        """Check FalkorDB connectivity."""
        try:
            resp = await self._pool.get(f"{self.base_url}")
            return resp.status_code in (200, 404)
        except Exception:
            return False

    async def query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Alias for execute() - execute a Cypher query."""
        return await self.execute(query, params)

    async def query_nodes(
        self,
        node_type: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query nodes with type and property filtering."""
        safe_type = _safe_identifier(node_type or "Entity", ALLOWED_NODE_TYPES)
        safe_limit = _safe_int(limit, 100)

        where_parts = ["true"]
        params: Dict[str, Any] = {"limit": safe_limit}

        if properties:
            for i, (k, v) in enumerate(properties.items()):
                safe_key = _safe_identifier(k, ALLOWED_NODE_TYPES, "")
                if not safe_key:
                    continue
                key = f"k{i}"
                where_parts.append(f"n.{safe_key} = ${key}")
                params[key] = v

        where_clause = " AND ".join(where_parts)
        cypher = f"""
        MATCH (n:{safe_type})
        WHERE {where_clause}
        RETURN n
        LIMIT $limit
        """
        result = await self.execute(cypher, params)
        return [r.get("n", {}) for r in result.get("results", [])]

    async def query_relationships(
        self,
        rel_type: Optional[str] = None,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query relationships with filtering."""
        safe_limit = _safe_int(limit, 100)
        params: Dict[str, Any] = {"limit": safe_limit}

        where_parts = ["true"]
        if rel_type:
            safe_type = _safe_identifier(rel_type, ALLOWED_EDGE_TYPES, "RELATED_TO")
            where_parts.append(f"type(r) = $rel_type")
            params["rel_type"] = safe_type
        if source_id:
            where_parts.append("startNode(r).id = $source_id")
            params["source_id"] = source_id
        if target_id:
            where_parts.append("endNode(r).id = $target_id")
            params["target_id"] = target_id

        where_clause = " AND ".join(where_parts)
        cypher = f"""
        MATCH ()-[r]->()
        WHERE {where_clause}
        RETURN r
        LIMIT $limit
        """
        result = await self.execute(cypher, params)
        return [r.get("r", {}) for r in result.get("results", [])]

    async def get_connected(
        self, node_id: str, rel_types: Optional[List[str]] = None, depth: int = 2
    ) -> Dict[str, Any]:
        """Get nodes connected to a given node within depth."""
        safe_depth = min(max(1, depth), MAX_DEPTH)
        rel_filter = ""
        if rel_types:
            safe_types = [_safe_identifier(t, ALLOWED_EDGE_TYPES, "RELATED_TO") for t in rel_types]
            rel_filter = f", {safe_types}" if safe_types else ""

        cypher = f"""
        MATCH path = (n {{id: $id}})-[*1..{safe_depth}]{rel_filter}-(connected)
        RETURN nodes(path) as nodes, relationships(path) as rels
        LIMIT $limit
        """
        result = await self.execute(cypher, {"id": node_id, "limit": MAX_LIMIT})
        return result.get("results", [{}])[0]


_falkordb_client: Optional[FalkorDBClient] = None


def get_falkordb_client() -> FalkorDBClient:
    global _falkordb_client
    if _falkordb_client is None:
        _falkordb_client = FalkorDBClient()
    return _falkordb_client