"""
README claim: "7 source types: Git repositories, Documents, Tickets, Telemetry,
Knowledge Base, Architecture, Requirements"
Source: README.md line 119
"""
import pytest
import importlib


@pytest.mark.claim
def test_ingestion_source_types_exist():
    source_modules = [
        "git.pipeline",
        "ingestion.pipeline",
        "ingestion.ticket",
        "ingestion.telemetry",
        "ingestion.knowledge_base",
        "ingestion.architecture",
        "ingestion.requirements",
    ]
    for mod in source_modules:
        try:
            importlib.import_module(mod)
        except ImportError as e:
            pytest.fail(f"Ingestion source module '{mod}' missing: {e}")


@pytest.mark.claim
def test_git_ingestion_method_exists():
    from git.pipeline import GitIngestionPipeline
    pipeline = GitIngestionPipeline()
    assert hasattr(pipeline, "ingest_repository"), "Git pipeline must have ingest_repository method"


@pytest.mark.claim
@pytest.mark.asyncio
async def test_document_ingestion_produces_chunks():
    from ingestion.pipeline import IngestionPipeline
    from unittest.mock import AsyncMock, MagicMock

    pipeline = IngestionPipeline()
    pipeline.embedder = MagicMock()
    pipeline.embedder.embed_chunks = AsyncMock(return_value=[
        {"id": "chunk1", "content": "test", "embedding": [0.1] * 10, "source_id": "test"}
    ])
    pipeline.vector_indexer = MagicMock()
    pipeline.vector_indexer.index_chunks = AsyncMock(return_value=MagicMock(indexed_count=1))

    job = await pipeline.ingest_document("Test content for chunking that is long enough", "test_doc", "document")
    assert job.total_chunks > 0, "Document ingestion produced 0 chunks"
    assert job.status.value == "completed", f"Ingestion should complete, got {job.status}"
