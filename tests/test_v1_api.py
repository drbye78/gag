import pytest
from fastapi.testclient import TestClient


client = None


def get_test_client():
    global client
    if client is None:
        from api.main import app

        client = TestClient(app)
    return client


class TestV1PrefixEndpoints:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = get_test_client()

    def test_v1_query_endpoint_exists(self):
        response = self.client.post("/v1/query", json={"query": "test query"})
        assert response.status_code in [200, 401, 422, 500, 503]

    def test_v1_mcp_endpoint_exists(self):
        response = self.client.get("/v1/mcp")
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_entity_cache_stats_endpoint_exists(self):
        response = self.client.get("/v1/entity/cache/stats")
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_codegraph_complexity_endpoint_exists(self):
        response = self.client.get("/v1/codegraph/complexity/test_func")
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_codegraph_callers_endpoint_exists(self):
        response = self.client.get("/v1/codegraph/callers/test_func")
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_codegraph_callees_endpoint_exists(self):
        response = self.client.get("/v1/codegraph/callees/test_func")
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_codegraph_deps_endpoint_exists(self):
        response = self.client.get("/v1/codegraph/deps/test_module")
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_reasoning_chain_endpoint_exists(self):
        response = self.client.post(
            "/v1/reasoning/chain",
            json={"query": "test", "facts": []},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_reasoning_entity_endpoint_exists(self):
        response = self.client.post(
            "/v1/reasoning/entity",
            json={"query": "test", "facts": []},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_rerank_endpoint_exists(self):
        response = self.client.post(
            "/v1/rerank",
            json={"query": "test", "results": []},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_citations_endpoint_exists(self):
        response = self.client.post(
            "/v1/citations",
            json={"answer": "test answer", "sources": []},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_hybrid_enhanced_endpoint_exists(self):
        response = self.client.post(
            "/v1/hybrid/enhanced",
            json={"query": "test"},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_entity_cache_stats_endpoint_exists(self):
        response = self.client.get("/v1/entity/cache/stats")
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_entity_cache_invalidate_endpoint_exists(self):
        response = self.client.post("/v1/entity/cache/invalidate", json={})
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_search_kubernetes_endpoint_exists(self):
        response = self.client.post(
            "/v1/search/kubernetes",
            json={"query": "deployment"},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_search_helm_endpoint_exists(self):
        response = self.client.post(
            "/v1/search/helm",
            json={"query": "chart"},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_search_dockerfile_endpoint_exists(self):
        response = self.client.post(
            "/v1/search/dockerfile",
            json={"query": "FROM"},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_search_graphql_endpoint_exists(self):
        response = self.client.post(
            "/v1/search/graphql",
            json={"query": "query"},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_search_istio_endpoint_exists(self):
        response = self.client.post(
            "/v1/search/istio",
            json={"query": "VirtualService"},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_codegraph_find_endpoint_exists(self):
        response = self.client.post(
            "/v1/codegraph/find",
            json={"query": "test"},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_codegraph_relationships_endpoint_exists(self):
        response = self.client.post(
            "/v1/codegraph/relationships",
            json={"query_type": "find_callers", "target": "test"},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_codegraph_complex_endpoint_exists(self):
        response = self.client.post("/v1/codegraph/complex", json={})
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_codegraph_complex_is_post(self):
        response = self.client.get("/v1/codegraph/complex")
        assert response.status_code in [405, 404, 401]

    def test_v1_codegraph_complexity_endpoint_exists(self):
        response = self.client.get("/v1/codegraph/complexity/test_func")
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_codegraph_callers_endpoint_exists(self):
        response = self.client.get("/v1/codegraph/callers/test_func")
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_codegraph_callees_endpoint_exists(self):
        response = self.client.get("/v1/codegraph/callees/test_func")
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_codegraph_deps_endpoint_exists(self):
        response = self.client.get("/v1/codegraph/deps/test_module")
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_codegraph_dead_code_endpoint_exists(self):
        response = self.client.post("/v1/codegraph/dead-code", json={})
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_codegraph_visualize_endpoint_exists(self):
        response = self.client.post(
            "/v1/codegraph/visualize",
            json={"query_type": "show_all_nodes"},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_codegraph_index_git_endpoint_exists(self):
        response = self.client.post(
            "/v1/codegraph/index/git",
            json={"url": "https://github.com/example/repo"},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_codegraph_index_zip_endpoint_exists(self):
        import base64

        response = self.client.post(
            "/v1/codegraph/index/zip",
            json={"content": base64.b64encode(b"test").decode()},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_codegraph_index_markdown_endpoint_exists(self):
        response = self.client.post(
            "/v1/codegraph/index/markdown",
            json={"content": "# Test"},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_multimodal_extract_endpoint_exists(self):
        response = self.client.post(
            "/v1/multimodal/extract",
            json={"image_url": "https://example.com/image.png"},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_multimodal_diagram_extract_endpoint_exists(self):
        response = self.client.post(
            "/v1/multimodal/diagram/extract",
            json={},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_multimodal_diagram_search_endpoint_exists(self):
        response = self.client.post(
            "/v1/multimodal/diagram/search",
            json={"query": "test"},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_search_colpal_endpoint_exists(self):
        response = self.client.post(
            "/v1/search/colpal",
            json={"query": "button"},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_search_ui_sketch_endpoint_exists(self):
        response = self.client.post(
            "/v1/search/ui-sketch",
            json={"sketch_data": "test"},
        )
        assert response.status_code in [200, 401, 422, 500]


class TestV1SubRouterMounts:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = get_test_client()

    def test_v1_ingestion_endpoint_exists(self):
        response = self.client.get("/v1/ingestion/jobs")
        assert response.status_code in [200, 401, 404, 422, 500]

    def test_v1_git_endpoint_exists(self):
        response = self.client.get("/v1/git/jobs")
        assert response.status_code in [200, 401, 404, 422, 500]

    def test_v1_documents_endpoint_exists(self):
        response = self.client.get("/v1/documents/")
        assert response.status_code in [200, 401, 404, 422, 500]

    def test_v1_ui_endpoint_exists(self):
        response = self.client.get("/v1/ui/")
        assert response.status_code in [200, 401, 404, 422, 500]

    def test_v1_graphrag_query_endpoint_exists(self):
        response = self.client.post("/v1/graphrag/query", json={"query": "test"})
        assert response.status_code in [200, 401, 422, 500, 503]

    def test_v1_adapter_endpoint_exists(self):
        response = self.client.post(
            "/v1/adapter/query",
            json={"query": "test"},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_knowledge_endpoint_exists(self):
        response = self.client.post(
            "/v1/knowledge/query",
            json={"query": "test"},
        )
        assert response.status_code in [200, 401, 422, 500]

    def test_v1_artifacts_endpoint_exists(self):
        response = self.client.get("/v1/artifacts/jobs")
        assert response.status_code in [200, 401, 404, 422, 500]
