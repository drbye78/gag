from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from ingestion.crossref import get_cross_reference_extractor, CrossReferenceExtractor
from ingestion.structural_chunker import get_structural_chunker
from ingestion.graphrag.entity_extractor import (
    get_entity_extractor,
    DocumentEntityExtractor,
)
from ingestion.graphrag.relationship_inferrer import (
    get_relationship_inferrer,
    RelationshipInferrer,
)
from ingestion.graphrag.community_detector import (
    get_community_detector,
    CommunityDetector,
)
from ingestion.indexer import get_graph_indexer, get_vector_indexer


@dataclass
class GraphRAGResult:
    source_id: str
    entities: List[Any] = field(default_factory=list)
    relationships: List[Any] = field(default_factory=list)
    communities: List[Any] = field(default_factory=list)
    cross_references: List[Any] = field(default_factory=list)
    chunks: List[Any] = field(default_factory=list)
    took_ms: int = 0


class GraphRAGPipeline:
    def __init__(
        self,
        use_llm_extraction: bool = False,
        use_structural_chunking: bool = True,
    ):
        self.use_llm_extraction = use_llm_extraction
        self.use_structural_chunking = use_structural_chunking

        self.crossref_extractor = get_cross_reference_extractor()
        self.structural_chunker = get_structural_chunker()
        self.entity_extractor = get_entity_extractor(use_llm=use_llm_extraction)
        self.relationship_inferrer = get_relationship_inferrer(
            use_llm=use_llm_extraction
        )
        self.community_detector = get_community_detector(use_llm=use_llm_extraction)

        self.graph_indexer = get_graph_indexer()
        self.vector_indexer = get_vector_indexer()

    async def process_document(
        self,
        content: str,
        source_id: str,
        source_type: str = "document",
    ) -> GraphRAGResult:
        import time

        start = time.time()

        cross_ref_result = self.crossref_extractor.extract(content, source_id)

        if self.use_structural_chunking:
            chunk_result = self.structural_chunker.chunk(content, source_id)
        else:
            from ingestion.chunker import get_document_chunker

            chunk_result = get_document_chunker().chunk(content, source_id)

        entities = []
        relationships = []
        communities = []

        if hasattr(self.entity_extractor, "extract"):
            entity_result = await self.entity_extractor.extract(content, source_id)
            entities = entity_result.entities

            if entities and hasattr(self.relationship_inferrer, "infer"):
                rel_result = await self.relationship_inferrer.infer(
                    entities, content, source_id
                )
                relationships = rel_result.relationships

                if hasattr(self.community_detector, "detect"):
                    comm_result = await self.community_detector.detect(
                        entities, relationships
                    )
                    communities = comm_result.communities

        await self._index_to_graph(entities, relationships, cross_ref_result.references)

        for chunk in chunk_result.chunks:
            chunk.metadata["entities"] = [
                e.id for e in entities if e.name.lower() in chunk.content.lower()
            ][:10]

        took = int((time.time() - start) * 1000)
        return GraphRAGResult(
            source_id=source_id,
            entities=entities,
            relationships=relationships,
            communities=communities,
            cross_references=cross_ref_result.references,
            chunks=chunk_result.chunks,
            took_ms=took,
        )

    async def _index_to_graph(
        self,
        entities: List[Any],
        relationships: List[Any],
        cross_refs: List[Any],
    ) -> None:
        nodes = []
        for entity in entities:
            nodes.append(
                {
                    "id": entity.id,
                    "node_type": "entity",
                    "properties": {
                        "name": entity.name,
                        "type": entity.entity_type.value,
                        "description": entity.description,
                        "source_id": entity.id.split(":")[0]
                        if ":" in entity.id
                        else "",
                    },
                }
            )

        if nodes:
            await self.graph_indexer.index_nodes(nodes)

        edges = []
        for rel in relationships:
            edges.append(
                {
                    "source_id": rel.source_id,
                    "target_id": rel.target_id,
                    "edge_type": rel.relationship_type.value,
                    "properties": {
                        "confidence": rel.confidence,
                        "context": rel.context[:200],
                    },
                }
            )

        for cross_ref in cross_refs:
            edges.append(
                {
                    "source_id": cross_ref.source_id,
                    "target_id": cross_ref.target_id,
                    "edge_type": "references",
                    "properties": {
                        "ref_type": cross_ref.ref_type.value,
                        "line": cross_ref.line_number,
                    },
                }
            )

        if edges:
            await self.graph_indexer.index_edges(edges)


class IncrementalGraphRAGPipeline(GraphRAGPipeline):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.doc_hashes: Dict[str, str] = {}

    def _compute_hash(self, content: str) -> str:
        import hashlib

        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def process_document(
        self,
        content: str,
        source_id: str,
        source_type: str = "document",
    ) -> GraphRAGResult:
        new_hash = self._compute_hash(content)

        if source_id in self.doc_hashes and self.doc_hashes[source_id] == new_hash:
            return GraphRAGResult(source_id=source_id, took_ms=0)

        self.doc_hashes[source_id] = new_hash

        return await super().process_document(content, source_id, source_type)


def get_graphrag_pipeline(
    use_llm_extraction: bool = False,
    use_structural_chunking: bool = True,
    incremental: bool = False,
) -> GraphRAGPipeline:
    if incremental:
        return IncrementalGraphRAGPipeline(
            use_llm_extraction=use_llm_extraction,
            use_structural_chunking=use_structural_chunking,
        )
    return GraphRAGPipeline(
        use_llm_extraction=use_llm_extraction,
        use_structural_chunking=use_structural_chunking,
    )
