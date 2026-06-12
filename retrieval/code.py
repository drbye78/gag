"""
Code Retriever - Code retrieval from vector store.

Queries code entities from Qdrant with language filtering.
"""

import time
from typing import Any, Dict, Optional

import httpx


class CodeRetriever:
    # Common programming language identifiers for filtering
    SUPPORTED_LANGUAGES = {
        "python",
        "javascript",
        "typescript",
        "java",
        "go",
        "rust",
        "c",
        "cpp",
        "csharp",
        "ruby",
        "php",
        "swift",
        "kotlin",
        "scala",
        "shell",
        "sql",
        "html",
        "css",
    }

    def __init__(self, host: Optional[str] = None, port: int = 6333, collection: str = "code"):
        self.host = host or "localhost"
        self.port = port
        self.collection = collection
        self.base_url = f"http://{self.host}:{self.port}"

    async def search(
        self,
        query: str,
        limit: int = 10,
        language: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)

        from llm.router import get_router

        router = get_router()
        embedding = await router.embed(query)
        payload = {"vector": embedding, "limit": limit, "filter": filters or {}}

        if language:
            normalized_lang = language.lower().strip()
            if normalized_lang in self.SUPPORTED_LANGUAGES:
                payload["filter"]["language"] = {"eq": normalized_lang}
            else:
                # Still apply the filter even if not in known set
                payload["filter"]["language"] = {"eq": normalized_lang}

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
            "source": "code",
            "query": query,
            "results": data.get("result", []),
            "total": len(data.get("result", [])),
            "took_ms": took,
        }


def get_code_retriever() -> CodeRetriever:
    return CodeRetriever()
