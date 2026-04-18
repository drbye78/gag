"""
Diagram Retriever - Search and understand architecture diagrams.

Integrates with hybrid retrieval for diagram-aware search.
Supports Qdrant-based vector indexing and FalkorDB graph storage.
"""

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from documents.diagram_parser import (
    get_diagram_parser,
    DiagramType,
    DiagramExtractionResult,
)


logger = logging.getLogger(__name__)


@dataclass
class DiagramSearchResult:
    doc_id: str
    score: float
    diagram_type: str
    entities: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    generated_code: str = ""
    content: str = ""


@dataclass
class DiagramRetrievalResult:
    query: str
    results: List[DiagramSearchResult]
    detected_type: str = ""
    took_ms: int = 0
    error: Optional[str] = None


class DiagramQdrantIndexer:
    """Qdrant-based vector indexer for diagrams."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 6333,
        collection: str = "diagrams",
        vector_size: int = 384,
    ):
        self.host = host or os.getenv("QDRANT_HOST", "localhost")
        self.port = port
        self.collection = collection
        self.vector_size = vector_size
        self.base_url = f"http://{self.host}:{self.port}"
        self._client: Optional[httpx.AsyncClient] = None
        self._embedder = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=30.0),
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _get_embedder(self):
        if self._embedder is None:
            try:
                from ingestion.embedder import get_text_embedder
                self._embedder = get_text_embedder()
            except Exception as e:
                logger.warning("Failed to load embedder: %s", e)
        return self._embedder

    async def create_collection(self) -> bool:
        payload = {
            "vectors": {
                "size": self.vector_size,
                "distance": "Cosine",
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
            logger.error("Failed to create collection: %s", e)
            return False

    async def index_diagram(
        self,
        doc_id: str,
        content: str,
        diagram_type: str,
        entities: List[Dict],
        relationships: List[Dict],
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        start = time.time()
        embedder = self._get_embedder()

        if not embedder:
            return {"indexed": False, "error": "Embedder not available"}

        try:
            await self.create_collection()
        except Exception:
            pass

        try:
            embedding = await embedder.aget_embedding(content)
            if hasattr(embedding, "tolist"):
                vector = embedding.tolist()
            else:
                vector = list(embedding)
        except Exception as e:
            logger.warning("Failed to embed content: %s", e)
            vector = [0.0] * self.vector_size

        combined_text = content
        if entities:
            entity_names = ", ".join([e.get("name", "") for e in entities[:10]])
            combined_text = f"{content}. Entities: {entity_names}"

        point = {
            "id": doc_id,
            "vector": vector,
            "payload": {
                "content": content[:2000],
                "diagram_type": diagram_type,
                "entities": entities,
                "relationships": relationships,
                "metadata": metadata or {},
                "combined_text": combined_text[:2000],
            },
        }

        try:
            client = await self._get_client()
            resp = await client.put(
                f"{self.base_url}/collections/{self.collection}/points",
                json={"points": [point]},
                timeout=60.0,
            )
            indexed = resp.status_code in (200, 201)
        except Exception as e:
            return {"indexed": False, "error": str(e)}

        return {
            "indexed": indexed,
            "doc_id": doc_id,
            "took_ms": int((time.time() - start) * 1000),
        }

    async def search(
        self,
        query: str,
        limit: int = 10,
        diagram_type_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        embedder = self._get_embedder()
        if not embedder:
            return []

        try:
            query_emb = await embedder.aget_embedding(query)
            if hasattr(query_emb, "tolist"):
                vector = query_emb.tolist()
            else:
                vector = list(query_emb)
        except Exception:
            return []

        filter_dict = None
        if diagram_type_filter:
            filter_dict = {
                "must": [
                    {"key": "diagram_type", "match": {"value": diagram_type_filter}}
                ]
            }

        search_payload = {
            "vector": vector,
            "limit": limit,
            "with_payload": True,
            "with_vector": False,
        }
        if filter_dict:
            search_payload["filter"] = filter_dict

        try:
            client = await self._get_client()
            resp = await client.post(
                f"{self.base_url}/collections/{self.collection}/points/search",
                json=search_payload,
                timeout=60.0,
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            results = []
            for point in data.get("result", []):
                payload = point.get("payload", {})
                results.append({
                    "doc_id": point.get("id"),
                    "score": point.get("score", 0.0),
                    "content": payload.get("content", ""),
                    "diagram_type": payload.get("diagram_type", ""),
                    "entities": payload.get("entities", []),
                    "relationships": payload.get("relationships", []),
                    "metadata": payload.get("metadata", {}),
                })
            return results
        except Exception as e:
            logger.error("Diagram search failed: %s", e)
            return []

    async def delete_by_doc_id(self, doc_id: str) -> bool:
        try:
            client = await self._get_client()
            resp = await client.post(
                f"{self.base_url}/collections/{self.collection}/points/delete",
                json={"points": [doc_id]},
                timeout=30.0,
            )
            return resp.status_code in (200, 201)
        except Exception:
            return False


class DiagramGraphIndexer:
    """FalkorDB-based graph indexer for diagram entities."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 7379,
    ):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def index_diagram(
        self,
        doc_id: str,
        diagram_type: str,
        entities: List[Dict],
        relationships: List[Dict],
    ) -> Dict[str, Any]:
        if not entities:
            return {"indexed": 0, "error": "No entities to index"}

        client = await self._get_client()
        indexed = 0

        for entity in entities:
            entity_name = entity.get("name", "")
            if not entity_name:
                continue

            node_id = f"{doc_id}:{entity_name}"
            cypher = """
            MERGE (n:DiagramEntity {id: $id})
            SET n.name = $name,
                n.type = $type,
                n.diagram_type = $diagram_type,
                n.doc_id = $doc_id
            """
            props = {
                "id": node_id,
                "name": entity_name,
                "type": entity.get("type", "entity"),
                "diagram_type": diagram_type,
                "doc_id": doc_id,
            }

            try:
                resp = await client.post(
                    f"{self.base_url}/query",
                    json={"query": cypher, "params": props},
                    timeout=30.0,
                )
                if resp.status_code in (200, 201):
                    indexed += 1
            except Exception as e:
                logger.warning(f"Failed to index entity {entity_name}: {e}")

        for rel in relationships:
            from_name = rel.get("from", "")
            to_name = rel.get("to", "")
            if not from_name or not to_name:
                continue

            from_id = f"{doc_id}:{from_name}"
            to_id = f"{doc_id}:{to_name}"
            rel_type = rel.get("type", "RELATED_TO").upper()

            cypher = """
            MATCH (a:DiagramEntity {id: $from_id})
            MATCH (b:DiagramEntity {id: $to_id})
            MERGE (a)-[r:DIAGRAM_RELATIONSHIP {type: $rel_type}]->(b)
            """
            props = {
                "from_id": from_id,
                "to_id": to_id,
                "rel_type": rel_type,
            }

            try:
                await client.post(
                    f"{self.base_url}/query",
                    json={"query": cypher, "params": props},
                    timeout=30.0,
                )
            except Exception:
                pass

        return {"indexed": indexed, "doc_id": doc_id}

    async def search_by_entity(
        self,
        entity_name: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        cypher = """
        MATCH (n:DiagramEntity)
        WHERE n.name CONTAINS $name
        OPTIONAL MATCH (n)-[r:DIAGRAM_RELATIONSHIP]->(m:DiagramEntity)
        RETURN n.name as entity, n.type as type, n.diagram_type as diagram_type,
               m.name as target, r.type as rel_type
        LIMIT $limit
        """
        try:
            client = await self._get_client()
            resp = await client.post(
                f"{self.base_url}/query",
                json={"query": cypher, "params": {"name": entity_name, "limit": limit}},
                timeout=30.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("results", [])
        except Exception:
            pass
        return []


class DiagramRetriever:
    def __init__(
        self,
        use_qdrant: bool = True,
        use_graph: bool = True,
    ):
        self._parser = get_diagram_parser()
        self._indexed: List[Dict[str, Any]] = []
        self._qdrant_indexer: Optional[DiagramQdrantIndexer] = None
        self._graph_indexer: Optional[DiagramGraphIndexer] = None
        self._use_qdrant = use_qdrant
        self._use_graph = use_graph

    def _get_qdrant_indexer(self) -> Optional[DiagramQdrantIndexer]:
        if self._qdrant_indexer is None and self._use_qdrant:
            self._qdrant_indexer = DiagramQdrantIndexer()
        return self._qdrant_indexer

    def _get_graph_indexer(self) -> Optional[DiagramGraphIndexer]:
        if self._graph_indexer is None and self._use_graph:
            self._graph_indexer = DiagramGraphIndexer()
        return self._graph_indexer

    async def index_diagram(
        self,
        image_content: Any,
        doc_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result = await self._parser.parse_image(image_content)

        combined_content = result.generated_code
        if not combined_content and result.entities:
            entity_texts = [e.get("name", "") for e in result.entities[:20]]
            combined_content = f"Type: {result.diagram_type.value}. Entities: {', '.join(entity_texts)}"

        indexed = {
            "doc_id": doc_id,
            "diagram_type": result.diagram_type.value,
            "entities": result.entities,
            "relationships": result.relationships,
            "generated_code": result.generated_code,
            "content": combined_content,
            "metadata": metadata or {},
        }
        self._indexed.append(indexed)

        qdrant_idx = self._get_qdrant_indexer()
        if qdrant_idx:
            try:
                await qdrant_idx.index_diagram(
                    doc_id=doc_id,
                    content=combined_content,
                    diagram_type=result.diagram_type.value,
                    entities=result.entities,
                    relationships=result.relationships,
                    metadata=metadata,
                )
            except Exception as e:
                logger.warning(f"Qdrant indexing failed: {e}")

        graph_idx = self._get_graph_indexer()
        if graph_idx:
            try:
                await graph_idx.index_diagram(
                    doc_id=doc_id,
                    diagram_type=result.diagram_type.value,
                    entities=result.entities,
                    relationships=result.relationships,
                )
            except Exception as e:
                logger.warning(f"Graph indexing failed: {e}")

        return indexed

    async def index_text_diagram(
        self,
        text: str,
        doc_id: str,
        diagram_type: Optional[DiagramType] = None,
    ) -> Dict[str, Any]:
        result = await self._parser.parse_from_text(text, diagram_type)

        combined_content = result.generated_code
        if not combined_content and result.entities:
            entity_texts = [e.get("name", "") for e in result.entities[:20]]
            combined_content = f"Type: {result.diagram_type.value}. Entities: {', '.join(entity_texts)}"

        indexed = {
            "doc_id": doc_id,
            "diagram_type": result.diagram_type.value,
            "entities": result.entities,
            "relationships": result.relationships,
            "generated_code": result.generated_code,
            "content": combined_content,
        }
        self._indexed.append(indexed)

        qdrant_idx = self._get_qdrant_indexer()
        if qdrant_idx:
            try:
                await qdrant_idx.index_diagram(
                    doc_id=doc_id,
                    content=combined_content,
                    diagram_type=result.diagram_type.value,
                    entities=result.entities,
                    relationships=result.relationships,
                )
            except Exception as e:
                logger.warning(f"Qdrant indexing failed: {e}")

        return indexed

    async def search_diagrams(
        self,
        query: str,
        limit: int = 10,
        use_vector: bool = True,
    ) -> Dict[str, Any]:
        result = await self.search(query, limit, use_vector=use_vector)
        return {
            "source": "diagram",
            "results": [
                {
                    "doc_id": r.doc_id,
                    "score": r.score,
                    "diagram_type": r.diagram_type,
                    "entities": r.entities,
                    "relationships": r.relationships,
                    "generated_code": r.generated_code,
                    "content": r.content,
                }
                for r in result.results
            ],
            "total": len(result.results),
            "detected_type": result.detected_type,
            "took_ms": result.took_ms,
            "error": result.error,
        }

    async def search(
        self,
        query: str,
        limit: int = 10,
        use_vector: bool = True,
    ) -> DiagramRetrievalResult:
        start = int(time.time() * 1000)

        if use_vector:
            qdrant_idx = self._get_qdrant_indexer()
            if qdrant_idx:
                try:
                    vector_results = await qdrant_idx.search(query, limit)
                    if vector_results:
                        results = []
                        for r in vector_results:
                            results.append(
                                DiagramSearchResult(
                                    doc_id=r.get("doc_id", ""),
                                    score=r.get("score", 0.0),
                                    diagram_type=r.get("diagram_type", ""),
                                    entities=r.get("entities", []),
                                    relationships=r.get("relationships", []),
                                    generated_code=r.get("metadata", {}).get("generated_code", ""),
                                    content=r.get("content", ""),
                                )
                            )
                        return DiagramRetrievalResult(
                            query=query,
                            results=results,
                            detected_type=results[0].diagram_type if results else "",
                            took_ms=int((time.time() - start) * 1000),
                        )
                except Exception as e:
                    logger.warning(f"Vector search failed, falling back: {e}")

        if not self._indexed:
            return DiagramRetrievalResult(
                query=query, results=[], error="No diagrams indexed"
            )

        scores = []
        query_lower = query.lower()

        for doc in self._indexed:
            score = 0.0

            for ent in doc.get("entities", []):
                name = ent.get("name", "").lower()
                if name and name in query_lower:
                    score += 1.0

            for rel in doc.get("relationships", []):
                for_val = rel.get("from", "").lower()
                to_val = rel.get("to", "").lower()
                if (for_val and for_val in query_lower) or (
                    to_val and to_val in query_lower
                ):
                    score += 0.5

            scores.append((doc, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for doc, score in scores[:limit]:
            results.append(
                DiagramSearchResult(
                    doc_id=doc.get("doc_id", ""),
                    score=score,
                    diagram_type=doc.get("diagram_type", ""),
                    entities=doc.get("entities", []),
                    relationships=doc.get("relationships", []),
                    generated_code=doc.get("generated_code", ""),
                    content=doc.get("content", ""),
                )
            )

        return DiagramRetrievalResult(
            query=query,
            results=results,
            detected_type=results[0].diagram_type if results else "",
            took_ms=int(time.time() * 1000) - start,
        )

    def get_entities_by_type(self, diagram_type: str) -> List[Dict[str, Any]]:
        entities = []
        for doc in self._indexed:
            if doc.get("diagram_type") == diagram_type:
                entities.extend(doc.get("entities", []))
        return entities

    def get_relationships(self) -> List[Dict[str, Any]]:
        rels = []
        for doc in self._indexed:
            rels.extend(doc.get("relationships", []))
        return rels

    def clear_index(self):
        self._indexed = []

    def get_index_size(self) -> int:
        return len(self._indexed)


_diagram_retriever: Optional[DiagramRetriever] = None


def get_diagram_retriever() -> DiagramRetriever:
    global _diagram_retriever
    if _diagram_retriever is None:
        _diagram_retriever = DiagramRetriever()
    return _diagram_retriever


def get_diagram_qdrant_indexer() -> Optional[DiagramQdrantIndexer]:
    return DiagramQdrantIndexer()


def get_diagram_graph_indexer() -> Optional[DiagramGraphIndexer]:
    return DiagramGraphIndexer()