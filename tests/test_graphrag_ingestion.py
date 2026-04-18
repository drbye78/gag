import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ingestion.pipeline import IngestionPipeline, JobStatus


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
    pipeline = IngestionPipeline(use_graphrag=False)

    with patch.object(pipeline.chunker, 'chunk', return_value=MockChunkResult([
        MockChunk("c1", "test content", 0, {}),
    ])):
        with patch('ingestion.pipeline.get_embedding_pipeline') as mock_embed:
            mock_embed.return_value.embed_chunks = AsyncMock(return_value=[
                MockEmbeddedChunk("c1", "test content", [0.1] * 1024, {})
            ])

            with patch.object(pipeline.vector_indexer, 'index_chunks', return_value=MockIndexerResult(1)):
                job = await pipeline.ingest_document(
                    content="test content",
                    source_id="test-1",
                    source_type="document",
                    metadata={},
                    index=True,
                )

                assert job.status == JobStatus.COMPLETED
                assert job.total_chunks == 1
                assert job.indexed_count == 1


@pytest.mark.asyncio
async def test_ingest_document_accepts_use_graphrag_param():
    pipeline = IngestionPipeline(use_graphrag=False)

    job = await pipeline.ingest_document(
        content="test content",
        source_id="test-1",
        source_type="document",
        use_graphrag=False,
    )

    assert job is not None
    assert job.source_id == "test-1"


@pytest.mark.asyncio
async def test_ingest_with_metadata():
    pipeline = IngestionPipeline(use_graphrag=False)

    with patch.object(pipeline.chunker, 'chunk', return_value=MockChunkResult([
        MockChunk("c1", "test content", 0, {}),
    ])):
        with patch('ingestion.pipeline.get_embedding_pipeline') as mock_embed:
            mock_embed.return_value.embed_chunks = AsyncMock(return_value=[
                MockEmbeddedChunk("c1", "test content", [0.1] * 1024, {})
            ])

            with patch.object(pipeline.vector_indexer, 'index_chunks', return_value=MockIndexerResult(1)):
                job = await pipeline.ingest_document(
                    content="test content",
                    source_id="test-1",
                    metadata={"custom_key": "custom_value"},
                )

                assert job.metadata.get("custom_key") == "custom_value"


@pytest.mark.asyncio
async def test_ingest_code_type_uses_code_chunker():
    pipeline = IngestionPipeline(use_graphrag=False)

    with patch.object(pipeline.code_chunker, 'chunk', return_value=MockChunkResult([
        MockChunk("c1", "def test(): pass", 0, {"entity_type": "function"}),
    ])):
        with patch('ingestion.pipeline.get_embedding_pipeline') as mock_embed:
            mock_embed.return_value.embed_chunks = AsyncMock(return_value=[
                MockEmbeddedChunk("c1", "def test(): pass", [0.1] * 1024, {"entity_type": "function"})
            ])

            with patch.object(pipeline.vector_indexer, 'index_chunks', return_value=MockIndexerResult(1)):
                job = await pipeline.ingest_document(
                    content="def test(): pass",
                    source_id="test-code",
                    source_type="code",
                )

                assert job.status == JobStatus.COMPLETED
                assert job.source_type == "code"


def test_get_ingestion_pipeline_with_graphrag_flag():
    with patch('ingestion.pipeline.get_settings') as mock_settings:
        mock_settings.return_value.graphrag_enabled = False

        pipeline = IngestionPipeline(use_graphrag=True)
        assert pipeline.use_graphrag == True

        pipeline2 = IngestionPipeline(use_graphrag=False)
        assert pipeline2.use_graphrag == False


def test_pipeline_has_graphrag_pipeline_property():
    pipeline = IngestionPipeline(use_graphrag=False)
    assert hasattr(pipeline, 'graphrag_pipeline')
    assert pipeline.graphrag_pipeline is None


@pytest.mark.asyncio
async def test_pipeline_list_jobs():
    pipeline = IngestionPipeline(use_graphrag=False)

    job = await pipeline.ingest_document(
        content="test",
        source_id="test-1",
    )

    jobs = pipeline.list_jobs(limit=10)
    assert len(jobs) >= 1
    assert jobs[0]["source_id"] == "test-1"


@pytest.mark.asyncio
async def test_pipeline_get_job():
    pipeline = IngestionPipeline(use_graphrag=False)

    job = await pipeline.ingest_document(
        content="test",
        source_id="test-1",
    )

    retrieved = pipeline.get_job(job.job_id)
    assert retrieved is not None
    assert retrieved.job_id == job.job_id


def test_pipeline_cancel_job():
    pipeline = IngestionPipeline(use_graphrag=False)

    with patch('ingestion.pipeline.get_embedding_pipeline') as mock_embed:
        mock_embed.return_value.embed_chunks = AsyncMock(return_value=[])

        job = pipeline._jobs["test-job"] = MagicMock()
        job.status = JobStatus.PENDING

        result = pipeline.cancel_job("test-job")
        assert result == True