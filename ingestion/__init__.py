"""
Ingestion Module - Data ingestion subsystem.

Provides chunking, embedding, and indexing pipelines
for multi-source data ingestion.
"""

from ingestion.api import app as ingestion_app
from ingestion.chunker import ChunkResult, CodeChunker, DocumentChunker
from ingestion.crossref import CrossReferenceExtractor, get_cross_reference_extractor
from ingestion.embedder import EmbeddingPipeline, get_embedding_pipeline
from ingestion.graphrag.community_detector import Community, get_community_detector
from ingestion.graphrag.entity_extractor import (
    EntityType,
    ExtractedEntity,
    get_entity_extractor,
)
from ingestion.graphrag.pipeline import GraphRAGPipeline, get_graphrag_pipeline
from ingestion.indexer import GraphIndexer, IndexerResult, VectorIndexer
from ingestion.pipeline import IngestionJob, IngestionPipeline
from ingestion.structural_chunker import (
    HierarchicalChunker,
    StructuralChunker,
    get_hierarchical_chunker,
    get_structural_chunker,
)

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
