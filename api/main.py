"""
FastAPI Main - Application setup, CORS, lifespan, router includes.

Endpoint implementations are in separate router modules:
- api/query_routes.py: /query, /hybrid/enhanced, /reasoning/*, /rerank, /citations
- api/tooling_routes.py: /search/{kubernetes,helm,...}, /codegraph/*
- api/multimodal_routes.py: /multimodal/*, /entity/cache/*, /search/colpal, /search/ui-sketch
- api/adapters.py: /adapter/*
- api/graphrag.py: /graphrag/*
- api/knowledge.py: /knowledge/*
"""

from contextlib import asynccontextmanager
import logging
import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, Optional

from __version__ import __version__
from core.auth import require_authenticated
from core.middleware import setup_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.getLogger(__name__).info("Starting Engineering Intelligence System...")
    from core.pool import get_http_pool
    await get_http_pool().start()
    from core.di import register_services
    register_services()
    from core.config import get_settings
    _settings = get_settings()
    if _settings.enable_tracing:
        from core.observability import setup_otel_tracing
        setup_otel_tracing(_settings)
        logging.getLogger(__name__).info("OpenTelemetry tracing enabled")
    yield
    # Shutdown
    logging.getLogger(__name__).info("Shutting down Engineering Intelligence System...")
    from llm.router import LLMRouter
    await LLMRouter.close_client()
    from core.pool import get_http_pool
    await get_http_pool().stop()
    import logging as _log
    _logger = _log.getLogger(__name__)
    try:
        from retrieval.docs import get_docs_retriever
        dr = get_docs_retriever()
        if hasattr(dr.backend, 'close'):
            await dr.backend.close()
    except Exception as e:
        _logger.debug("Docs retriever close: %s", e)
    try:
        from retrieval.code import get_code_retriever
        cr = get_code_retriever()
        if hasattr(cr, 'close'):
            await cr.close()
    except Exception as e:
        _logger.debug("Code retriever close: %s", e)
    _logger.info("Resources cleaned up.")


app = FastAPI(
    title="Engineering Intelligence System API",
    description="Production-grade engineering intelligence system with multi-RAG, multimodal diagrams, and multilingual support",
    version=__version__,
    lifespan=lifespan,
)

# --- CORS ---
from core.config import get_settings
_cors_settings = get_settings()
_cors_origins = _cors_settings.cors_origins
_allow_credentials = False
if "*" in _cors_origins:
    logging.getLogger(__name__).critical(
        "Wildcard CORS origin is forbidden when credentials are enabled. Restricting to localhost only."
    )
    _cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
elif not _cors_settings.debug:
    for origin in _cors_origins:
        if not origin.startswith("https://"):
            logging.getLogger(__name__).warning("CORS origin '%s' is not HTTPS.", origin)
    _allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-Id"],
)

# --- Mount sub-routers ---
try:
    from ingestion.api import router as ingestion_router
    app.include_router(ingestion_router)
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

# --- New extracted routers ---
try:
    from api.query_routes import router as query_router
    app.include_router(query_router)
except ImportError as e:
    logging.getLogger(__name__).warning("Query routes not available: %s", e)

try:
    from api.tooling_routes import router as tooling_router
    app.include_router(tooling_router)
except ImportError as e:
    logging.getLogger(__name__).warning("Tooling routes not available: %s", e)

try:
    from api.multimodal_routes import router as multimodal_router
    app.include_router(multimodal_router)
except ImportError as e:
    logging.getLogger(__name__).warning("Multimodal routes not available: %s", e)

# --- MCP ---
try:
    from api.mcp import get_mcp_handler
    import models.mcp
    @app.post("/mcp", dependencies=[Depends(require_authenticated)])
    async def mcp(request: models.mcp.MCPRequest):
        handler = get_mcp_handler()
        result = await handler.handle_request(request)
        return result

    @app.get("/mcp", dependencies=[Depends(require_authenticated)])
    async def mcp_list():
        from api.mcp import MCP_JSON_SCHEMA
        from tools.base import get_tool_registry
        registry = get_tool_registry()
        tools = registry.list_tools()
        return {"tools": tools, "schema": MCP_JSON_SCHEMA}
except ImportError as e:
    logging.getLogger(__name__).warning("MCP not available: %s", e)

# --- Health & Metrics ---
class HealthResponse(BaseModel):
    status: str
    version: str


@app.get("/health", response_model=HealthResponse, tags=["public"])
async def health():
    from core.health import get_health_checker
    checker = get_health_checker()
    status_info = await checker.get_status()
    return HealthResponse(status=status_info["status"], version=__version__)


@app.get("/metrics", tags=["public"])
async def metrics():
    """Prometheus-compatible metrics endpoint."""
    from core.observability import get_metrics_collector
    collector = get_metrics_collector()
    data = collector.get_metrics()
    lines = []
    lines.append("# HELP eis_latency_ms Latency in milliseconds")
    lines.append("# TYPE eis_latency_ms histogram")
    for op, stats in data.get("latencies", {}).items():
        safe_op = op.replace(".", "_").replace("-", "_")
        lines.append(f'eis_latency_ms{{operation="{safe_op}",percentile="p50"}} {stats["p50"]}')
        lines.append(f'eis_latency_ms{{operation="{safe_op}",percentile="p95"}} {stats["p95"]}')
        lines.append(f'eis_latency_ms{{operation="{safe_op}",percentile="p99"}} {stats["p99"]}')
        lines.append(f'eis_latency_count{{operation="{safe_op}"}} {stats["count"]}')
    lines.append("# HELP eis_counter_total Counter metrics")
    lines.append("# TYPE eis_counter_total counter")
    for key, value in data.get("counters", {}).items():
        safe_key = key.replace(".", "_").replace("-", "_")
        lines.append(f'eis_counter_total{{metric="{safe_key}"}} {value}')
    lines.append("# HELP eis_gauge Gauge metrics")
    lines.append("# TYPE eis_gauge gauge")
    for key, value in data.get("gauges", {}).items():
        safe_key = key.replace(".", "_").replace("-", "_")
        lines.append(f'eis_gauge{{metric="{safe_key}"}} {value}')
    return {"metrics": "\n".join(lines), "format": "prometheus_text"}


@app.get("/", tags=["public"])
async def root():
    return {
        "service": "Engineering Intelligence System",
        "version": __version__,
        "endpoints": [
            "/health", "/metrics", "/query", "/mcp",
            "/hybrid/enhanced", "/multimodal/extract",
            "/reasoning/chain", "/reasoning/entity",
            "/rerank", "/citations",
            "/graphrag/query", "/graphrag/entities",
            "/ingestion/ingest", "/ingestion/batch",
            "/search/kubernetes", "/search/helm",
            "/codegraph/find", "/codegraph/visualize",
        ],
    }


# Re-export models for backward compatibility with tests
from api.query_routes import (
    QueryRequest, QueryResponse,
    ReasoningRequest, ReasoningResponse,
    RerankRequest, RerankResponse,
    CitationRequest, CitationResponse,
)
from api.multimodal_routes import (
    ImageExtractionRequest, ImageExtractionResponse,
)
from api.tooling_routes import (
    ToolingSearchRequest, ToolingSearchResponse,
    CodeGraphFindRequest, CodeGraphRelationshipRequest,
    CodeGraphComplexRequest, CodeGraphRequest, CodeGraphDeadCodeRequest,
    CodeGraphVisualizeRequest, CodeGraphIndexGitRequest,
    CodeGraphIndexZipRequest, CodeGraphIndexURLRequest,
    CodeGraphIndexMarkdownRequest, CodeGraphIndexConfluenceRequest,
    CodeGraphIndexConfluenceSpaceRequest, CodeGraphIndexConfluenceSpaceResponse,
    CodeGraphIndexConfluenceTreeRequest, CodeGraphIndexConfluenceTreeResponse,
    CodeGraphIndexConfluencePageRequest, CodeGraphIndexConfluencePageResponse,
    CodeGraphIndexResponse, CodeGraphResponse,
)


# Configure middleware
setup_middleware(app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
