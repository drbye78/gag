import pytest
import asyncio
import os

os.environ.setdefault("JWT_SECRET", "test")
os.environ.setdefault("CREDENTIAL_ENCRYPT_KEY", "12345678")
os.environ.setdefault("LLM_API_KEY", "")
os.environ.setdefault("VLM_PROVIDER", "openrouter")
os.environ.setdefault("VLM_MODEL", "google/gemma-4-31b-it:free")
os.environ.setdefault("OPENAI_API_KEY", "")

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def falkordb_pool():
    from core.pool import HttpPool
    pool = HttpPool(base_url="http://localhost:6379")
    await pool.start()
    yield pool
    await pool.close()


@pytest.fixture(scope="session")
def qdrant_client():
    from qdrant_client import QdrantClient
    return QdrantClient(host="localhost", port=6333)


@pytest.fixture(scope="session")
def ollama_client():
    import httpx
    return httpx.Client(base_url="http://localhost:11434")


@pytest.fixture(scope="session")
def mock_embeddings():
    def _embed(texts):
        import hashlib
        dim = 1024
        return [list(
            (int(hashlib.sha256(t.encode()).hexdigest(),) * dim 
            for t in texts
        )]
    return _embed


@pytest.fixture(scope="session")
def mock_llm_response():
    return "Mock LLM response for testing"


@pytest.fixture(scope="session")
def mock_vlm_response():
    return {"content": "Mock VLM extraction result"}


@pytest.fixture(autouse=True)
def reset_settings():
    from core.config import reset_settings
    yield
    reset_settings()