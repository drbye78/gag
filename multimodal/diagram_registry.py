import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import httpx

if TYPE_CHECKING:
    from multimodal.diagram_ir import DiagramIR

logger = logging.getLogger(__name__)

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
FALKOR_HOST = os.getenv("FALKOR_HOST", "localhost")
FALKOR_PORT = int(os.getenv("FALKOR_PORT", "6379"))


@dataclass
class DiagramSearchResult:
    ir: "DiagramIR"
    score: float = 0.0


class DiagramRegistry:
    def __init__(
        self,
        use_qdrant: bool = True,
        use_falkor: bool = True,
    ):
        self.use_qdrant = use_qdrant and self._check_qdrant()
        self.use_falkor = use_falkor and self._check_falkor()
        self._cache: Dict[str, "DiagramIR"] = {}

    def _check_qdrant(self) -> bool:
        try:
            import httpx

            r = httpx.get(f"http://{QDRANT_HOST}:{QDRANT_PORT}/health", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def _check_falkor(self) -> bool:
        try:
            import httpx

            r = httpx.get(f"http://{FALKOR_HOST}:{FALKOR_PORT}/health", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    async def index(self, ir: "DiagramIR") -> bool:
        if ir.id in self._cache:
            self._cache[ir.id] = ir
            return True

        self._cache[ir.id] = ir

        if self.use_qdrant:
            await self._index_qdrant(ir)
        if self.use_falkor:
            await self._index_falkor(ir)

        return True

    async def _index_qdrant(self, ir: "DiagramIR"):
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "points": [
                        {
                            "id": ir.id,
                            "vector": ir.embedding or [0.0] * 384,
                            "payload": {
                                "diagram_type": ir.diagram_type,
                                "title": ir.title,
                                "node_count": len(ir.nodes),
                                "edge_count": len(ir.edges),
                            },
                        }
                    ]
                }
                await client.put(
                    f"http://{QDRANT_HOST}:{QDRANT_PORT}/collections/diagrams/points",
                    json=payload,
                    timeout=10,
                )
        except Exception as e:
            logger.debug("Qdrant indexing failed: %s", e)

    async def _index_falkor(self, ir: "DiagramIR"):
        try:
            async with httpx.AsyncClient() as client:
                # Batch all nodes and edges into a single request to avoid N+1
                batch_payload = {
                    "diagram_id": ir.id,
                    "nodes": [
                        {
                            "diagram_id": ir.id,
                            "node_id": node.id,
                            "type": node.type.value,
                            "name": node.name,
                        }
                        for node in ir.nodes
                    ],
                    "edges": [
                        {
                            "diagram_id": ir.id,
                            "source": edge.source,
                            "target": edge.target,
                            "type": edge.type.value,
                            "label": edge.label,
                        }
                        for edge in ir.edges
                    ],
                }
                await client.post(
                    f"http://{FALKOR_HOST}:{FALKOR_PORT}/batch",
                    json=batch_payload,
                    timeout=30,
                )
        except Exception as e:
            logger.debug("FalkorDB batch indexing failed: %s", e)

    async def search(
        self,
        query: str,
        limit: int = 10,
        diagram_types: Optional[List[str]] = None,
    ) -> List[DiagramSearchResult]:
        results = []

        if self.use_qdrant:
            qdrant_results = await self._search_qdrant(query, limit, diagram_types)
            results.extend(qdrant_results)

        if not results and self.use_falkor:
            falkor_results = await self._search_falkor(query, limit, diagram_types)
            results.extend(falkor_results)

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    async def _search_qdrant(
        self,
        query: str,
        limit: int,
        diagram_types: Optional[List[str]],
    ) -> List[DiagramSearchResult]:
        try:
            from llm.router import get_llm_router

            router = get_llm_router()
            embedding = await router.embed(query)
            if not embedding:
                return []

            async with httpx.AsyncClient() as client:
                payload = {
                    "vector": embedding,
                    "limit": limit,
                    "filter": {"must": [{"key": "diagram_type", "match": diagram_types}]}
                    if diagram_types
                    else None,
                }
                r = await client.post(
                    f"http://{QDRANT_HOST}:{QDRANT_PORT}/collections/diagrams/points/search",
                    json=payload,
                    timeout=10,
                )
                if r.status_code != 200:
                    return []

                data = r.json()
                results = []
                for point in data.get("result", []):
                    ir = self._cache.get(point.get("id"))
                    if ir:
                        results.append(
                            DiagramSearchResult(ir=ir, score=point.get("score", 0.0))
                        )
                return results

        except Exception as e:
            logger.debug("Qdrant search failed: %s", e)
            return []

    async def _search_falkor(
        self,
        query: str,
        limit: int,
        diagram_types: Optional[List[str]],
    ) -> List[DiagramSearchResult]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"http://{FALKOR_HOST}:{FALKOR_PORT}/search",
                    json={"query": query, "limit": limit},
                    timeout=10,
                )
                if r.status_code != 200:
                    return []

                data = r.json()
                results = []
                for item in data.get("data", []):
                    ir = self._cache.get(item.get("diagram_id"))
                    if ir:
                        results.append(
                            DiagramSearchResult(ir=ir, score=item.get("score", 0.0))
                        )
                return results

        except Exception as e:
            logger.debug("Falkor search failed: %s", e)
            return []

    async def get_by_id(self, diagram_id: str) -> Optional["DiagramIR"]:
        return self._cache.get(diagram_id)

    async def get_graph(self, diagram_id: str) -> Optional[Dict[str, Any]]:
        ir = self._cache.get(diagram_id)
        if not ir:
            return None

        nodes = []
        for node in ir.nodes:
            nodes.append({"id": node.id, "label": node.name, "type": node.type.value})

        edges = []
        for edge in ir.edges:
            edges.append(
                {"from": edge.source, "to": edge.target, "label": edge.type.value}
            )

        return {"nodes": nodes, "edges": edges}

    def list_diagrams(self) -> List[str]:
        return list(self._cache.keys())