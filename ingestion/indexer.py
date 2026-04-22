"""
Indexer - Vector and graph indexing.

Provides VectorIndexer for Qdrant and GraphIndexer
for FalkorDB with batched operations and connection pooling.
"""

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class IndexTarget(str, Enum):
    QDRANT = "qdrant"
    FALKORDB = "falkordb"


@dataclass
class IndexerResult:
    target: str
    indexed_count: int
    took_ms: int
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class VectorIndexer:
    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 6333,
        collection: str = "documents",
    ):
        self.host = host or os.getenv("QDRANT_HOST", "localhost")
        self.port = port
        self.collection = collection
        self.base_url = f"http://{self.host}:{self.port}"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=10.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def create_collection(
        self,
        vector_size: int = 1536,
        distance: str = "Cosine",
    ) -> bool:
        payload = {
            "vectors": {
                "size": vector_size,
                "distance": distance,
            }
        }

        try:
            client = await self._get_client()
            resp = await client.put(
                f"{self.base_url}/collections/{self.collection}",
                json=payload,
                timeout=30.0,
            )
            return resp.status_code in (200, 201)
        except Exception as e:
            logger.error("Failed to create collection %s: %s", self.collection, e)
            return False

    async def index_chunks(
        self,
        chunks: List[Dict[str, Any]],
        source_tag: str = "default",
    ) -> IndexerResult:
        start = time.time()
        errors = []

        if not chunks:
            return IndexerResult(
                target="qdrant",
                indexed_count=0,
                took_ms=0,
                errors=[],
                metadata={},
            )

        points = []
        for chunk in chunks:
            point = {
                "id": chunk.get("id", str(uuid.uuid4())),
                "vector": chunk.get("embedding", []),
                "payload": {
                    "content": chunk.get("content", ""),
                    "source_id": chunk.get("source_id", ""),
                    "source_type": chunk.get("source_type", "document"),
                    "chunk_index": chunk.get("chunk_index", 0),
                    "metadata": chunk.get("metadata", {}),
                    "source_tag": source_tag,
                },
            }
            points.append(point)

        client = await self._get_client()
        batch_size = 100
        indexed = 0
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            try:
                resp = await client.put(
                    f"{self.base_url}/collections/{self.collection}/points",
                    json={"points": batch},
                    timeout=60.0,
                )
                if resp.status_code in (200, 201):
                    indexed += len(batch)
                else:
                    errors.append(
                        f"Batch {i // batch_size} failed: HTTP {resp.status_code}"
                    )
                    logger.error(
                        "Qdrant batch %d failed: HTTP %d",
                        i // batch_size,
                        resp.status_code,
                    )
            except Exception as e:
                errors.append(f"Batch {i // batch_size} error: {e}")
                logger.error("Qdrant batch %d error: %s", i // batch_size, e)

        took = int((time.time() - start) * 1000)
        return IndexerResult(
            target="qdrant",
            indexed_count=indexed,
            took_ms=took,
            errors=errors,
            metadata={"total_chunks": len(chunks), "source_tag": source_tag},
        )

    async def index_with_entities(
        self,
        chunks: List[Dict[str, Any]],
        entities: List[Dict[str, Any]],
        source_tag: str = "default",
    ) -> IndexerResult:
        start = time.time()
        errors = []

        if not chunks:
            return IndexerResult(
                target="qdrant",
                indexed_count=0,
                took_ms=0,
                errors=[],
                metadata={},
            )

        points = []
        for chunk, entity in zip(chunks, entities):
            point = {
                "id": chunk.get("id", str(uuid.uuid4())),
                "vector": chunk.get("embedding", []),
                "payload": {
                    "content": chunk.get("content", ""),
                    "source_id": chunk.get("source_id", ""),
                    "source_type": chunk.get("source_type", "document"),
                    "chunk_index": chunk.get("chunk_index", 0),
                    "metadata": chunk.get("metadata", {}),
                    "source_tag": source_tag,
                    "entity_type": entity.get("entity_type", "unknown"),
                    "entity_name": entity.get("name", ""),
                    "language": entity.get("language", ""),
                    "start_line": entity.get("start_line", 0),
                    "end_line": entity.get("end_line", 0),
                },
            }
            points.append(point)

        client = await self._get_client()
        batch_size = 100
        indexed = 0
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            try:
                resp = await client.put(
                    f"{self.base_url}/collections/{self.collection}/points",
                    json={"points": batch},
                    timeout=60.0,
                )
                if resp.status_code in (200, 201):
                    indexed += len(batch)
                else:
                    errors.append(f"Batch {i // batch_size} failed: HTTP {resp.status_code}")
            except Exception as e:
                errors.append(f"Batch {i // batch_size} error: {e}")

        took = int((time.time() - start) * 1000)
        return IndexerResult(
            target="qdrant",
            indexed_count=indexed,
            took_ms=took,
            errors=errors,
            metadata={
                "total_chunks": len(chunks),
                "source_tag": source_tag,
                "with_entities": True,
            },
        )

    async def delete_by_source(
        self,
        source_id: str,
    ) -> IndexerResult:
        start = time.time()

        try:
            client = await self._get_client()
            resp = await client.post(
                f"{self.base_url}/collections/{self.collection}/points/delete",
                json={
                    "filter": {
                        "must": [
                            {"key": "source_id", "match": {"value": source_id}}
                        ]
                    }
                },
                timeout=30.0,
            )
            took = int((time.time() - start) * 1000)
            return IndexerResult(
                target="qdrant",
                indexed_count=0,  # Qdrant delete doesn't return count reliably
                took_ms=took,
                errors=[],
                metadata={"deleted_source": source_id},
            )
        except Exception as e:
            return IndexerResult(
                target="qdrant",
                indexed_count=0,
                took_ms=0,
                errors=[str(e)],
                metadata={},
            )

    async def get_collection_info(self) -> Dict[str, Any]:
        try:
            client = await self._get_client()
            resp = await client.get(
                f"{self.base_url}/collections/{self.collection}",
                timeout=10.0,
            )
            if resp.status_code == 200:
                return resp.json()
            return {}
        except Exception:
            return {}


class EdgeType(str, Enum):
    CALLS = "CALLS"
    DEFINES = "DEFINES"
    IMPORTS = "IMPORTS"
    RETURNS = "RETURNS"
    CONTAINS = "CONTAINS"
    INHERITS = "INHERITS"
    IMPLEMENTS = "IMPLEMENTS"
    DEPENDS_ON = "DEPENDS_ON"
    RELATED_TO = "RELATED_TO"
    DOCUMENTED_BY = "DOCUMENTED_BY"


class NodeType(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    FILE = "file"
    COMPONENT = "component"
    SERVICE = "service"
    API = "api"
    INTERFACE = "interface"


# Allowlists for Cypher injection prevention
ALLOWED_NODE_TYPES = {
    "Entity",
    "function",
    "class",
    "module",
    "file",
    "component",
    "service",
    "api",
    "interface",
}

ALLOWED_EDGE_TYPES = {
    "RELATED_TO",
    "CALLS",
    "DEFINES",
    "IMPORTS",
    "RETURNS",
    "CONTAINS",
    "INHERITS",
    "IMPLEMENTS",
    "DEPENDS_ON",
    "DOCUMENTED_BY",
}


def _validate_node_type(node_type: str) -> str:
    """Validate node_type against allowlist to prevent Cypher injection."""
    if node_type not in ALLOWED_NODE_TYPES:
        raise ValueError(f"Invalid node_type: {node_type}")
    return node_type


def _validate_edge_type(edge_type: str) -> str:
    """Validate edge_type against allowlist to prevent Cypher injection."""
    validated = edge_type.upper()
    if validated not in ALLOWED_EDGE_TYPES:
        raise ValueError(f"Invalid edge_type: {edge_type}")
    return validated


class GraphIndexer:
    """FalkorDB graph indexer with batched Cypher operations."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 7379,
    ):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self._client: Optional[httpx.AsyncClient] = None
        self._node_cache: Dict[str, Dict[str, Any]] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _execute_cypher(self, query: str, params: Dict[str, Any]) -> bool:
        """Execute a single Cypher query."""
        client = await self._get_client()
        resp = await client.post(
            f"{self.base_url}/query",
            json={"query": query, "params": params},
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.status_code in (200, 201)

    async def index_nodes(
        self,
        nodes: List[Dict[str, Any]],
    ) -> IndexerResult:
        start = time.time()
        errors = []

        if not nodes:
            return IndexerResult(
                target="falkordb",
                indexed_count=0,
                took_ms=0,
                errors=[],
                metadata={},
            )

        # Batch all nodes into a single UNWIND query
        batch_size = 500
        indexed = 0

        for i in range(0, len(nodes), batch_size):
            batch = nodes[i : i + batch_size]
            try:
                # Build UNWIND query for batch insertion
                node_data = [
                    {
                        "id": n.get("id", str(uuid.uuid4())),
                        "label": n.get("node_type", "entity"),
                        "props": n.get("properties", {}),
                    }
                    for n in batch
                ]

                cypher = """
                UNWIND $nodes AS node
                CALL db.labels() YIELD label
                WITH node
                CALL apoc.create.node([node.label], node.props) YIELD node AS n
                RETURN count(n) AS count
                """
                # Fallback to simpler MERGE approach since FalkorDB may not have APOC
                cypher = """
                UNWIND $nodes AS node
                MERGE (n:Entity {id: node.id})
                SET n += node.props
                WITH n, node
                CALL apoc.create.addLabels(n, [node.label]) YIELD node AS labeled
                RETURN count(labeled) AS count
                """

                params = {"nodes": node_data}

                client = await self._get_client()
                resp = await client.post(
                    f"{self.base_url}/query",
                    json={"query": cypher, "params": params},
                    timeout=60.0,
                )

                if resp.status_code in (200, 201):
                    indexed += len(batch)
                    for n in batch:
                        nid = n.get("id", "")
                        if nid:
                            self._node_cache[nid] = n
                else:
                    # Fallback: insert individually
                    for node in batch:
                        node_id = node.get("id", str(uuid.uuid4()))
                        validated_type = _validate_node_type(node.get("node_type", "Entity"))
                        cypher = """
                        MERGE (n:Entity {id: $id})
                        SET n += $props
                        """
                        try:
                            await self._execute_cypher(
                                cypher,
                                {"id": node_id, "props": node.get("properties", {})},
                            )
                            indexed += 1
                            self._node_cache[node_id] = node
                        except Exception as e:
                            errors.append(f"Node {node_id} error: {e}")

            except Exception as e:
                # Final fallback: individual insertions
                logger.warning("Batch node insert failed, falling back: %s", e)
                for node in batch:
                    node_id = node.get("id", str(uuid.uuid4()))
                    validated_type = _validate_node_type(node.get("node_type", "Entity"))
                    cypher = """
                    MERGE (n:Entity {id: $id})
                    SET n += $props
                    """
                    try:
                        await self._execute_cypher(
                            cypher,
                            {"id": node_id, "props": node.get("properties", {})},
                        )
                        indexed += 1
                        self._node_cache[node_id] = node
                    except Exception as e2:
                        errors.append(f"Node {node_id} error: {e2}")

        took = int((time.time() - start) * 1000)
        return IndexerResult(
            target="falkordb",
            indexed_count=indexed,
            took_ms=took,
            errors=errors,
            metadata={"total_nodes": len(nodes)},
        )

    async def index_edges(
        self,
        edges: List[Dict[str, Any]],
    ) -> IndexerResult:
        start = time.time()
        errors = []

        if not edges:
            return IndexerResult(
                target="falkordb",
                indexed_count=0,
                took_ms=0,
                errors=[],
                metadata={},
            )

        # Batch edges into UNWIND queries
        batch_size = 200
        indexed = 0

        for i in range(0, len(edges), batch_size):
            batch = edges[i : i + batch_size]
            try:
                edge_data = [
                    {
                        "source_id": e.get("source_id"),
                        "target_id": e.get("target_id"),
                        "rel_type": e.get("edge_type", "RELATED_TO"),
                        "props": e.get("properties", {}),
                    }
                    for e in batch
                ]

                cypher = """
                UNWIND $edges AS edge
                MATCH (a {id: edge.source_id})
                MATCH (b {id: edge.target_id})
                CALL apoc.create.relationship(a, edge.rel_type, edge.props, b) YIELD rel
                RETURN count(rel) AS count
                """

                params = {"edges": edge_data}

                client = await self._get_client()
                resp = await client.post(
                    f"{self.base_url}/query",
                    json={"query": cypher, "params": params},
                    timeout=60.0,
                )

                if resp.status_code in (200, 201):
                    indexed += len(batch)
                else:
                    # Fallback: individual edge creation
                    for edge in batch:
                        rel_type = _validate_edge_type(edge.get("edge_type", "RELATED_TO"))
                        cypher = """
                        MATCH (a {id: $source_id})
                        MATCH (b {id: $target_id})
                        MERGE (a)-[r:RELATED_TO]->(b)
                        SET r += $props
                        """
                        try:
                            await self._execute_cypher(
                                cypher,
                                {
                                    "source_id": edge.get("source_id"),
                                    "target_id": edge.get("target_id"),
                                    "props": edge.get("properties", {}),
                                },
                            )
                            indexed += 1
                        except Exception as e:
                            errors.append(f"Edge error: {e}")

            except Exception as e:
                logger.warning("Batch edge insert failed, falling back: %s", e)
                for edge in batch:
                    rel_type = _validate_edge_type(edge.get("edge_type", "RELATED_TO"))
                    cypher = """
                    MATCH (a {id: $source_id})
                    MATCH (b {id: $target_id})
                    MERGE (a)-[r:RELATED_TO]->(b)
                    SET r += $props
                    """
                    try:
                        await self._execute_cypher(
                            cypher,
                            {
                                "source_id": edge.get("source_id"),
                                "target_id": edge.get("target_id"),
                                "props": edge.get("properties", {}),
                            },
                        )
                        indexed += 1
                    except Exception as e:
                        errors.append(f"Edge error: {e}")

        took = int((time.time() - start) * 1000)
        return IndexerResult(
            target="falkordb",
            indexed_count=indexed,
            took_ms=took,
            errors=errors,
            metadata={"total_edges": len(edges)},
        )

    async def index_architecture(
        self,
        components: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
    ) -> IndexerResult:
        node_result = await self.index_nodes(components)
        edge_result = await self.index_edges(relationships)

        return IndexerResult(
            target="falkordb",
            indexed_count=node_result.indexed_count + edge_result.indexed_count,
            took_ms=node_result.took_ms + edge_result.took_ms,
            errors=node_result.errors + edge_result.errors,
            metadata={
                "components": len(components),
                "relationships": len(relationships),
            },
        )

    async def index_code_entities(
        self,
        entities: List[Dict[str, Any]],
    ) -> IndexerResult:
        nodes = []
        edges = []

        for entity in entities:
            node_id = entity.get("id", "")
            node_type = entity.get("type", "entity")
            source_file = entity.get("file_path", "")

            nodes.append(
                {
                    "id": node_id,
                    "node_type": node_type,
                    "properties": {
                        "name": entity.get("name", ""),
                        "file_path": source_file,
                        "line": entity.get("line", 0),
                        "signature": entity.get("signature", ""),
                        "docstring": entity.get("docstring", ""),
                        "language": entity.get("language", ""),
                    },
                }
            )

            if source_file:
                file_node_id = f"file:{source_file}"
                self._node_cache[file_node_id] = {"type": "file", "path": source_file}
                edges.append(
                    {
                        "source_id": node_id,
                        "target_id": file_node_id,
                        "edge_type": "CONTAINS",
                        "properties": {},
                    }
                )

            for ref in entity.get("calls", []) or []:
                edges.append(
                    {
                        "source_id": node_id,
                        "target_id": ref,
                        "edge_type": "CALLS",
                        "properties": {},
                    }
                )

            for imp in entity.get("imports", []) or []:
                edges.append(
                    {
                        "source_id": node_id,
                        "target_id": imp,
                        "edge_type": "IMPORTS",
                        "properties": {},
                    }
                )

            for base in entity.get("inherits", []) or []:
                edges.append(
                    {
                        "source_id": node_id,
                        "target_id": base,
                        "edge_type": "INHERITS",
                        "properties": {},
                    }
                )

        node_result = await self.index_nodes(nodes)
        edge_result = await self.index_edges(edges)

        return IndexerResult(
            target="falkordb",
            indexed_count=node_result.indexed_count + edge_result.indexed_count,
            took_ms=node_result.took_ms + edge_result.took_ms,
            errors=node_result.errors + edge_result.errors,
            metadata={
                "nodes": len(nodes),
                "edges": len(edges),
            },
        )


_vector_indexer: Optional[VectorIndexer] = None
_graph_indexer: Optional[GraphIndexer] = None


def get_vector_indexer() -> VectorIndexer:
    global _vector_indexer
    if _vector_indexer is None:
        _vector_indexer = VectorIndexer()
    return _vector_indexer


def get_graph_indexer() -> GraphIndexer:
    global _graph_indexer
    if _graph_indexer is None:
        _graph_indexer = GraphIndexer()
    return _graph_indexer
