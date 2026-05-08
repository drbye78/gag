"""
Embeddings module - Standalone embedding service with provider abstraction.

Provides:
- EmbeddingService: Main service class for embedding generation
- Provider abstraction: OpenAI, Qwen, Ollama, OpenRouter
- Connection pooling and caching
- Language-aware model selection
"""

from embeddings.service import EmbeddingService, get_embedding_service

__all__ = [
    "EmbeddingService",
    "get_embedding_service",
]
