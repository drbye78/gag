import time
from typing import Any, Dict, List, Optional

import httpx


class GraphQLRetriever:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection: str = "graphql",
    ):
        self.host = host
        self.port = port
        self.collection = collection
        self.base_url = f"http://{host}:{port}"

    async def search(
        self,
        query: str,
        limit: int = 10,
        kind: Optional[str] = None,
        type_name: Optional[str] = None,
        entity_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)

        from llm.router import get_router
        router = get_router()
        embedding = await router.embed(query)
        payload = {"vector": embedding, "limit": limit, "filter": filters or {}}

        if kind:
            payload["filter"]["kind"] = {"eq": kind}
        if type_name:
            payload["filter"]["type_name"] = {"eq": type_name}
        if entity_type:
            payload["filter"]["entity_type"] = {"eq": entity_type}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/collections/{self.collection}/points/search",
                    json=payload,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
        except Exception:
            data = {"result": [], "status": "error"}

        took = int(time.time() * 1000) - start

        return {
            "source": "graphql",
            "query": query,
            "results": data.get("result", []),
            "total": len(data.get("result", [])),
            "took_ms": took,
        }


def get_graphql_retriever() -> GraphQLRetriever:
    return GraphQLRetriever()