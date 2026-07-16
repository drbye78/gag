import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestIndexerResult:
    def test_result_creation(self):
        from ingestion.indexer import IndexerResult

        result = IndexerResult(
            target="qdrant",
            indexed_count=10,
            took_ms=100,
            errors=[],
            metadata={"collection": "test"},
        )
        assert result.indexed_count == 10
        assert result.took_ms == 100
        assert result.errors == []

    def test_result_with_errors(self):
        from ingestion.indexer import IndexerResult

        result = IndexerResult(
            target="falkordb",
            indexed_count=0,
            took_ms=50,
            errors=["Error 1", "Error 2"],
        )
        assert result.indexed_count == 0
        assert len(result.errors) == 2


class TestVectorIndexer:
    def test_initialization(self):
        from ingestion.indexer import VectorIndexer

        indexer = VectorIndexer(host="localhost", port=6333, collection="test")
        assert indexer.host == "localhost"
        assert indexer.port == 6333
        assert indexer.collection == "test"
        assert indexer.base_url == "http://localhost:6333"

    def test_initialization_defaults(self):
        from ingestion.indexer import VectorIndexer

        indexer = VectorIndexer()
        assert "localhost" in indexer.base_url


class TestGraphIndexer:
    def test_initialization(self):
        from ingestion.indexer import GraphIndexer

        indexer = GraphIndexer()
        assert indexer is not None

    @pytest.mark.asyncio
    async def test_execute_cypher_handles_error(self):
        from ingestion.indexer import GraphIndexer

        indexer = GraphIndexer()
        try:
            result = await indexer._execute_cypher("RETURN 1", {})
            assert isinstance(result, bool)
        except Exception:
            pytest.skip("FalkorDB not accessible")


class TestCodeGraphIndexer:
    def test_initialization(self):
        from ingestion.codegraph_indexer import CodeGraphIndexer

        indexer = CodeGraphIndexer()
        assert indexer is not None


class TestCodeGraphFallbackIndexer:
    def test_initialization(self):
        from ingestion.codegraph_indexer import CodeGraphFallbackIndexer

        indexer = CodeGraphFallbackIndexer()
        assert indexer is not None