"""
Tests for RetrieverRegistry - Self-registering retriever factory.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestRetrieverRegistry:
    def test_register_and_get_retriever(self):
        from retrieval.registry import RetrieverRegistry

        registry = RetrieverRegistry()
        mock_retriever = MagicMock()

        registry.register("test", lambda: mock_retriever, "test_module")

        result = registry.get_retriever("test")
        assert result is mock_retriever

    def test_register_duplicate_warns(self):
        from retrieval.registry import RetrieverRegistry, logger

        registry = RetrieverRegistry()
        mock_retriever1 = MagicMock()
        mock_retriever2 = MagicMock()

        with patch.object(logger, "warning") as mock_warn:
            registry.register("test", lambda: mock_retriever1, "module1")
            registry.register("test", lambda: mock_retriever2, "module2")

            mock_warn.assert_called_once()
            result = registry.get_retriever("test")
            assert result is mock_retriever2

    def test_get_retriever_not_found_raises(self):
        from retrieval.registry import RetrieverRegistry

        registry = RetrieverRegistry()

        with pytest.raises(KeyError) as exc_info:
            registry.get_retriever("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert "Available" in str(exc_info.value)

    def test_list_retrievers(self):
        from retrieval.registry import RetrieverRegistry

        registry = RetrieverRegistry()
        registry.register("retriever1", lambda: MagicMock(), "module1")
        registry.register("retriever2", lambda: MagicMock(), "module2")

        retrievers = registry.list_retrievers()
        assert "retriever1" in retrievers
        assert "retriever2" in retrievers

    def test_is_registered(self):
        from retrieval.registry import RetrieverRegistry

        registry = RetrieverRegistry()
        registry.register("test", lambda: MagicMock(), "module")

        assert registry.is_registered("test") is True
        assert registry.is_registered("nonexistent") is False

    def test_get_retriever_info(self):
        from retrieval.registry import RetrieverRegistry

        registry = RetrieverRegistry()
        registry.register("test", lambda: MagicMock(), "test_module")

        info = registry.get_retriever_info()
        assert info["test"] == "test_module"

    def test_clear(self):
        from retrieval.registry import RetrieverRegistry

        registry = RetrieverRegistry()
        registry.register("test", lambda: MagicMock(), "module")

        registry.clear()

        assert registry.list_retrievers() == []
        assert registry.is_registered("test") is False


class TestGlobalRegistry:
    def test_get_registry_singleton(self):
        from retrieval.registry import get_registry

        reg1 = get_registry()
        reg2 = get_registry()

        assert reg1 is reg2

    def test_initialize_registry(self):
        from retrieval.registry import get_registry, initialize_registry

        registry = get_registry()
        registry.clear()

        initialize_registry()

        assert registry._initialized is True
        assert len(registry.list_retrievers()) > 0


class TestDecorator:
    def test_register_retriever_decorator(self):
        from retrieval.registry import get_registry

        registry = get_registry()
        original_retrievers = set(registry.list_retrievers())

        from retrieval.registry import register_retriever

        @register_retriever("decorated_test", "test_module")
        def get_test_retriever():
            return MagicMock()

        assert "decorated_test" in registry.list_retrievers()
        registry.clear()
        for r in original_retrievers:
            registry.register(r, lambda: None, "test")


class TestOrchestratorRegistryIntegration:
    def test_orchestrator_uses_registry(self):
        from retrieval.orchestrator import RetrievalOrchestrator

        orchestrator = RetrievalOrchestrator()

        assert hasattr(orchestrator, "_registry")
        assert hasattr(orchestrator, "list_retrievers")
        assert hasattr(orchestrator, "get_retriever")

    def test_orchestrator_list_retrievers(self):
        from retrieval.orchestrator import RetrievalOrchestrator

        orchestrator = RetrievalOrchestrator()
        retrievers = orchestrator.list_retrievers()

        assert isinstance(retrievers, list)
        assert len(retrievers) > 0

    def test_orchestrator_get_retriever(self):
        from retrieval.orchestrator import RetrievalOrchestrator
        from retrieval.registry import initialize_registry

        initialize_registry()
        orchestrator = RetrievalOrchestrator()

        available = orchestrator.list_retrievers()
        assert len(available) > 0, "No retrievers registered"

        retriever = orchestrator.get_retriever(available[0])
        assert retriever is not None or available[0] in ("ui", "colbert")
