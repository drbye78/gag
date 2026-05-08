import os

from embeddings.service import EmbeddingService

EmbeddingPipeline = EmbeddingService

_pipeline: EmbeddingService | None = None


def get_embedding_pipeline() -> EmbeddingService:
    global _pipeline
    if _pipeline is None:
        provider = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
        _pipeline = EmbeddingService(provider=provider)
    return _pipeline


class EmbedderProvider(str):
    OPENAI = "openai"
    QWEN = "qwen"
    OLLAMA = "ollama"
    QDRANT = "qdrant"


def get_text_embedder() -> EmbeddingService:
    return get_embedding_pipeline()


def get_embedder() -> EmbeddingService:
    return get_embedding_pipeline()
