"""
Ingestion Module - Data ingestion subsystem.

Provides chunking, embedding, and indexing pipelines
for multi-source data ingestion.
"""

from ingestion.chunker import DocumentChunker, CodeChunker, ChunkResult
from ingestion.embedder import EmbeddingPipeline, get_embedding_pipeline
from ingestion.indexer import VectorIndexer, GraphIndexer, IndexerResult
from ingestion.pipeline import IngestionPipeline, IngestionJob
from ingestion.api import app as ingestion_app
from ingestion.crossref import CrossReferenceExtractor, get_cross_reference_extractor
from ingestion.structural_chunker import (
    StructuralChunker,
    HierarchicalChunker,
    get_structural_chunker,
    get_hierarchical_chunker,
)
from ingestion.graphrag.pipeline import GraphRAGPipeline, get_graphrag_pipeline
from ingestion.graphrag.entity_extractor import (
    EntityType,
    ExtractedEntity,
    get_entity_extractor,
)
from ingestion.graphrag.community_detector import Community, get_community_detector


__all__ = [
    "DocumentChunker",
    "CodeChunker",
    "ChunkResult",
    "EmbeddingPipeline",
    "get_embedding_pipeline",
    "VectorIndexer",
    "GraphIndexer",
    "IndexerResult",
    "IngestionPipeline",
    "IngestionJob",
    "ingestion_app",
    "CrossReferenceExtractor",
    "get_cross_reference_extractor",
    "StructuralChunker",
    "HierarchicalChunker",
    "get_structural_chunker",
    "get_hierarchical_chunker",
    "GraphRAGPipeline",
    "get_graphrag_pipeline",
    "EntityType",
    "ExtractedEntity",
    "get_entity_extractor",
    "Community",
    "get_community_detector",
]
