"""
README claim: "Tooling Search: Kubernetes, Helm, Docker, GraphQL, Istio"
Source: README.md line 130
"""
import pytest
import importlib


@pytest.mark.claim
@pytest.mark.parametrize("tooling_type", ["kubernetes", "helm", "dockerfile", "graphql", "istio"])
def test_tooling_retriever_exists(tooling_type):
    module = importlib.import_module(f"retrieval.tooling.{tooling_type}")
    getter_name = f"get_{tooling_type}_retriever"
    assert hasattr(module, getter_name), f"Module retrieval.tooling.{tooling_type} missing {getter_name}"


@pytest.mark.claim
def test_tooling_search_endpoints_exist():
    from api.main import app
    routes = [r.path for r in app.routes]
    expected = ["/search/kubernetes", "/search/helm", "/search/dockerfile", "/search/graphql", "/search/istio"]
    for endpoint in expected:
        assert endpoint in routes, f"Endpoint {endpoint} not found in API routes"
