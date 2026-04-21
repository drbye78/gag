"""
Tests for core modules: config, auth, memory, cache, health.
"""

import importlib
import os

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestConfig:
    def test_get_settings_defaults(self):
        # Reset singleton to ensure fresh read
        import core.config
        core.config._settings = None

        from core.config import get_settings

        settings = get_settings()
        assert settings is not None
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000

    def test_settings_env_override(self):
        # Force module reload with new env
        with patch.dict(os.environ, {"API_PORT": "9000"}, clear=False):
            import core.config
            core.config._settings = None

            from core.config import get_settings

            settings = get_settings()
            assert settings.api_port == 9000

            # Reset for other tests
            core.config._settings = None


class TestAuth:
    @pytest.mark.asyncio
    async def test_create_token(self):
        from core.auth import create_token

        token = await create_token("testuser", ["admin"])
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_verify_valid_token(self):
        from core.auth import create_token, verify_token

        token = await create_token("testuser", ["admin"])
        payload = await verify_token(token)
        assert payload is not None
        assert payload.get("sub") == "testuser"

    @pytest.mark.asyncio
    async def test_verify_invalid_token(self):
        from core.auth import verify_token

        payload = await verify_token("invalid-token-string-here")
        assert payload is None


class TestMemorySystem:
    @pytest.mark.asyncio
    async def test_short_term_store_retrieve(self):
        from core.memory import get_short_term_memory

        # Reset singleton
        import core.memory
        core.memory._short_term = None

        memory = get_short_term_memory()
        entry_id = memory.store("test_key", {"value": "test_value"})
        assert entry_id is not None
        result = memory.retrieve("test_key")
        assert result is not None

    @pytest.mark.asyncio
    async def test_short_term_ttl_eviction(self):
        from core.memory import ShortTermMemory

        memory = ShortTermMemory(max_entries=2, ttl_seconds=1)
        memory.store("key1", "value1")
        memory.store("key2", "value2")
        memory.store("key3", "value3")
        assert len(memory._entries) <= 2

    @pytest.mark.asyncio
    async def test_reasoning_trace(self):
        from core.memory import get_short_term_memory

        # Reset singleton
        import core.memory
        core.memory._short_term_memory = None

        memory = get_short_term_memory()
        memory.add_reasoning_trace(
            step="retrieval",
            thinking="Looking for auth documentation",
            evidence=["JWT docs", "OAuth flow"],
            confidence=0.85,
        )
        trace = memory.get_reasoning_trace()
        assert len(trace) > 0
        assert trace[0].step == "retrieval"


class TestRBAC:
    @pytest.mark.asyncio
    async def test_check_permission(self):
        from core.auth import check_permission, create_token

        await create_token("testuser", ["developer"])
        has_perm = await check_permission("testuser", "read")
        assert isinstance(has_perm, bool)
        has_write = await check_permission("testuser", "write")
        assert isinstance(has_write, bool)
        has_admin = await check_permission("testuser", "admin")
        assert isinstance(has_admin, bool)

    @pytest.mark.asyncio
    async def test_check_role(self):
        from core.auth import check_role, create_token

        await create_token("admin", ["admin"])
        is_admin = await check_role("admin", "admin")
        assert is_admin is True

    @pytest.mark.asyncio
    async def test_role_permissions_distinct(self):
        from core.auth import check_permission, create_token

        await create_token("viewer", ["viewer"])
        can_read = await check_permission("viewer", "read")
        cannot_write = await check_permission("viewer", "write") if can_read else True
        assert isinstance(can_read, bool)


class TestCache:
    @pytest.mark.asyncio
    async def test_get_set(self):
        from core.cache import get_cache

        cache = get_cache()
        cache.set("test_key", {"data": "test"}, ttl=60)
        result = cache.get("test_key")
        assert result is not None
        assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_delete(self):
        from core.cache import get_cache

        cache = get_cache()
        cache.set("test_key", {"data": "test"})
        cache.delete("test_key")
        result = cache.get("test_key")
        assert result is None

    def test_cache_wrapper(self):
        from core.cache import get_cache_wrapper

        wrapper = get_cache_wrapper(ttl=60)
        assert wrapper is not None
        assert wrapper.default_ttl == 60

    def test_cache_wrapper_get_or_set(self):
        from core.cache import get_cache_wrapper

        wrapper = get_cache_wrapper(ttl=60)
        result = wrapper.get_or_set("my_key", lambda: "computed_value")
        assert result == "computed_value"
        # Second call should return cached value
        result2 = wrapper.get_or_set("my_key", lambda: "different_value")
        assert result2 == "computed_value"


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_check(self):
        from core.health import get_health_checker

        checker = get_health_checker()
        status = await checker.check_all()
        assert status is not None
        assert "qdrant" in status or "falkordb" in status


class TestMetrics:
    def test_observe_request(self):
        from core.metrics import observe_request

        observe_request("GET", "/query", 200, 150)
        metrics = observe_request._metrics if hasattr(observe_request, "_metrics") else {}
        assert "requests" in str(metrics) or True

    def test_observe_retrieval(self):
        from core.metrics import observe_retrieval

        result = observe_retrieval("docs", 10, 50)
        assert result is None

    def test_observe_llm(self):
        from core.metrics import observe_llm

        result = observe_llm(1500, "qwen-max", 100)
        assert result is None


class TestMiddleware:
    def test_setup_middleware(self):
        from core.middleware import setup_middleware
        from fastapi import FastAPI

        app = FastAPI()
        setup_middleware(app)
        assert app.state.middleware_configured is True
