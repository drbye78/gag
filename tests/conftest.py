"""
Test fixtures and configuration for Engineering Intelligence System.

Provides:
- Mock providers for external services (Qdrant, FalkorDB, Redis, LLM)
- Sample data for testing
- Async test helpers

Testing Pyramid Structure:
    /\       E2E (few) - full integration
   /  \      Integration (some) - real DB, mocked external APIs
  /----\     Unit (many) - all mocked
 /      \
/--------\

Use markers:
- @pytest.mark.unit - Most tests (default, all mocked)
- @pytest.mark.integration - Tests needing real DB
- @pytest.mark.e2e - Full end-to-end tests (marked slow)
- @pytest.mark.slow - Tests that take >5s
"""

# MUST be set BEFORE any imports that trigger Settings() initialization
import os
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("LOG_LEVEL", "DEBUG")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-ignore-security-warning")

import asyncio
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("LOG_LEVEL", "DEBUG")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-ignore-security-warning")


@dataclass
class MockChunk:
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MockEmbeddingResult:
    embeddings: List[List[float]]  # type: ignore[syntax]
    model: str = "test-embedding"


# type: ignore[attr-defined]
TestConfig = None


import pytest  # type: ignore[no-redef]


@dataclass
class MockSearchResult:
    results: List[MockChunk]
    total: int
    took_ms: int


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_text():
    return """
    This is a sample architecture document.
    The system uses a microservices architecture with API Gateway.
    Data is stored in PostgreSQL and cached in Redis.
    """


@pytest.fixture
def sample_code():
    return """
def calculate_total(items: List[dict]) -> float:
    total = 0.0
    for item in items:
        total += item.get('price', 0) * item.get('quantity', 1)
    return total

class OrderProcessor:
    def __init__(self, validator):
        self.validator = validator
    
    def process(self, order):
        if not self.validator.validate(order):
            raise ValueError("Invalid order")
        return {"status": "processed", "order": order}
"""


@pytest.fixture
def sample_architecture():
    return """
The system consists of:
- API Gateway (port 8000)
- Auth Service (port 8001)  
- User Service (port 8002)
- Order Service (port 8003)
- Database (PostgreSQL on port 5432)
- Cache (Redis on port 6379)
"""


@pytest.fixture
def sample_queries():
    return [
        "How does the authentication flow work?",
        "What's the database schema for users?",
        "Why is the API slow?",
        "Design a new notification service",
        "Explain the microservices architecture",
    ]


@pytest.fixture
def sample_intents():
    return [
        ("How does auth work?", "EXPLAIN"),
        ("Why is it slow?", "TROUBLESHOOT"),
        ("Design a new service", "DESIGN"),
        ("Optimize the cache", "OPTIMIZE"),
    ]


@pytest.fixture
def mock_qdrant():
    mock = MagicMock()
    mock.search = AsyncMock(
        return_value=MockSearchResult(
            results=[
                MockChunk(
                    id="1",
                    content="Authentication uses JWT tokens",
                    metadata={"source": "docs"},
                ),
                MockChunk(
                    id="2",
                    content="OAuth 2.0 is supported",
                    metadata={"source": "docs"},
                ),
            ],
            total=2,
            took_ms=10,
        )
    )
    mock.index = AsyncMock(return_value={"indexed": 2, "errors": []})
    mock.create_collection = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_falkordb():
    mock = MagicMock()
    mock.query = AsyncMock(
        return_value={
            "nodes": [
                {"id": "api_gateway", "type": "service", "properties": {"port": 8000}},
                {"id": "auth_service", "type": "service", "properties": {"port": 8001}},
            ],
            "edges": [
                {"from": "api_gateway", "to": "auth_service", "type": "calls"},
            ],
        }
    )
    mock.create_node = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_redis():
    mock = MagicMock()
    mock.get = AsyncMock(return_value=b'{"cached": true}')
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.exists = AsyncMock(return_value=1)
    return mock


@pytest.fixture
def mock_llm():
    mock = MagicMock()
    mock.complete = AsyncMock(
        return_value="""
    The authentication flow works as follows:
    1. Client sends credentials to /auth/login
    2. Server validates credentials
    3. Server returns JWT token
    4. Client includes token in Authorization header
    """
    )
    mock.embed = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    return mock


@pytest.fixture
def mock_embedding_provider():
    mock = MagicMock()
    mock.embed = AsyncMock(
        return_value=MockEmbeddingResult(
            embeddings=[[0.1] * 512],
            model="test-embedding",
        )
    )
    return mock


@pytest.fixture
def mock_http_client():
    mock = MagicMock()
    mock.get = AsyncMock(
        return_value=MagicMock(
            status_code=200,
            json=MagicMock(return_value={"status": "ok"}),
        )
    )
    mock.post = AsyncMock(
        return_value=MagicMock(
            status_code=201,
            json=MagicMock(return_value={"id": "new-id"}),
        )
    )
    mock.put = AsyncMock(
        return_value=MagicMock(
            status_code=200,
            json=MagicMock(return_value={"status": "created"}),
        )
    )
    return mock


@pytest.fixture
def mock_context():
    return {
        "query": "How does authentication work?",
        "ir_context": {},
        "retrieval_results": {},
        "tool_results": [],
        "intent": "EXPLAIN",
    }


@pytest.fixture
def mock_execution_state():
    return {
        "query": "test query",
        "answer": "test answer",
        "intent": "EXPLAIN",
        "plan": {"steps": []},
        "execution": {
            "iterations": 1,
            "steps": [],
            "took_ms": 100,
        },
    }


@pytest.fixture
def mock_retrieval_results():
    return {
        "docs": [
            {"id": "1", "content": "JWT token documentation", "score": 0.9},
            {"id": "2", "content": "OAuth flow", "score": 0.8},
        ],
        "code": [
            {"id": "auth.py", "content": "def authenticate(): ...", "score": 0.85},
        ],
        "graph": [
            {"id": "auth_service", "type": "service", "relationships": []},
        ],
    }


@pytest.fixture
def mock_tool_results():
    return [
        {
            "tool_name": "architecture_evaluate",
            "output": {"score": 0.85, "issues": []},
        },
        {
            "tool_name": "security_validate",
            "output": {"issues": [], "severity": "none"},
        },
    ]


@pytest.fixture
def stub_qdrant_host():
    return "localhost"


@pytest.fixture
def stub_falkordb_host():
    return "localhost"


@pytest.fixture
def stub_redis_url():
    return "redis://localhost:6379"


@pytest.fixture
def stub_llm_provider():
    return "openrouter"


@pytest.fixture
def stub_jwt_secret():
    return "test-secret-key-for-testing"


@pytest.fixture
def api_client():
    from httpx import AsyncClient
    from api.main import app

    return AsyncClient(app=app, base_url="http://test")


@pytest.fixture
async def auth_token(api_client):
    response = await api_client.post(
        "/auth/token",
        json={
            "username": "testuser",
            "password": "testpass",
        },
    )
    return response.json()["access_token"]


def assert_valid_response(response: Dict[str, Any], required_fields: List[str] = None):
    required_fields = required_fields or ["query", "answer"]
    for field in required_fields:
        assert field in response, f"Missing required field: {field}"
        assert response[field], f"Empty value for field: {field}"


def assert_valid_execution(execution: Dict[str, Any]):
    assert "iterations" in execution
    assert "steps" in execution
    assert "took_ms" in execution
    assert isinstance(execution["iterations"], int)
    assert execution["iterations"] >= 0


def assert_valid_retrieval(results: Dict[str, Any]):
    assert "results" in results
    assert isinstance(results["results"], list)
    assert "total_results" in results
    assert results["total_results"] >= 0


def assert_valid_plan(plan: Dict[str, Any]):
    assert "intent" in plan
    assert "steps" in plan
    assert isinstance(plan["steps"], list)


def assert_valid_ingestion_job(job: Dict[str, Any]):
    assert "job_id" in job or "id" in job
    assert "status" in job
    assert job["status"] in ["PENDING", "PROCESSING", "COMPLETED", "FAILED"]


def patch_dependencies(dependencies: Dict[str, Any]):
    return patch(
        "aiohttp.ClientSession",
        **{k: AsyncMock(return_value=v) for k, v in dependencies.items()},
    )
