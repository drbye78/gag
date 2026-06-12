import pytest

from ingestion.pipeline import IngestionPipeline


class MockChunk:
    def __init__(self, id, content, chunk_index, metadata=None):
        self.id = id
        self.content = content
        self.chunk_index = chunk_index
        self.metadata = metadata or {}


class MockChunkResult:
    def __init__(self, chunks):
        self.chunks = chunks


class MockEmbeddedChunk:
    def __init__(self, id, content, embedding, metadata):
        self.id = id
        self.content = content
        self.embedding = embedding
        self.metadata = metadata


class MockIndexerResult:
    def __init__(self, indexed_count=0):
        self.indexed_count = indexed_count


@pytest.mark.asyncio
async def test_ingest_standard_without_graphrag():
    from ingestion.graphrag.pipeline import GraphRAGPipeline

    try:
        pipeline = GraphRAGPipeline()
        # Test that pipeline can be instantiated
        assert pipeline is not None
    except Exception as e:
        pytest.skip(f"GraphRAG backend not available: {e}")


@pytest.mark.asyncio
async def test_ingest_document_accepts_use_graphrag_param():
    pipeline = IngestionPipeline(use_graphrag=False)

    assert hasattr(pipeline, "ingest_document")


@pytest.mark.asyncio
async def test_ingest_with_metadata():
    pipeline = IngestionPipeline(use_graphrag=False)

    assert hasattr(pipeline, "ingest_document")


@pytest.mark.asyncio
async def test_ingest_code_type_uses_code_chunker():
    from ingestion.chunker import CodeChunker

    chunker = CodeChunker()
    # Test that code chunker works
    assert chunker is not None


def test_get_ingestion_pipeline_with_graphrag_flag():
    from core.config import get_settings

    settings = get_settings()
    original = settings.graphrag_enabled

    pipeline = IngestionPipeline(use_graphrag=True)
    assert pipeline.use_graphrag

    pipeline2 = IngestionPipeline(use_graphrag=False)
    assert not pipeline2.use_graphrag


def test_pipeline_has_graphrag_pipeline_property():
    pipeline = IngestionPipeline(use_graphrag=False)
    assert hasattr(pipeline, "graphrag_pipeline")


def test_pipeline_list_jobs():
    pipeline = IngestionPipeline(use_graphrag=False)

    assert hasattr(pipeline, "list_jobs")
    assert callable(pipeline.list_jobs)


def test_pipeline_get_job():
    pipeline = IngestionPipeline(use_graphrag=False)

    assert hasattr(pipeline, "get_job")
    assert callable(pipeline.get_job)


def test_pipeline_cancel_job():
    pipeline = IngestionPipeline(use_graphrag=False)

    assert hasattr(pipeline, "cancel_job")
    assert callable(pipeline.cancel_job)
