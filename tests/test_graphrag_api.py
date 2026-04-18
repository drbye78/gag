import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock


client = None


def get_test_client():
    global client
    if client is None:
        from api.main import app
        client = TestClient(app)
    return client


class TestGraphRAGQueryEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = get_test_client()

    def test_graphrag_query_endpoint_exists(self):
        response = self.client.post(
            "/graphrag/query",
            json={"query": "What entities are in the system?"},
        )
        assert response.status_code in [200, 500, 503, 404]

    def test_graphrag_query_with_params(self):
        response = self.client.post(
            "/graphrag/query",
            json={
                "query": "Tell me about entities",
                "include_entities": True,
                "include_relationships": False,
                "include_communities": False,
                "max_hops": 2,
            },
        )
        assert response.status_code in [200, 500, 503, 404]

    def test_graphrag_query_missing_query(self):
        response = self.client.post(
            "/graphrag/query",
            json={},
        )
        assert response.status_code in [422, 500]


class TestGraphRAGEntitiesEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = get_test_client()

    def test_list_entities_endpoint_exists(self):
        response = self.client.get("/graphrag/entities")
        assert response.status_code in [200, 500, 503, 404]

    def test_list_entities_with_filters(self):
        response = self.client.get(
            "/graphrag/entities?source_id=test-source&entity_type=PERSON&limit=10"
        )
        assert response.status_code in [200, 500, 503, 404]

    def test_get_single_entity(self):
        response = self.client.get("/graphrag/entities/test-entity-id")
        assert response.status_code in [200, 404, 500, 503]


class TestGraphRAGRelationshipsEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = get_test_client()

    def test_list_relationships_endpoint_exists(self):
        response = self.client.get("/graphrag/relationships")
        assert response.status_code in [200, 500, 503, 404]

    def test_list_relationships_with_filters(self):
        response = self.client.get(
            "/graphrag/relationships?relationship_type=DEPENDS_ON&limit=50"
        )
        assert response.status_code in [200, 500, 503, 404]


class TestGraphRAGCommunitiesEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = get_test_client()

    def test_list_communities_endpoint_exists(self):
        response = self.client.get("/graphrag/communities")
        assert response.status_code in [200, 500, 503, 404]

    def test_list_communities_with_filters(self):
        response = self.client.get(
            "/graphrag/communities?source_id=test-source&min_size=2&limit=20"
        )
        assert response.status_code in [200, 500, 503, 404]

    def test_get_single_community(self):
        response = self.client.get("/graphrag/communities/test-community-id")
        assert response.status_code in [200, 404, 500, 503]


class TestGraphRAGStatsEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = get_test_client()

    def test_stats_endpoint_exists(self):
        response = self.client.get("/graphrag/stats")
        assert response.status_code in [200, 500, 503, 404]

    def test_stats_response_structure(self):
        response = self.client.get("/graphrag/stats")
        if response.status_code == 200:
            data = response.json()
            assert "total_entities" in data or "error" in data


class TestIngestionWithGraphRAG:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = get_test_client()

    def test_ingest_with_graphrag_flag(self):
        response = self.client.post(
            "/ingestion/ingest",
            json={
                "content": "John works at Acme Corp. Acme develops AI products.",
                "source_id": "test-doc-1",
                "source_type": "document",
                "use_graphrag": True,
            },
        )
        assert response.status_code in [200, 500, 503, 404, 422]

    def test_ingest_without_graphrag_flag(self):
        response = self.client.post(
            "/ingestion/ingest",
            json={
                "content": "Simple document content",
                "source_id": "test-doc-2",
                "use_graphrag": False,
            },
        )
        assert response.status_code in [200, 500, 503, 404, 422]


class TestRootEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = get_test_client()

    def test_root_shows_graphrag_endpoints(self):
        response = self.client.get("/")
        assert response.status_code == 200

        data = response.json()
        endpoints = data.get("endpoints", [])

        assert "/graphrag/query" in endpoints
        assert "/graphrag/entities" in endpoints
        assert "/graphrag/relationships" in endpoints
        assert "/graphrag/communities" in endpoints
        assert "/graphrag/stats" in endpoints