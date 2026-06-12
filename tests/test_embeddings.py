from unittest.mock import AsyncMock, patch

import pytest


class TestEmbeddingService:
    def test_init_default_provider(self, monkeypatch):
        monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
        from embeddings.service import EmbeddingService

        service = EmbeddingService()
        assert service.provider == "openai"
        assert service.model == "text-embedding-3-small"
        assert service.dimensions == 1536

    def test_init_qwen_provider(self):
        from embeddings.service import EmbeddingService

        service = EmbeddingService(provider="qwen")
        assert service.provider == "qwen"
        assert service.model == "text-embedding-v3"
        assert service.dimensions == 1024

    def test_init_ollama_provider(self):
        from embeddings.service import EmbeddingService

        service = EmbeddingService(provider="ollama")
        assert service.provider == "ollama"
        assert service.model == "bge-m3:latest"
        assert service.dimensions == 1024

    def test_text_hash(self):
        from embeddings.service import EmbeddingService

        service = EmbeddingService()
        hash1 = service._text_hash("hello world")
        hash2 = service._text_hash("hello world")
        hash3 = service._text_hash("different text")

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64

    def test_cache_operations(self):
        from embeddings.service import EmbeddingService

        service = EmbeddingService(cache_capacity=10, cache_ttl=3600)
        text_hash = service._text_hash("test text")

        assert service._cache_get(text_hash) is None

        test_embedding = [0.1, 0.2, 0.3]
        service._cache_put(text_hash, test_embedding)

        cached = service._cache_get(text_hash)
        assert cached == test_embedding

    def test_cache_eviction(self):
        from embeddings.service import EmbeddingService

        service = EmbeddingService(cache_capacity=2)
        hash1 = service._text_hash("text1")
        hash2 = service._text_hash("text2")
        hash3 = service._text_hash("text3")

        service._cache_put(hash1, [0.1])
        service._cache_put(hash2, [0.2])

        assert len(service._embedding_cache) == 2

        service._cache_put(hash3, [0.3])

        assert len(service._embedding_cache) == 2

    def test_cache_stats(self):
        from embeddings.service import EmbeddingService

        service = EmbeddingService(cache_capacity=100, cache_ttl=86400)
        stats = service.get_cache_stats()

        assert stats["size"] == 0
        assert stats["capacity"] == 100
        assert stats["ttl_seconds"] == 86400

    @pytest.mark.asyncio
    async def test_embed_empty_text(self):
        from embeddings.service import EmbeddingService

        service = EmbeddingService(provider="openai")
        service.embed_batch = AsyncMock(return_value=[])
        result = await service.embed("")
        assert result == []

    @pytest.mark.asyncio
    async def test_embed_batch_empty(self):
        from embeddings.service import EmbeddingService

        service = EmbeddingService()
        result = await service.embed_batch([])
        assert result == []


class TestEmbeddingServiceProviders:
    @pytest.mark.asyncio
    async def test_embed_openai_mock(self):
        from embeddings.service import EmbeddingService

        service = EmbeddingService(provider="openai")

        with patch.object(service, "_embed_openai", return_value=[[0.1, 0.2, 0.3]]):
            result = await service.embed("test")
            assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_embed_qwen_mock(self):
        from embeddings.service import EmbeddingService

        service = EmbeddingService(provider="qwen")

        with patch.object(service, "_embed_qwen", return_value=[[0.1, 0.2, 0.3]]):
            result = await service.embed("test")
            assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_embed_openrouter_mock(self):
        from embeddings.service import EmbeddingService

        service = EmbeddingService(provider="openrouter")

        with patch.object(service, "_embed_openrouter", return_value=[[0.1, 0.2, 0.3]]):
            result = await service.embed("test")
            assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_embed_batch_mock(self):
        from embeddings.service import EmbeddingService

        service = EmbeddingService(provider="openai")

        mock_embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        with patch.object(service, "_embed_openai", return_value=mock_embeddings):
            result = await service.embed_batch(["text1", "text2", "text3"])
            assert result == mock_embeddings


class TestEmbeddingServiceChunks:
    @pytest.mark.asyncio
    async def test_embed_chunks_empty(self):
        from embeddings.service import EmbeddingService

        service = EmbeddingService()
        result = await service.embed_chunks([])
        assert result == []

    @pytest.mark.asyncio
    async def test_embed_chunks(self):
        from embeddings.service import EmbeddingService

        service = EmbeddingService(provider="openai")

        mock_embeddings = [[0.1, 0.2], [0.3, 0.4]]
        chunks = [
            {"content": "chunk1", "metadata": {"id": 1}},
            {"content": "chunk2", "metadata": {"id": 2}},
        ]

        with patch.object(service, "_embed_openai", return_value=mock_embeddings):
            result = await service.embed_chunks(chunks)

            assert len(result) == 2
            assert result[0]["embedding"] == [0.1, 0.2]
            assert result[0]["content"] == "chunk1"
            assert result[0]["provider"] == "openai"
            assert result[1]["embedding"] == [0.3, 0.4]
            assert result[1]["content"] == "chunk2"


class TestGetEmbeddingService:
    def test_get_embedding_service_singleton(self):
        from embeddings import get_embedding_service

        service1 = get_embedding_service()
        service2 = get_embedding_service()

        assert service1 is service2

    def test_get_embedding_service_import(self):
        from embeddings import EmbeddingService

        service = EmbeddingService()
        assert service is not None
        assert hasattr(service, "embed")
        assert hasattr(service, "embed_batch")


class TestEmbeddingProvider:
    def test_provider_enum(self):
        from embeddings.service import EmbeddingProvider

        assert EmbeddingProvider.OPENAI == "openai"
        assert EmbeddingProvider.QWEN == "qwen"
        assert EmbeddingProvider.OLLAMA == "ollama"
        assert EmbeddingProvider.OPENROUTER == "openrouter"
