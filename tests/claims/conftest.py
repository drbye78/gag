"""
Fixtures for claim-verification tests.
Claim tests exercise real behavior against the current codebase.
They mock ONLY external services — never the SUT.
"""
import os
import sys
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-claims-testing")
os.environ.setdefault("CREDENTIAL_ENCRYPT_KEY", "12345678")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "openrouter")
os.environ.setdefault("LLM_MODEL", "qwen-max")
os.environ.setdefault("EMBEDDING_PROVIDER", "ollama")


@pytest.fixture
def mock_llm_router():
    mock = MagicMock()
    mock.chat = AsyncMock(return_value=MagicMock(
        text="This is a test answer from the LLM.",
        choices=[{"message": {"content": "This is a test answer from the LLM."}}],
        usage={"total_tokens": 100},
    ))
    mock.embed = AsyncMock(return_value=[0.1] * 1536)
    return mock


@pytest.fixture
def seeded_retrieval_results():
    return {
        "docs": [
            {"id": "d1", "content": "Authentication uses JWT tokens with RS256.", "score": 0.92, "source": "docs"},
            {"id": "d2", "content": "OAuth 2.0 flow is supported for third-party apps.", "score": 0.85, "source": "docs"},
            {"id": "d3", "content": "Token refresh happens every 60 minutes.", "score": 0.78, "source": "docs"},
        ],
        "code": [
            {"id": "c1", "content": "def authenticate(user, password): return jwt.encode(...)", "score": 0.88, "source": "code"},
            {"id": "c2", "content": "class AuthMiddleware: ...", "score": 0.75, "source": "code"},
        ],
        "graph": [
            {"id": "g1", "content": "AuthService calls TokenValidator", "score": 0.80, "source": "graph"},
        ],
    }
