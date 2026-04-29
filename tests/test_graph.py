import pytest


class TestFalkorDBClientConnection:
    def test_client_import(self):
        from graph.client import FalkorDBClient
        assert FalkorDBClient is not None

    def test_client_instantiation(self):
        from graph.client import FalkorDBClient
        client = FalkorDBClient()
        assert client is not None


class TestCypherBuilder:
    def test_cypher_builder_import(self):
        from graph.cypher_builder import CypherBuilder
        assert CypherBuilder is not None


class TestGraphQueries:
    def test_client_query_method(self):
        from graph.client import FalkorDBClient
        client = FalkorDBClient()
        hasattr(client, 'query') or hasattr(client, 'execute')