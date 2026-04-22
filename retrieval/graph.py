"""
Graph Retriever - Knowledge graph retrieval from FalkorDB.
 
Queries graph relationships via Cypher with depth control
and multi-hop traversal support.
"""

import re
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import httpx

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_identifier(name: str) -> str:
    """Validate identifier for Cypher label/type — prevents injection."""
    if not name or not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid identifier '{name}': must match ^[A-Za-z_][A-Za-z0-9_]*$")
    return name


class QueryType(str, Enum):
    DIRECT = "direct"
    ONE_HOP = "one_hop"
    MULTI_HOP = "multi_hop"
    RELATIONSHIP = "relationship"
    CAUSAL = "causal"


# Whitelists for Cypher injection prevention
ALLOWED_NODE_TYPES = {"Person", "Organization", "Document", "Entity", "Service", "Component", "Repository"}
ALLOWED_EDGE_TYPES = {"IMPORTS", "CALLS", "DEPENDS_ON", "CONTAINS", "PROVIDES", "USES"}


class GraphRetriever:
    def __init__(self, host: str = "localhost", port: int = 7379):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"

    async def search(
        self,
        query: str,
        node_types: Optional[List[str]] = None,
        edge_types: Optional[List[str]] = None,
        limit: int = 100,
        depth: int = 2,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)

        if depth == 1:
            cypher = """
            MATCH (a)-[r]->(b) 
            WHERE a.name CONTAINS $query OR b.name CONTAINS $query
            RETURN a, r, b
            LIMIT $limit
            """
            params = {"query": query, "limit": limit}
        else:
            cypher = """
            MATCH path = (a)-[r*1..$depth]->(b)
            WHERE a.name CONTAINS $query
            RETURN path, length(path) as path_length
            ORDER BY path_length
            LIMIT $limit
            """
            params = {"query": query, "depth": depth, "limit": limit}

        if edge_types:
            for et in edge_types:
                _safe_identifier(et)
            edge_filter = " OR ".join([f"type(r) = '{_safe_identifier(e)}'" for e in edge_types])
            cypher = cypher.replace("WHERE", f"WHERE ({edge_filter}) AND")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/query",
                    json={"query": cypher, "params": params},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            data = {"results": [], "error": str(e)}

        took = int(time.time() * 1000) - start

        return {
            "source": "graph",
            "query": query,
            "results": data.get("results", []),
            "total": len(data.get("results", [])),
            "took_ms": took,
        }

    async def multi_hop_search(
        self,
        query: str,
        max_hops: int = 3,
        edge_types: Optional[List[str]] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)
        all_results = []

        for hop in range(1, max_hops + 1):
            hop_results = await self.search(
                query=query,
                edge_types=edge_types,
                limit=limit,
                depth=hop,
            )
            all_results.extend(hop_results.get("results", []))

        unique_results = self._deduplicate_results(all_results)

        took = int(time.time() * 1000) - start

        return {
            "source": "graph",
            "query": query,
            "results": unique_results[:limit],
            "total": len(unique_results),
            "max_hops": max_hops,
            "took_ms": took,
        }

    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        seen: Set[str] = set()
        unique = []

        for result in results:
            key = self._get_result_key(result)
            if key not in seen:
                seen.add(key)
                unique.append(result)

        return unique

    def _get_result_key(self, result: Dict) -> str:
        if isinstance(result, dict):
            path = result.get("path", [])
            if path:
                nodes = [n.get("name", str(n)) for n in path]
                return "|".join(nodes)
        return str(result)

    async def find_relationships(
        self,
        source: str,
        target: str,
        max_depth: int = 4,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)

        cypher = """
        MATCH path = (a)-[r*1..$max_depth]->(b)
        WHERE a.name = $source AND b.name = $target
        RETURN path, length(path) as hops
        ORDER BY hops
        LIMIT 10
        """
        params = {"source": source, "target": target, "max_depth": max_depth}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/query",
                    json={
                        "query": cypher,
                        "params": {"source": source, "target": target},
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            data = {"results": [], "error": str(e)}

        took = int(time.time() * 1000) - start

        paths = []
        for result in data.get("results", []):
            path = result.get("path", [])
            hops = result.get("hops", 0)
            paths.append(
                {
                    "nodes": [n.get("name", "") for n in path],
                    "edges": [e.get("type", "") for e in path],
                    "hops": hops,
                }
            )

        return {
            "source": "graph",
            "source_node": source,
            "target_node": target,
            "paths": paths,
            "total": len(paths),
            "took_ms": took,
        }

    async def get_node_by_name(
        self,
        name: str,
        node_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)

        if node_type:
            if node_type not in ALLOWED_NODE_TYPES:
                raise ValueError(f"Invalid node_type: {node_type}. Allowed: {ALLOWED_NODE_TYPES}")
            cypher = """
            MATCH (n:`$node_type`)
            WHERE n.name = $name
            RETURN n
            """
            params = {"name": name, "node_type": node_type}
        else:
            cypher = """
            MATCH (n)
            WHERE n.name = $name
            RETURN n
            """
            params = {"name": name}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/query",
                    json={"query": cypher, "params": params},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            data = {"results": [], "error": str(e)}

        took = int(time.time() * 1000) - start

        return {
            "source": "graph",
            "name": name,
            "node": data.get("results", [{}])[0].get("n", {}),
            "took_ms": took,
        }

    async def get_connected_nodes(
        self,
        node_name: str,
        edge_type: Optional[str] = None,
        direction: str = "outgoing",
        depth: int = 1,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)

        if edge_type and edge_type not in ALLOWED_EDGE_TYPES:
            raise ValueError(f"Invalid edge_type: {edge_type}. Allowed: {ALLOWED_EDGE_TYPES}")
        if edge_type:
            _safe_identifier(edge_type)
        if depth < 1 or depth > 10:
            raise ValueError(f"Invalid depth: {depth}. Must be between 1 and 10")

        if direction == "outgoing":
            rel_pattern = (
                f"[r:`{edge_type}`*1..{depth}]->" if edge_type else f"[r*1..{depth}]->"
            )
        elif direction == "incoming":
            rel_pattern = (
                f"<-[r:`{edge_type}`*1..{depth}]" if edge_type else f"<-[r*1..{depth}]"
            )
        else:
            rel_pattern = (
                f"[r:`{edge_type}`*1..{depth}]" if edge_type else f"[r*1..{depth}]"
            )

        cypher = f"""
        MATCH (a {{name: $name }}){rel_pattern}(b)
        RETURN a, b, r
        LIMIT 100
        """

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/query",
                    json={"query": cypher, "params": {"name": node_name}},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            data = {"results": [], "error": str(e)}

        took = int(time.time() * 1000) - start

        connected = []
        for result in data.get("results", []):
            b = result.get("b", {})
            r = result.get("r", {})
            connected.append(
                {
                    "node": b,
                    "relationship": r.get("type", "") if isinstance(r, dict) else "",
                }
            )

        return {
            "source": "graph",
            "query_node": node_name,
            "connected": connected,
            "total": len(connected),
            "took_ms": took,
        }

    async def get_entity_dependencies(
        self,
        entity_name: str,
    ) -> Dict[str, Any]:
        return await self.get_connected_nodes(
            node_name=entity_name,
            edge_type="IMPORTS",
            direction="incoming",
        )

    async def get_entity_usage(
        self,
        entity_name: str,
    ) -> Dict[str, Any]:
        return await self.get_connected_nodes(
            node_name=entity_name,
            edge_type="CALLS",
            direction="outgoing",
        )

    async def get_related(
        self, node_id: str, edge_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        return await self.search(node_id, edge_types=edge_types)


def get_graph_retriever() -> GraphRetriever:
    return GraphRetriever()
