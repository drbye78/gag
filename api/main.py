"""
FastAPI Main - REST API endpoints.

Provides /health, /query, /mcp, /multimodal/extract,
/reasoning, /rerank, /citations, /hybrid/enhanced,
/ingestion, /git, and /documents endpoints.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health, ingestion, multimodal, query, reasoning, retrieval
from api.routes.v1 import router as v1_router
from core.config import get_settings
from core.middleware import setup_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger(__name__).info("Starting Engineering Intelligence System...")
    yield
    logging.getLogger(__name__).info("Shutting down Engineering Intelligence System...")
    from llm.router import LLMRouter

    await LLMRouter.close_client()
    logging.getLogger(__name__).info("Resources cleaned up.")


app = FastAPI(
    title="Engineering Intelligence System API",
    description="Production-grade engineering intelligence system with multi-RAG, multimodal diagrams, and multilingual support",
    version="4.1.0",
    lifespan=lifespan,
)


_cors_settings = get_settings()
_cors_origins = _cors_settings.cors_origins
_allow_credentials = False

if "*" in _cors_origins:
    logging.getLogger(__name__).critical(
        "Wildcard CORS origin is forbidden when credentials are enabled. "
        "Restricting to localhost only."
    )
    _cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    _allow_credentials = False
elif not _cors_settings.debug:
    logger = logging.getLogger(__name__)
    for origin in _cors_origins:
        if not origin.startswith("https://"):
            logger.warning(
                f"CORS origin '{origin}' is not HTTPS. "
                "Production environments should use HTTPS origins only."
            )
    _allow_credentials = True
else:
    _allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-Id"],
)


@app.middleware("http")
async def security_headers_middleware(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
    )
    settings = get_settings()
    if settings.enable_hsts:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


app.include_router(health.router)
app.include_router(query.router)
app.include_router(retrieval.router)
app.include_router(reasoning.router)
app.include_router(reasoning.rerank_router)
app.include_router(reasoning.citations_router)
app.include_router(multimodal.router)
app.include_router(ingestion.router)


try:
    from ingestion.api import router as ingestion_api_router

    app.include_router(ingestion_api_router)
except ImportError as e:
    logging.getLogger(__name__).warning("Ingestion API not available: %s", e)

try:
    from git.api import router as git_router

    app.include_router(git_router)
except ImportError as e:
    logging.getLogger(__name__).warning("Git API not available: %s", e)

try:
    from documents.api import router as documents_router

    app.include_router(documents_router)
except ImportError as e:
    logging.getLogger(__name__).warning("Documents API not available: %s", e)

try:
    from ui.api import router as ui_router

    app.include_router(ui_router)
except ImportError as e:
    logging.getLogger(__name__).warning("UI API not available: %s", e)

try:
    from api.graphrag import router as graphrag_router

    app.include_router(graphrag_router)
except ImportError as e:
    logging.getLogger(__name__).warning("GraphRAG API not available: %s", e)

try:
    from api.adapters import router as adapter_router

    app.include_router(adapter_router)
except ImportError as e:
    logging.getLogger(__name__).warning("Adapter API not available: %s", e)

try:
    from api.knowledge import router as knowledge_router

    app.include_router(knowledge_router)
except ImportError as e:
    logging.getLogger(__name__).warning("Knowledge API not available: %s", e)

try:
    from unified_ingestion.api import router as unified_ingestion_router

    app.include_router(unified_ingestion_router)
except ImportError as e:
    logging.getLogger(__name__).warning("Unified Ingestion API not available: %s", e)

setup_middleware(app)

app.include_router(v1_router)

# Keep legacy mount for sub-routers that have their own prefix definitions
# These will be available at /v1/{subrouter}/{path} via the v1 router
