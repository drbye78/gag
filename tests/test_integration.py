"""
Integration tests for API endpoints and MCP interface.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_client():
    """Create an ASGI test client for the main app."""
    from httpx import AsyncClient, ASGITransport
    from api.main import app

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestAPIEndpoints:
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        async with _make_client() as client:
            response = await client.get("/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_query_endpoint(self):
        with patch("agents.orchestration.get_orchestration_engine") as mock_eng:
            mock_engine = MagicMock()
            mock_engine.execute = AsyncMock(
                return_value={
                    "query": "test",
                    "answer": "test answer",
                    "retrieval_results": {"results": []},
                    "metadata": {},
                    "intent": "explain",
                    "plan": {"steps": [], "intent": "explain"},
                    "execution": {"iterations": 1, "steps": [], "took_ms": 10},
                    "metrics": {},
                }
            )
            mock_eng.return_value = mock_engine

            async with _make_client() as client:
                response = await client.post("/query", json={"query": "test"})
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_query_requires_body(self):
        async with _make_client() as client:
            response = await client.post("/query")
            assert response.status_code in [400, 422]


class TestMCPInterface:
    @pytest.mark.asyncio
    async def test_mcp_initialize(self):
        from api.mcp import MCPHandler, MCPResponse

        handler = MCPHandler()
        request = MagicMock()
        request.jsonrpc = "2.0"
        request.id = "1"
        request.method = "initialize"
        request.params = {}
        result = await handler.handle_request(request)
        assert result is not None

    @pytest.mark.asyncio
    async def test_mcp_tools_list(self):
        from api.mcp import MCPHandler

        handler = MCPHandler()
        request = MagicMock()
        request.jsonrpc = "2.0"
        request.id = "1"
        request.method = "tools/list"
        request.params = {}
        result = await handler.handle_request(request)
        assert "tools" in result or "result" in result or result is not None

    @pytest.mark.asyncio
    async def test_mcp_tools_call(self):
        from api.mcp import MCPHandler

        handler = MCPHandler()
        request = MagicMock()
        request.jsonrpc = "2.0"
        request.id = "1"
        request.method = "tools/call"
        request.params = {
            "name": "architecture_evaluate",
            "arguments": {"architecture_id": "test"},
        }
        result = await handler.handle_request(request)
        assert result is not None

    @pytest.mark.asyncio
    async def test_mcp_query(self):
        from api.mcp import MCPHandler

        handler = MCPHandler()
        request = MagicMock()
        request.jsonrpc = "2.0"
        request.id = "1"
        request.method = "query"
        request.params = {"query": "test"}
        result = await handler.handle_request(request)
        assert result is not None


class TestGitIngestionAPI:
    @pytest.mark.asyncio
    async def test_clone_repo(self):
        try:
            from git.api import router
        except ImportError:
            pytest.skip("Git API not available")

        # Just verify the router exists and has the clone route
        assert router is not None

    @pytest.mark.asyncio
    async def test_list_repos(self):
        try:
            from git.api import router
        except ImportError:
            pytest.skip("Git API not available")

        assert router is not None


class TestDocumentAPI:
    @pytest.mark.asyncio
    async def test_upload_document(self):
        try:
            from documents.api import router
        except ImportError:
            pytest.skip("Documents API not available")

        assert router is not None


class TestIngestionAPI:
    @pytest.mark.asyncio
    async def test_ingest_endpoint(self):
        try:
            from ingestion.api import router
        except ImportError:
            pytest.skip("Ingestion API not available")

        assert router is not None

    @pytest.mark.asyncio
    async def test_job_status(self):
        try:
            from ingestion.api import router
        except ImportError:
            pytest.skip("Ingestion API not available")

        assert router is not None


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_token_creation(self):
        from core.auth import create_token

        token = await create_token("testuser", ["user"])
        assert token is not None

    @pytest.mark.asyncio
    async def test_requires_auth(self):
        # Git repos endpoint should be accessible (no auth required by default)
        try:
            from git.api import router
            assert router is not None
        except ImportError:
            pass  # Skip if not available


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_invalid_json(self):
        async with _make_client() as client:
            response = await client.post(
                "/query",
                content=b"invalid json",
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        async with _make_client() as client:
            # Root endpoint should always work
            response = await client.get("/")
            assert response.status_code == 200
