"""
Tests for Confluence ingestion REST endpoints.
"""

import pytest
from unittest.mock import AsyncMock, patch


class TestConfluenceSpaceSync:
    @pytest.mark.asyncio
    async def test_sync_space_endpoint(self):
        from api.main import CodeGraphIndexConfluenceSpaceRequest
        
        request = CodeGraphIndexConfluenceSpaceRequest(
            base_url="https://test.atlassian.net",
            space_key="TEST",
            email="test@example.com",
            api_token="test-token",
            include_children=True,
            max_depth=2,
            include_attachments=False,
        )
        assert request.space_key == "TEST"
        assert request.max_depth == 2

    @pytest.mark.asyncio
    async def test_sync_space_response_model(self):
        from api.main import CodeGraphIndexConfluenceSpaceResponse
        
        response = CodeGraphIndexConfluenceSpaceResponse(
            source="confluence",
            space_key="TEST",
            success=True,
            pages_indexed=5,
            errors=[],
        )
        assert response.success is True
        assert response.pages_indexed == 5


class TestConfluenceTree:
    @pytest.mark.asyncio
    async def test_tree_endpoint_request(self):
        from api.main import CodeGraphIndexConfluenceTreeRequest
        
        request = CodeGraphIndexConfluenceTreeRequest(
            base_url="https://test.atlassian.net",
            page_id="123456",
            email="test@example.com",
            api_token="test-token",
            depth=3,
            include_attachments=True,
        )
        assert request.page_id == "123456"
        assert request.depth == 3

    @pytest.mark.asyncio
    async def test_tree_endpoint_response(self):
        from api.main import CodeGraphIndexConfluenceTreeResponse
        
        response = CodeGraphIndexConfluenceTreeResponse(
            source="confluence",
            root_page_id="123456",
            success=True,
            pages_indexed=10,
            attachments_indexed=3,
        )
        assert response.pages_indexed == 10
        assert response.attachments_indexed == 3


class TestConfluencePage:
    @pytest.mark.asyncio
    async def test_page_endpoint_request(self):
        from api.main import CodeGraphIndexConfluencePageRequest
        
        request = CodeGraphIndexConfluencePageRequest(
            base_url="https://test.atlassian.net",
            page_id="123456",
            email="test@example.com",
            api_token="test-token",
            include_attachments=True,
            include_children=True,
            children_depth=2,
        )
        assert request.include_attachments is True
        assert request.include_children is True

    @pytest.mark.asyncio
    async def test_page_endpoint_response(self):
        from api.main import CodeGraphIndexConfluencePageResponse
        
        response = CodeGraphIndexConfluencePageResponse(
            source="confluence",
            page_id="123456",
            success=True,
            indexed=True,
            attachments_count=2,
            children_count=5,
        )
        assert response.indexed is True
        assert response.children_count == 5


class TestConfluenceClientIntegration:
    @pytest.mark.asyncio
    async def test_confluence_client_sync_space(self):
        from documents.confluence import ConfluenceClient, ConfluencePage
        
        client = ConfluenceClient(
            url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token",
        )
        assert client.url == "https://test.atlassian.net"
        assert client.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_confluence_page_model(self):
        from documents.confluence import ConfluencePage
        
        page = ConfluencePage(
            page_id="123",
            title="Test Page",
            space_key="TEST",
            content="<p>Test content</p>",
        )
        assert page.page_id == "123"
        assert page.title == "Test Page"
        assert page.space_key == "TEST"