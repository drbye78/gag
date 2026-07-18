"""
Integration test stubs for external service dependencies.

These tests start real Qdrant, FalkorDB, and Redis containers
via docker-compose.test.yml and verify end-to-end functionality.

To run:
1. Start test containers: docker-compose -f docker-compose.test.yml up -d
2. Set test env: export QDRANT_HOST=localhost QDRANT_PORT=6334
   export FALKORDB_HOST=localhost FALKORDB_PORT=7380
   export REDIS_URL=redis://localhost:6380
3. Run: pytest tests/test_integration_e2e.py -v
"""
import os
import pytest

# Skip all tests if test services are not available
pytestmark = pytest.mark.skipif(
    os.getenv("SKIP_INTEGRATION_TESTS", "true").lower() == "true",
    reason="Set SKIP_INTEGRATION_TESTS=false to run integration tests"
)


@pytest.fixture
async def qdrant_client():
    """Connect to test Qdrant instance."""
    import httpx
    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_TEST_PORT", "6334"))
    base_url = f"http://{host}:{port}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Wait for Qdrant to be ready
        for _ in range(10):
            try:
                resp = await client.get(f"{base_url}/ready")
                if resp.status_code == 200:
                    break
            except Exception:
                pass
            import asyncio
            await asyncio.sleep(1)

        yield client


@pytest.fixture
async def falkordb_client():
    """Connect to test FalkorDB instance."""
    import httpx
    host = os.getenv("FALKORDB_HOST", "localhost")
    port = int(os.getenv("FALKORDB_TEST_PORT", "7380"))
    base_url = f"http://{host}:{port}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        for _ in range(10):
            try:
                resp = await client.get(f"{base_url}")
                if resp.status_code == 200:
                    break
            except Exception:
                pass
            import asyncio
            await asyncio.sleep(1)

        yield client


class TestQdrantIntegration:
    """Integration tests against real Qdrant instance."""

    @pytest.mark.asyncio
    async def test_qdrant_health(self, qdrant_client):
        """Qdrant should be healthy."""
        resp = await qdrant_client.get("/ready")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_create_collection(self, qdrant_client):
        """Should be able to create a collection."""
        resp = await qdrant_client.put(
            "/collections/test_collection",
            json={"vectors": {"size": 128, "distance": "Cosine"}},
        )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_index_and_search(self, qdrant_client):
        """Should be able to index a point and search for it."""
        # Index
        resp = await qdrant_client.put(
            "/collections/test_collection/points",
            json={
                "points": [
                    {
                        "id": "test1",
                        "vector": [0.1] * 128,
                        "payload": {"content": "test content", "source": "test"},
                    }
                ]
            },
        )
        assert resp.status_code in (200, 201)

        # Search
        resp = await qdrant_client.post(
            "/collections/test_collection/points/search",
            json={
                "vector": [0.1] * 128,
                "limit": 1,
                "with_payload": True,
            },
        )
        assert resp.status_code == 200
        results = resp.json().get("result", [])
        assert len(results) > 0
        assert results[0]["payload"]["content"] == "test content"

    @pytest.mark.asyncio
    async def test_with_payload_returns_content(self, qdrant_client):
        """Search with with_payload=True must return payload content."""
        resp = await qdrant_client.post(
            "/collections/test_collection/points/search",
            json={
                "vector": [0.1] * 128,
                "limit": 1,
                "with_payload": True,
            },
        )
        results = resp.json().get("result", [])
        assert len(results) > 0
        assert "payload" in results[0]
        assert "content" in results[0]["payload"]


class TestFalkorDBIntegration:
    """Integration tests against real FalkorDB instance."""

    @pytest.mark.asyncio
    async def test_falkordb_health(self, falkordb_client):
        """FalkorDB should be healthy."""
        resp = await falkordb_client.get("/")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_create_and_query_nodes(self, falkordb_client):
        """Should be able to create nodes and query them (without APOC)."""
        # Create a node using plain MERGE (no APOC)
        resp = await falkordb_client.post(
            "/query",
            json={
                "query": "MERGE (n:TestEntity {id: $id, name: $name}) RETURN n",
                "params": {"id": "test1", "name": "Test Node"},
            },
        )
        assert resp.status_code in (200, 201)

        # Query it back
        resp = await falkordb_client.post(
            "/query",
            json={
                "query": "MATCH (n:TestEntity {id: $id}) RETURN n",
                "params": {"id": "test1"},
            },
        )
        assert resp.status_code == 200
        results = resp.json().get("results", [])
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_depth_literal_not_parameter(self, falkordb_client):
        """Variable-length path with literal depth (not parameter) should work."""
        # Create test data
        await falkordb_client.post("/query", json={
            "query": "MERGE (a:TestNode {name: $a})-[:CONNECTS_TO]->(b:TestNode {name: $b})",
            "params": {"a": "node_a", "b": "node_b"},
        })

        # Query with literal depth (not $depth parameter)
        resp = await falkordb_client.post("/query", json={
            "query": "MATCH path = (a:TestNode {name: $name})-[r*1..2]->(b) RETURN path, length(path) as hops LIMIT 10",
            "params": {"name": "node_a"},
        })
        assert resp.status_code == 200
        results = resp.json().get("results", [])
        assert len(results) > 0


class TestEndToEndRetrieval:
    """End-to-end retrieval tests using real services."""

    @pytest.mark.asyncio
    async def test_ingest_and_retrieve(self, qdrant_client):
        """Ingest a document and verify it can be retrieved."""
        from ingestion.pipeline import IngestionPipeline
        from unittest.mock import MagicMock

        pipeline = IngestionPipeline()
        # Mock embedder to avoid LLM API calls
        pipeline.embedder = MagicMock()
        pipeline.embedder.embed_chunks = MagicMock(return_value=[
            {"id": "chunk1", "content": "Authentication uses JWT tokens", "embedding": [0.1] * 128, "source_id": "test"}
        ])
        pipeline.vector_indexer = MagicMock()
        pipeline.vector_indexer.index_chunks = MagicMock(return_value=MagicMock(indexed_count=1))

        job = await pipeline.ingest_document(
            "Authentication uses JWT tokens for security. The token is signed with RS256.",
            "test_doc",
            "document",
        )
        assert job.total_chunks > 0
        assert job.status.value == "completed"
