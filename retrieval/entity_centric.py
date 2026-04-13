from typing import List, Dict, Any, Optional
import httpx


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
            cypher = f"""
            MATCH (e:`{entity_type}` {{name: $name}})
            CALL {{
                WITH e
                MATCH path = (e)-[r*1..{depth}]-(other)
                RETURN path, length(path) as dist
                ORDER BY dist
                LIMIT {limit}
            }}
            RETURN path, dist
            """
        else:
            cypher = f"""
            MATCH (e {{name: $name}})
            CALL {{
                WITH e
                MATCH path = (e)-[r*1..{depth}]-(other)
                RETURN path, length(path) as dist
                ORDER BY dist
                LIMIT {limit}
            }}
            RETURN path, dist
            """

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/query",
                    json={"query": cypher, "params": {"name": entity_name}},
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
        if source_entity and target_entity:
            cypher = f"""
            MATCH (a {{name: $source}})-[r:`{relationship_type}`]->(b {{name: $target}})
            RETURN a, r, b
            LIMIT {limit}
            """
            params = {"source": source_entity, "target": target_entity}
        elif source_entity:
            cypher = f"""
            MATCH (a {{name: $source}})-[r:`{relationship_type}`]->(b)
            RETURN a, r, b
            LIMIT {limit}
            """
            params = {"source": source_entity}
        else:
            cypher = f"""
            MATCH (a)-[r:`{relationship_type}`]->(b)
            RETURN a, r, b
            LIMIT {limit}
            """
            params = {}

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
        cypher = f"""
        MATCH (e {{name: $name}})
        CALL {{
            WITH e
            MATCH path = (e)-[r*1..{max_distance}]-(neighbor)
            RETURN neighbor, length(path) as dist
            ORDER BY dist
        }}
        RETURN collect({{node: neighbor, distance: dist}}) as neighborhood
        """

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/query",
                    json={"query": cypher, "params": {"name": entity_name}},
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
