"""
Unified Ingestion Pipeline - Multi-format artifact ingestion with dual output.

Provides:
- 30+ artifact type handlers (document, markdown, source_code, config, k8s, diagram, etc.)
- Dual output: Qdrant (vectors) + FalkorDB (graph)
- Handlers adapt from existing ingestion/ and integrate with GraphRAG

Architecture:
- ArtifactJob with status progression: PENDING → CHUNKING → EMBEDDING → INDEXING → COMPLETED
- HandlerRegistry factory pattern for handler discovery
- VectorIndexer for Qdrant, GraphIndexer for FalkorDB
"""

from unified_ingestion.api import router as ingestion_router
from unified_ingestion.core.job import ArtifactJob, JobStatus
from unified_ingestion.core.registry import JobRegistry, get_job_registry
from unified_ingestion.core.types import ArtifactStatus, ArtifactType
from unified_ingestion.handlers.base import Chunk, Handler, HandlerResult
from unified_ingestion.handlers.registry import HandlerRegistry, get_handler_registry

__all__ = [
    "ArtifactType",
    "ArtifactStatus",
    "ArtifactJob",
    "JobStatus",
    "JobRegistry",
    "get_job_registry",
    "HandlerRegistry",
    "get_handler_registry",
    "Handler",
    "HandlerResult",
    "Chunk",
    "ingestion_router",
]
