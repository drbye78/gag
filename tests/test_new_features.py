"""
Tests for entity graph cache, LLM router, extended config, tools, and API validation.
"""

import time

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Entity Graph Cache
# ---------------------------------------------------------------------------


class TestEntityGraphCache:
    def test_put_and_get(self):
        from retrieval.entity_cache import EntityGraphCache, EntityGraphCacheEntry

        cache = EntityGraphCache(capacity=3, default_ttl=60)
        entry = EntityGraphCacheEntry(
            entity_name="AuthService",
            relations=[{"target": "APIGateway"}],
        )
        cache.put("AuthService", entry)

        result = cache.get("AuthService")
        assert result is not None
        assert result.entity_name == "AuthService"
        assert result.hit_count == 1

    def test_cache_miss(self):
        from retrieval.entity_cache import EntityGraphCache

        cache = EntityGraphCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_ttl_expiry(self):
        from retrieval.entity_cache import EntityGraphCache, EntityGraphCacheEntry

        cache = EntityGraphCache(default_ttl=0)  # 0 TTL = immediately expired
        entry = EntityGraphCacheEntry(entity_name="Test", ttl=0)
        cache.put("Test", entry)
        # Small sleep to ensure time advances
        import time as _time
        _time.sleep(0.01)
        result = cache.get("Test")
        assert result is None

    def test_lru_eviction(self):
        from retrieval.entity_cache import EntityGraphCache, EntityGraphCacheEntry

        cache = EntityGraphCache(capacity=2, default_ttl=3600)
        cache.put("A", EntityGraphCacheEntry(entity_name="A"))
        cache.put("B", EntityGraphCacheEntry(entity_name="B"))
        cache.put("C", EntityGraphCacheEntry(entity_name="C"))  # should evict A

        assert cache.get("A") is None
        assert cache.get("B") is not None
        assert cache.get("C") is not None

    def test_lru_touch_moves_to_end(self):
        from retrieval.entity_cache import EntityGraphCache, EntityGraphCacheEntry

        cache = EntityGraphCache(capacity=2, default_ttl=3600)
        cache.put("A", EntityGraphCacheEntry(entity_name="A"))
        cache.put("B", EntityGraphCacheEntry(entity_name="B"))
        # Access A to move it to end (most recently used)
        cache.get("A")
        # Now add C — should evict B (least recently used)
        cache.put("C", EntityGraphCacheEntry(entity_name="C"))

        assert cache.get("A") is not None
        assert cache.get("B") is None
        assert cache.get("C") is not None

    def test_invalidate(self):
        from retrieval.entity_cache import EntityGraphCache, EntityGraphCacheEntry

        cache = EntityGraphCache()
        cache.put("Test", EntityGraphCacheEntry(entity_name="Test"))
        assert cache.invalidate("Test") is True
        assert cache.get("Test") is None
        assert cache.invalidate("NonExistent") is False

    def test_invalidate_by_prefix(self):
        from retrieval.entity_cache import EntityGraphCache, EntityGraphCacheEntry

        cache = EntityGraphCache()
        cache.put("Auth:Service", EntityGraphCacheEntry(entity_name="Auth:Service"))
        cache.put("Auth:Gateway", EntityGraphCacheEntry(entity_name="Auth:Gateway"))
        cache.put("Other:Thing", EntityGraphCacheEntry(entity_name="Other:Thing"))

        count = cache.invalidate_by_prefix("Auth:")
        assert count == 2
        assert cache.get("Auth:Service") is None
        assert cache.get("Auth:Gateway") is None
        assert cache.get("Other:Thing") is not None

    def test_clear(self):
        from retrieval.entity_cache import EntityGraphCache, EntityGraphCacheEntry

        cache = EntityGraphCache()
        cache.put("A", EntityGraphCacheEntry(entity_name="A"))
        cache.put("B", EntityGraphCacheEntry(entity_name="B"))
        cache.get("A")  # generate a hit
        cache.clear()

        stats = cache.get_stats()
        assert stats["size"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_get_stats(self):
        from retrieval.entity_cache import EntityGraphCache, EntityGraphCacheEntry

        cache = EntityGraphCache(capacity=100, default_ttl=3600)
        cache.put("Test", EntityGraphCacheEntry(entity_name="Test"))
        cache.get("Test")
        cache.get("Missing")

        stats = cache.get_stats()
        assert stats["size"] == 1
        assert stats["capacity"] == 100
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
        assert stats["utilization_pct"] == 1.0
        assert stats["oldest_entry"] is not None

    def test_hit_rate_property(self):
        from retrieval.entity_cache import EntityGraphCache

        cache = EntityGraphCache()
        assert cache.hit_rate == 0.0
        cache.get("x")  # miss
        cache.get("y")  # miss
        assert cache.hit_rate == 0.0

    def test_entry_to_dict(self):
        from retrieval.entity_cache import EntityGraphCacheEntry

        entry = EntityGraphCacheEntry(entity_name="Test", relations=[{"id": 1}])
        d = entry.to_dict()
        assert d["entity_name"] == "Test"
        assert "is_expired" in d
        assert "hit_count" in d
        assert "ttl" in d

    def test_singleton_accessor(self):
        from retrieval.entity_cache import get_entity_graph_cache

        cache = get_entity_graph_cache()
        assert cache is not None
        assert get_entity_graph_cache() is cache  # same instance


# ---------------------------------------------------------------------------
# LLM Router
# ---------------------------------------------------------------------------


class TestLLMRouter:
    def test_router_uses_settings(self):
        with patch("llm.router.get_settings") as mock_settings:
            mock = MagicMock()
            mock.llm_provider = "openrouter"
            mock.llm_model = "qwen-max"
            mock.llm_api_key = "test-key"
            mock_settings.return_value = mock

            from llm.router import LLMRouter
            router = LLMRouter()
            assert router.provider.value == "openrouter"
            assert router.model.value == "qwen-max"
            assert router.api_key == "test-key"

    @pytest.mark.asyncio
    async def test_chat_raises_on_no_api_key(self):
        from llm.router import LLMRouter, LLMProvider

        router = LLMRouter(
            provider=LLMProvider.OPENROUTER,
            api_key="",  # No key
        )
        with pytest.raises(Exception):
            await router.chat("test")

    def test_build_headers(self):
        from llm.router import LLMRouter, LLMProvider

        router = LLMRouter(provider=LLMProvider.OPENROUTER, api_key="test")
        headers = router._build_headers()
        assert headers["Authorization"] == "Bearer test"
        assert headers["Content-Type"] == "application/json"

    def test_build_messages_with_system(self):
        from llm.router import LLMRouter

        router = LLMRouter()
        msgs = router._build_messages("hello", system_prompt="be helpful")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"

    def test_build_messages_without_system(self):
        from llm.router import LLMRouter

        router = LLMRouter()
        msgs = router._build_messages("hello")
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"


# ---------------------------------------------------------------------------
# Extended Config
# ---------------------------------------------------------------------------


class TestConfigExtended:
    def test_all_new_settings_exist(self):
        from core.config import get_settings, reset_settings
        reset_settings()

        s = get_settings()
        # Spot-check new fields
        assert hasattr(s, "falkordb_user")
        assert hasattr(s, "openai_api_key")
        assert hasattr(s, "dashscope_api_key")
        assert hasattr(s, "confluence_url")
        assert hasattr(s, "webdav_url")
        assert hasattr(s, "stackoverflow_api_key")
        assert hasattr(s, "credential_encrypt_key")
        assert hasattr(s, "embedding_provider")
        assert hasattr(s, "cohere_api_key")
        assert hasattr(s, "jina_api_key")
        assert hasattr(s, "prometheus_user")
        assert hasattr(s, "elastic_api_key")
        assert hasattr(s, "loki_url")
        assert hasattr(s, "vlm_provider")
        assert hasattr(s, "anthropic_api_key")
        assert hasattr(s, "ollama_host")
        assert hasattr(s, "qwen_api_key")
        assert hasattr(s, "gitlab_token")
        assert hasattr(s, "azure_devops_username")
        assert hasattr(s, "azure_devops_token")
        assert hasattr(s, "forum_base_url")
        assert hasattr(s, "forum_api_key")
        assert hasattr(s, "requirements_path")
        assert hasattr(s, "elastic_api_key")

    def test_reset_settings(self):
        from core.config import get_settings, reset_settings

        old = get_settings()
        reset_settings()
        new = get_settings()
        assert old is not new  # different instance after reset

    def test_settings_validate_warning(self):
        from core.config import Settings
        import warnings as w
        import os

        os.environ.pop("JWT_SECRET", None)
        os.environ.pop("CREDENTIAL_ENCRYPT_KEY", None)
        with w.catch_warnings(record=True) as caught:
            w.simplefilter("always")
            Settings()
            jwt_warnings = [x for x in caught if "JWT_SECRET" in str(x.message)]
            assert len(jwt_warnings) >= 1

    def test_settings_validate_no_warning_with_custom_secret(self):
        from core.config import Settings, reset_settings
        import warnings as w
        import os

        reset_settings()
        os.environ["JWT_SECRET"] = "super-secret-key-12345"
        os.environ["CREDENTIAL_ENCRYPT_KEY"] = "test-encrypt-key-32-chars!!"
        try:
            with w.catch_warnings(record=True) as caught:
                w.simplefilter("always")
                Settings()
                jwt_warnings = [x for x in caught if "JWT_SECRET" in str(x.message)]
                assert len(jwt_warnings) == 0
        finally:
            os.environ.pop("JWT_SECRET", None)
            os.environ.pop("CREDENTIAL_ENCRYPT_KEY", None)

    def test_settings_defaults(self):
        from core.config import get_settings, reset_settings
        reset_settings()

        s = get_settings()
        assert s.qdrant_port == 6333
        assert s.falkordb_port == 7379
        assert s.llm_provider == "openrouter"
        assert s.embedding_provider == "openai"
        assert s.rerank_provider == "cohere"
        assert s.citation_style == "parenthetical"
        assert s.rate_limit_requests == 100
        assert s.max_workers == 4
        assert s.entity_aware_max_hops == 3
        assert s.iterative_max_iterations == 3


# ---------------------------------------------------------------------------
# Tools / Tool Registry
# ---------------------------------------------------------------------------


class TestToolRegistry:
    @pytest.mark.asyncio
    async def test_registry_has_default_tools(self):
        from tools.base import get_tool_registry

        registry = get_tool_registry()
        tools = registry.list_tools()
        names = [t["name"] for t in tools]
        assert "search" in names
        assert "hybrid_search" in names
        assert "rerank" in names
        assert "chain_reasoning" in names
        assert "entity_search" in names

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self):
        from tools.base import get_tool_registry

        registry = get_tool_registry()
        result = await registry.execute("nonexistent_tool", {})
        assert result.error is not None
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_execute_with_invalid_input(self):
        from tools.base import get_tool_registry

        registry = get_tool_registry()
        result = await registry.execute("search", {"query": ""})
        # Should not crash — either returns error or executes
        assert result is not None

    @pytest.mark.asyncio
    async def test_batch_execution(self):
        from tools.base import get_tool_registry

        registry = get_tool_registry()
        calls = [
            {"name": "nonexistent", "arguments": {}},
            {"name": "search", "arguments": {"query": "test"}},
        ]
        results = await registry.execute_batch(calls)
        assert len(results) == 2
        assert results[0].error is not None

    def test_list_resources(self):
        from tools.base import get_tool_registry

        registry = get_tool_registry()
        resources = registry.list_resources()
        assert isinstance(resources, list)

    def test_list_prompts(self):
        from tools.base import get_tool_registry

        registry = get_tool_registry()
        prompts = registry.list_prompts()
        assert isinstance(prompts, list)


# ---------------------------------------------------------------------------
# API Input Validation
# ---------------------------------------------------------------------------


class TestAPIInputValidation:
    def test_query_request_rejects_empty(self):
        from api.main import QueryRequest
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="query must not be empty"):
            QueryRequest(query="")

        with pytest.raises(ValidationError, match="query must not be empty"):
            QueryRequest(query="   ")

    def test_query_request_strips_whitespace(self):
        from api.main import QueryRequest

        req = QueryRequest(query="  hello  ")
        assert req.query == "hello"

    def test_reasoning_request_rejects_empty(self):
        from api.main import ReasoningRequest
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="query must not be empty"):
            ReasoningRequest(query="", facts=[])

    def test_rerank_request_rejects_empty(self):
        from api.main import RerankRequest
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="query must not be empty"):
            RerankRequest(query="", results=[])

    def test_citation_request_rejects_empty(self):
        from api.main import CitationRequest
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="answer must not be empty"):
            CitationRequest(answer="", sources=[])

    def test_image_extraction_rejects_empty_url(self):
        from api.main import ImageExtractionRequest
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="image_url must not be empty"):
            ImageExtractionRequest(image_url="")

    def test_valid_requests_pass(self):
        from api.main import QueryRequest, ReasoningRequest, RerankRequest

        q = QueryRequest(query="hello", limit=5)
        assert q.query == "hello"
        assert q.limit == 5

        r = ReasoningRequest(query="how?", facts=[{"content": "test"}])
        assert r.query == "how?"

        rr = RerankRequest(query="search", results=[])
        assert rr.query == "search"
