import pytest
from unittest.mock import AsyncMock, patch


class TestLLMRouter:
    def test_router_import(self):
        from llm.router import LLMRouter
        assert LLMRouter is not None

    def test_router_instantiation(self):
        from llm.router import LLMRouter
        router = LLMRouter(provider="openrouter", model="qwen-max")
        assert router is not None

    def test_router_has_methods(self):
        from llm.router import LLMRouter
        router = LLMRouter(provider="openrouter", model="qwen-max")
        assert hasattr(router, '__call__') or hasattr(router, 'chat') or hasattr(router, 'generate')

    def test_router_config(self):
        from llm.router import LLMRouter
        router = LLMRouter(provider="openrouter", model="qwen-max")
        assert router.provider == "openrouter"


class TestProviderConfig:
    def test_openrouter_config(self):
        import os
        if os.getenv("LLM_API_KEY"):
            from llm.router import LLMRouter
            router = LLMRouter(provider="openrouter", model="qwen-max")
            assert router.provider == "openrouter"

    def test_model_selection(self):
        from llm.router import LLMRouter
        routers = [
            LLMRouter(provider="openrouter", model="qwen-max"),
            LLMRouter(provider="openrouter", model="qwen-small"),
        ]
        assert routers[0].model != routers[1].model


class TestTokenCounting:
    def test_llm_router_class_exists(self):
        from llm.router import LLMRouter
        assert LLMRouter is not None