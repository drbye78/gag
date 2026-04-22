import re
from typing import List, Dict, Any, Optional
import httpx

# Allowlists for parameter validation to prevent Cypher injection
ALLOWED_ENTITY_TYPES = {"Person", "Company", "Document", "UIElement", "UISketch"}
ALLOWED_RELATIONSHIP_TYPES = {
    "CONTAINS", "DEPENDS_ON", "IMPLEMENTS", "EXTENDS", "CALLED_BY",
    "CALLS", "REFERENCES", "HAS_PROPERTY", "LINKED_TO", "RELATED_TO"
}

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_identifier(name: str) -> str:
    """Validate identifier for Cypher label/type — prevents injection."""
    if not name or not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid identifier '{name}': must match ^[A-Za-z_][A-Za-z0-9_]*$")
    return name


# Validate and sanitize integer parameters
def _validate_int(value: Any, name: str, min_val: int = 1, max_val: int = 100) -> int:
    try:
        int_val = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {name}: must be an integer")
    if int_val < min_val or int_val > max_val:
        raise ValueError(f"Invalid {name}: must be between {min_val} and {max_val}")
    return int_val


class EntityCentricRetriever:
    def __init__(self, host: str = "localhost", port: int = 7379):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"

    async def search_by_entity(
        self,
        entity_name: str,
        entity_type: Optional[str] = None,
        depth: int = 2,
        limit: int = 20,
    ) -> Dict[str, Any]:
        if entity_type:
            _safe_identifier(entity_type)
        depth_val = _validate_int(depth, "depth", 1, 10)
        limit_val = _validate_int(limit, "limit", 1, 100)

        if entity_type:
            cypher = """
            MATCH (e:`{lbl}` {name: $name})
            CALL {
                WITH e
                MATCH path = (e)-[r*1..$depth]-(other)
                RETURN path, length(path) as dist
                ORDER BY dist
                LIMIT $limit
            }
            RETURN path, dist
            """.replace("{lbl}", _safe_identifier(entity_type))
            params = {"name": entity_name, "depth": depth_val, "limit": limit_val}
        else:
            cypher = """
            MATCH (e {name: $name})
            CALL {
                WITH e
                MATCH path = (e)-[r*1..$depth]-(other)
                RETURN path, length(path) as dist
                ORDER BY dist
                LIMIT $limit
            }
            RETURN path, dist
            """
            params = {"name": entity_name, "depth": depth_val, "limit": limit_val}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/query",
                    json={"query": cypher, "params": params},
                    timeout=30.0,
                )
                data = resp.json()
        except Exception as e:
            return {"error": str(e), "results": []}

        results = []
        for item in data.get("results", []):
            path = item.get("path", [])
            nodes = []
            for node in path:
                nodes.append(
                    {
                        "name": node.get("name", ""),
                        "type": node.get("type", ""),
                    }
                )

            rels = []
            for rel in item.get("relationships", []):
                rels.append(rel.get("type", ""))

            results.append(
                {
                    "nodes": nodes,
                    "relationships": rels,
                    "distance": item.get("dist", 0),
                }
            )

        return {
            "entity_name": entity_name,
            "entity_type": entity_type,
            "results": results,
            "total": len(results),
        }

    async def search_by_relationship_type(
        self,
        relationship_type: str,
        source_entity: Optional[str] = None,
        target_entity: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        _safe_identifier(relationship_type)
        limit_val = _validate_int(limit, "limit", 1, 100)

        if source_entity and target_entity:
            cypher = """
            MATCH (a {name: $source})-[r:`{rt}`]->(b {name: $target})
            RETURN a, r, b
            LIMIT $limit
            """.replace("{rt}", _safe_identifier(relationship_type))
            params = {"source": source_entity, "target": target_entity, "limit": limit_val}
        elif source_entity:
            cypher = """
            MATCH (a {name: $source})-[r:`{rt}`]->(b)
            RETURN a, r, b
            LIMIT $limit
            """.replace("{rt}", _safe_identifier(relationship_type))
            params = {"source": source_entity, "limit": limit_val}
        else:
            cypher = """
            MATCH (a)-[r:`{rt}`]->(b)
            RETURN a, r, b
            LIMIT $limit
            """.replace("{rt}", _safe_identifier(relationship_type))
            params = {"limit": limit_val}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/query",
                    json={"query": cypher, "params": params},
                    timeout=30.0,
                )
                data = resp.json()
        except Exception as e:
            return {"error": str(e), "results": []}

        results = []
        for item in data.get("results", []):
            results.append(
                {
                    "source": item.get("a", {}).get("name", ""),
                    "target": item.get("b", {}).get("name", ""),
                    "relationship": relationship_type,
                }
            )

        return {
            "relationship_type": relationship_type,
            "results": results,
            "total": len(results),
        }

    async def get_entity_neighborhood(
        self,
        entity_name: str,
        max_distance: int = 2,
    ) -> Dict[str, Any]:
        distance_val = _validate_int(max_distance, "max_distance", 1, 10)
        cypher = """
        MATCH (e {name: $name})
        CALL {
            WITH e
            MATCH path = (e)-[r*1..$max_dist]-(neighbor)
            RETURN neighbor, length(path) as dist
            ORDER BY dist
        }
        RETURN collect({node: neighbor, distance: dist}) as neighborhood
        """

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/query",
                    json={"query": cypher, "params": {"name": entity_name, "max_dist": distance_val}},
                    timeout=30.0,
                )
                data = resp.json()
        except Exception as e:
            return {"error": str(e), "neighbors": []}

        neighbors = []
        for item in data.get("results", []):
            neighborhood = item.get("neighborhood", [])
            for n in neighborhood:
                node = n.get("node", {})
                neighbors.append(
                    {
                        "name": node.get("name", ""),
                        "type": node.get("type", ""),
                        "distance": n.get("distance", 0),
                    }
                )

        return {
            "entity_name": entity_name,
            "neighbors": neighbors,
            "total": len(neighbors),
        }


_entity_retriever: Optional[EntityCentricRetriever] = None


def get_entity_centric_retriever() -> EntityCentricRetriever:
    global _entity_retriever
    if _entity_retriever is None:
        _entity_retriever = EntityCentricRetriever()
    return _entity_retriever
