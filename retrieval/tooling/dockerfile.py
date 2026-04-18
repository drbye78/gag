import time
from typing import Any, Dict, List, Optional

import httpx


class DockerfileRetriever:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection: str = "dockerfile",
    ):
        self.host = host
        self.port = port
        self.collection = collection
        self.base_url = f"http://{host}:{port}"

    async def search(
        self,
        query: str,
        limit: int = 10,
        instruction: Optional[str] = None,
        base_image: Optional[str] = None,
        entity_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)

        payload = {"vector": [0.0] * 1024, "limit": limit, "filter": filters or {}}

        if instruction:
            payload["filter"]["instruction"] = {"eq": instruction}
        if base_image:
            payload["filter"]["base_image"] = {"eq": base_image}
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
            "source": "dockerfile",
            "query": query,
            "results": data.get("result", []),
            "total": len(data.get("result", [])),
            "took_ms": took,
        }


def get_dockerfile_retriever() -> DockerfileRetriever:
    return DockerfileRetriever()