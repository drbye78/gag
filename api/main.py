"""
FastAPI Main - REST API endpoints.

Provides /health, /query, /mcp, /multimodal/extract,
/reasoning, /rerank, /citations, /hybrid/enhanced,
/ingestion, /git, and /documents endpoints.
"""

import base64
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

import models.mcp
from core.middleware import setup_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.getLogger(__name__).info("Starting Engineering Intelligence System...")
    yield
    # Shutdown - cleanup resources
    logging.getLogger(__name__).info("Shutting down Engineering Intelligence System...")
    from llm.router import LLMRouter

    await LLMRouter.close_client()
    logging.getLogger(__name__).info("Resources cleaned up.")


app = FastAPI(
    title="Engineering Intelligence System API",
    description="Production-grade engineering intelligence system with multi-RAG, multimodal diagrams, and multilingual support",
    version="4.2.0",
    lifespan=lifespan,
)

from core.config import get_settings

_cors_settings = get_settings()

_cors_origins = _cors_settings.cors_origins

_allow_credentials = False

if "*" in _cors_origins:
    import logging

    logging.getLogger(__name__).critical(
        "Wildcard CORS origin is forbidden when credentials are enabled. "
        "Restricting to localhost only."
    )
    _cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    _allow_credentials = False
elif not _cors_settings.debug:
    import logging

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

# ---------------------------------------------------------------------------
# Mount sub-routers
# ---------------------------------------------------------------------------

# Ingestion API
try:
    from ingestion.api import router as ingestion_router

    app.include_router(ingestion_router)
except ImportError as e:
    import logging

    logging.getLogger(__name__).warning("Ingestion API not available: %s", e)

# Git API
try:
    from git.api import router as git_router

    app.include_router(git_router)
except ImportError as e:
    import logging

    logging.getLogger(__name__).warning("Git API not available: %s", e)

# Documents API
try:
    from documents.api import router as documents_router

    app.include_router(documents_router)
except ImportError as e:
    import logging

    logging.getLogger(__name__).warning("Documents API not available: %s", e)

# UI sketch understanding
try:
    from ui.api import router as ui_router

    app.include_router(ui_router)
except ImportError as e:
    import logging

    logging.getLogger(__name__).warning("UI API not available: %s", e)

# GraphRAG API
try:
    from api.graphrag import router as graphrag_router

    app.include_router(graphrag_router)
except ImportError as e:
    import logging

    logging.getLogger(__name__).warning("GraphRAG API not available: %s", e)

try:
    from api.adapters import router as adapter_router

    app.include_router(adapter_router)
except ImportError as e:
    import logging

    logging.getLogger(__name__).warning("Adapter API not available: %s", e)

try:
    from api.knowledge import router as knowledge_router

    app.include_router(knowledge_router)
except ImportError as e:
    import logging

    logging.getLogger(__name__).warning("Knowledge API not available: %s", e)

# Configure middleware
setup_middleware(app)

# NOTE: The API does not currently expose an OpenTelemetry traces endpoint
# (e.g., /v1/traces). To add distributed tracing support, integrate an
# OTLP exporter and mount a traces endpoint using the opentelemetry-sdk.

# ---------------------------------------------------------------------------
# Authentication - DEFAULT DENY POLICY
# ---------------------------------------------------------------------------
from fastapi import Depends

from core.auth import require_authenticated

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    query: str
    sources: Optional[List[str]] = None
    limit: Optional[int] = 10

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must not be empty")
        v = v.strip()
        if len(v) > 10000:
            raise ValueError("query must not exceed 10000 characters")
        return v


class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    version: str


class ImageExtractionRequest(BaseModel):
    image_url: str
    prompt: Optional[str] = "Extract all text from this image"

    @field_validator("image_url")
    @classmethod
    def image_url_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("image_url must not be empty")
        v = v.strip()
        if len(v) > 5000:
            raise ValueError("image_url must not exceed 5000 characters")
        return v


class ImageExtractionResponse(BaseModel):
    text: str
    metadata: Dict[str, Any]


class ReasoningRequest(BaseModel):
    query: str
    facts: List[Dict[str, Any]]
    mode: Optional[str] = "chain_of_thoughts"

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must not be empty")
        v = v.strip()
        if len(v) > 10000:
            raise ValueError("query must not exceed 10000 characters")
        return v


class ReasoningResponse(BaseModel):
    query: str
    answer: str
    reasoning_mode: str
    confidence: float
    steps: List[Dict[str, Any]]


class RerankRequest(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    provider: Optional[str] = "cohere"
    strategy: Optional[str] = "single"

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must not be empty")
        v = v.strip()
        if len(v) > 10000:
            raise ValueError("query must not exceed 10000 characters")
        return v


class RerankResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    reranked: bool


class CitationRequest(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    style: Optional[str] = "parenthetical"

    @field_validator("answer")
    @classmethod
    def answer_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("answer must not be empty")
        v = v.strip()
        if len(v) > 100000:
            raise ValueError("answer must not exceed 100000 characters")
        return v


class CitationResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["public"])
async def health():
    from core.health import get_health_checker

    checker = get_health_checker()
    status_info = await checker.get_status()

    return HealthResponse(
        status=status_info["status"],
        version="4.2.0",
    )


@app.get("/", tags=["public"])
async def root():
    return {
        "service": "Engineering Intelligence System",
        "version": "3.2.0",
        "endpoints": [
            "/health",
            "/query",
            "/mcp",
            "/multimodal/extract",
            "/reasoning/chain",
            "/reasoning/entity",
            "/rerank",
            "/citations",
            "/hybrid/enhanced",
            "/graphrag/query",
            "/graphrag/entities",
            "/graphrag/relationships",
            "/graphrag/communities",
            "/graphrag/stats",
            "/ingestion/ingest",
            "/ingestion/batch",
            "/ingestion/codebase",
            "/ingestion/jobs",
        ],
    }


@app.post("/query", response_model=QueryResponse, dependencies=[Depends(require_authenticated)])
async def query(request: QueryRequest):
    from agents.orchestration import get_orchestration_engine

    engine = get_orchestration_engine()
    result = await engine.execute(request.query)

    return QueryResponse(
        query=result["query"],
        answer=result["answer"],
        sources=result.get("retrieval_results", {}).get("results", []),
        metadata=result.get("metadata", {}),
    )


@app.post("/mcp", dependencies=[Depends(require_authenticated)])
async def mcp(request: models.mcp.MCPRequest):
    from api.mcp import get_mcp_handler

    handler = get_mcp_handler()
    result = await handler.handle_request(request)

    if result.error:
        raise HTTPException(status_code=400, detail=result.error)

    return result


@app.get("/mcp", dependencies=[Depends(require_authenticated)])
async def mcp_list():
    from api.mcp import MCP_JSON_SCHEMA
    from tools.base import get_tool_registry

    registry = get_tool_registry()
    tools = registry.list_tools()

    return {"tools": tools, "schema": MCP_JSON_SCHEMA}


@app.post(
    "/multimodal/extract",
    response_model=ImageExtractionResponse,
    dependencies=[Depends(require_authenticated)],
)
async def extract_from_image(request: ImageExtractionRequest):
    from multimodal.vlm import get_vlm_processor

    processor = get_vlm_processor()
    result = await processor.extract_for_ir(request.image_url, title=None)

    return ImageExtractionResponse(
        text=result.get("content", ""),
        metadata={},
    )


@app.post(
    "/reasoning/chain",
    response_model=ReasoningResponse,
    dependencies=[Depends(require_authenticated)],
)
async def chain_reasoning(request: ReasoningRequest):
    from retrieval.reasoning import ReasoningMode, get_reasoning_engine

    engine = get_reasoning_engine(ReasoningMode.CHAIN_OF_THOUGHTS)
    result = await engine.reason(request.query, request.facts)

    return ReasoningResponse(
        query=result["query"],
        answer=result["answer"],
        reasoning_mode=result["reasoning_mode"],
        confidence=result["confidence"],
        steps=[
            {
                "thought": s.get("thought", "") if isinstance(s, dict) else s.thought,
                "action": s.get("action", "") if isinstance(s, dict) else s.action,
                "observation": s.get("observation", "") if isinstance(s, dict) else s.observation,
            }
            for s in result.get("steps", [])
        ],
    )


@app.post(
    "/reasoning/entity",
    response_model=ReasoningResponse,
    dependencies=[Depends(require_authenticated)],
)
async def entity_reasoning(request: ReasoningRequest):
    from retrieval.reasoning.entity_aware import get_entity_aware_reasoning_engine

    engine = get_entity_aware_reasoning_engine()
    result = await engine.reason(request.query, request.facts)

    return ReasoningResponse(
        query=result["query"],
        answer=result["answer"],
        reasoning_mode=result["reasoning_mode"],
        confidence=result["confidence"],
        steps=[
            {
                "thought": s.get("thought", "") if isinstance(s, dict) else s.thought,
                "action": s.get("action", "") if isinstance(s, dict) else s.action,
                "observation": s.get("observation", "") if isinstance(s, dict) else s.observation,
            }
            for s in result.get("steps", [])
        ],
    )


@app.post("/rerank", response_model=RerankResponse, dependencies=[Depends(require_authenticated)])
async def rerank(request: RerankRequest):
    from retrieval.rerank import get_rerank_pipeline

    pipeline = get_rerank_pipeline()
    reranked = await pipeline.rerank(request.query, request.results)

    return RerankResponse(
        query=request.query,
        results=[{"content": r.content, "score": r.score, "id": r.node_id} for r in reranked],
        reranked=True,
    )


@app.post(
    "/citations", response_model=CitationResponse, dependencies=[Depends(require_authenticated)]
)
async def generate_citations(request: CitationRequest):
    from retrieval.citations import CitationBuilder, CitationStyle

    style = CitationStyle(request.style) if request.style else CitationStyle.PARENTHETICAL
    builder = CitationBuilder(style=style)

    annotated = builder.build(request.answer, request.sources)

    return CitationResponse(
        answer=annotated.answer,
        citations=[{"id": c.id, "confidence": c.confidence} for c in annotated.citations],
        sources=[{"source_id": s.source_id, "content": s.content[:100]} for s in annotated.sources],
    )


@app.post("/hybrid/enhanced", dependencies=[Depends(require_authenticated)])
async def enhanced_search(request: QueryRequest):
    from retrieval.hybrid import get_enhanced_hybrid_retriever

    retriever = get_enhanced_hybrid_retriever()
    result = await retriever.search_with_enhanced_reasoning(
        request.query,
        limit=request.limit or 10,
    )

    return result


# ---------------------------------------------------------------------------
# Entity graph cache management endpoints
# ---------------------------------------------------------------------------


class EntityCacheStatsResponse(BaseModel):
    size: int
    capacity: int
    hit_rate: float
    hits: int
    misses: int
    utilization_pct: float
    oldest_entry: Optional[Dict[str, Any]]


@app.get(
    "/entity/cache/stats",
    response_model=EntityCacheStatsResponse,
    dependencies=[Depends(require_authenticated)],
)
async def entity_cache_stats():
    from retrieval.hybrid import get_enhanced_hybrid_retriever

    retriever = get_enhanced_hybrid_retriever()
    stats = retriever.get_entity_cache_stats()
    return EntityCacheStatsResponse(
        size=stats["size"],
        capacity=stats["capacity"],
        hit_rate=stats["hit_rate"],
        hits=stats["hits"],
        misses=stats["misses"],
        utilization_pct=stats["utilization_pct"],
        oldest_entry=stats.get("oldest_entry"),
    )


class EntityCacheInvalidateRequest(BaseModel):
    entity_name: Optional[str] = None


class EntityCacheInvalidateResponse(BaseModel):
    invalidated: bool
    entity_name: Optional[str] = None
    message: str


@app.post(
    "/entity/cache/invalidate",
    response_model=EntityCacheInvalidateResponse,
    dependencies=[Depends(require_authenticated)],
)
async def entity_cache_invalidate(request: EntityCacheInvalidateRequest):
    from retrieval.hybrid import get_enhanced_hybrid_retriever

    retriever = get_enhanced_hybrid_retriever()
    success = retriever.invalidate_entity_cache(request.entity_name)
    return EntityCacheInvalidateResponse(
        invalidated=success,
        entity_name=request.entity_name,
        message="Cache cleared"
        if not request.entity_name
        else f"Invalidated '{request.entity_name}'",
    )


# Tooling Search Request/Response models


class ToolingSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10
    entity_type: Optional[str] = None

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must not be empty")
        v = v.strip()
        if len(v) > 10000:
            raise ValueError("query must not exceed 10000 characters")
        return v


class ToolingSearchResponse(BaseModel):
    query: str
    results: Any
    tool: str
    count: int


# ---------------------------------------------------------------------------
# CodeGraph Request/Response models
# ---------------------------------------------------------------------------


class CodeGraphFindRequest(BaseModel):
    query: str
    fuzzy: Optional[bool] = False
    edit_distance: Optional[int] = 2
    repo_path: Optional[str] = None
    limit: Optional[int] = 10


class CodeGraphRelationshipRequest(BaseModel):
    query_type: str
    target: str
    context: Optional[str] = None
    repo_path: Optional[str] = None


class CodeGraphComplexRequest(BaseModel):
    limit: Optional[int] = 10
    repo_path: Optional[str] = None


class CodeGraphDeadCodeRequest(BaseModel):
    exclude_decorated_with: Optional[List[str]] = []
    repo_path: Optional[str] = None


class CodeGraphVisualizeRequest(BaseModel):
    query_type: str  # "show_all_nodes" or "show_relationships"
    node_name: Optional[str] = None  # Required when query_type == "show_relationships"


class CodeGraphIndexGitRequest(BaseModel):
    url: str
    branch: Optional[str] = "main"
    depth: Optional[int] = 1


class CodeGraphIndexZipRequest(BaseModel):
    content: str  # base64 encoded
    filename: Optional[str] = None


class CodeGraphIndexURLRequest(BaseModel):
    url: str
    url_type: Optional[str] = "zip"  # "zip", "markdown"


class CodeGraphIndexMarkdownRequest(BaseModel):
    content: str
    source_name: Optional[str] = "document.md"


class CodeGraphIndexConfluenceRequest(BaseModel):
    base_url: str
    page_id: str
    email: str
    api_token: str


class CodeGraphIndexConfluenceSpaceRequest(BaseModel):
    base_url: str
    space_key: str
    email: str
    api_token: str
    include_children: bool = True
    max_depth: int = 3
    include_attachments: bool = False


class CodeGraphIndexConfluenceSpaceResponse(BaseModel):
    source: str
    space_key: str
    success: bool
    pages_indexed: int = 0
    errors: List[str] = []


class CodeGraphIndexConfluenceTreeRequest(BaseModel):
    base_url: str
    page_id: str
    email: str
    api_token: str
    depth: int = 3
    include_attachments: bool = True


class CodeGraphIndexConfluenceTreeResponse(BaseModel):
    source: str
    root_page_id: str
    success: bool
    pages_indexed: int = 0
    attachments_indexed: int = 0


class CodeGraphIndexConfluencePageRequest(BaseModel):
    base_url: str
    page_id: str
    email: str
    api_token: str
    include_attachments: bool = False
    include_children: bool = False
    children_depth: int = 1


class CodeGraphIndexConfluencePageResponse(BaseModel):
    source: str
    page_id: str
    success: bool
    indexed: bool = False
    attachments_count: int = 0
    children_count: int = 0


class CodeGraphIndexResponse(BaseModel):
    source: str
    success: bool
    error: Optional[str] = None
    url: Optional[str] = None
    branch: Optional[str] = None
    filename: Optional[str] = None


class CodeGraphResponse(BaseModel):
    query: str
    results: Any
    method: str
    count: int


# ---------------------------------------------------------------------------
# Multi-Modal Search Request/Response models
# ---------------------------------------------------------------------------


class ColPALSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10


class ColPALSearchResponse(BaseModel):
    query: str
    results: Any
    method: str = "colpal"
    count: int


class UISketchSearchRequest(BaseModel):
    sketch_data: str
    limit: Optional[int] = 10


class UISketchSearchResponse(BaseModel):
    results: Any
    method: str = "ui_sketch"
    count: int


class DiagramExtractRequest(BaseModel):
    content: Optional[str] = None
    image_url: Optional[str] = None
    source: Optional[str] = None
    enrich: bool = False


class DiagramExtractResponse(BaseModel):
    diagram_id: str
    diagram_type: str
    title: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    extraction_confidence: float


class DiagramSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10
    diagram_types: Optional[List[str]] = None


class DiagramSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    count: int


# ---------------------------------------------------------------------------
# Tooling Search Endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/search/kubernetes",
    response_model=ToolingSearchResponse,
    dependencies=[Depends(require_authenticated)],
)
async def search_kubernetes(request: ToolingSearchRequest):
    from retrieval.tooling.kubernetes import KubernetesRetriever

    retriever = KubernetesRetriever()
    results = await retriever.search(request.query, limit=request.limit or 10)

    if request.entity_type:
        results = [r for r in results if r.get("entity_type") == request.entity_type]

    return ToolingSearchResponse(
        query=request.query,
        results=results,
        tool="kubernetes",
        count=len(results),
    )


@app.post(
    "/search/helm",
    response_model=ToolingSearchResponse,
    dependencies=[Depends(require_authenticated)],
)
async def search_helm(request: ToolingSearchRequest):
    from retrieval.tooling.helm import HelmRetriever

    retriever = HelmRetriever()
    results = await retriever.search(request.query, limit=request.limit or 10)

    if request.entity_type:
        results = [r for r in results if r.get("entity_type") == request.entity_type]

    return ToolingSearchResponse(
        query=request.query,
        results=results,
        tool="helm",
        count=len(results),
    )


@app.post(
    "/search/dockerfile",
    response_model=ToolingSearchResponse,
    dependencies=[Depends(require_authenticated)],
)
async def search_dockerfile(request: ToolingSearchRequest):
    from retrieval.tooling.dockerfile import DockerfileRetriever

    retriever = DockerfileRetriever()
    results = await retriever.search(request.query, limit=request.limit or 10)

    if request.entity_type:
        results = [r for r in results if r.get("entity_type") == request.entity_type]

    return ToolingSearchResponse(
        query=request.query,
        results=results,
        tool="dockerfile",
        count=len(results),
    )


@app.post(
    "/search/graphql",
    response_model=ToolingSearchResponse,
    dependencies=[Depends(require_authenticated)],
)
async def search_graphql(request: ToolingSearchRequest):
    from retrieval.tooling.graphql import GraphQLRetriever

    retriever = GraphQLRetriever()
    results = await retriever.search(request.query, limit=request.limit or 10)

    if request.entity_type:
        results = [r for r in results if r.get("entity_type") == request.entity_type]

    return ToolingSearchResponse(
        query=request.query,
        results=results,
        tool="graphql",
        count=len(results),
    )


@app.post(
    "/search/istio",
    response_model=ToolingSearchResponse,
    dependencies=[Depends(require_authenticated)],
)
async def search_istio(request: ToolingSearchRequest):
    from retrieval.tooling.istio import IstioRetriever

    retriever = IstioRetriever()
    results = await retriever.search(request.query, limit=request.limit or 10)

    if request.entity_type:
        results = [r for r in results if r.get("entity_type") == request.entity_type]

    return ToolingSearchResponse(
        query=request.query,
        results=results,
        tool="istio",
        count=len(results),
    )


# ---------------------------------------------------------------------------
# CodeGraph Endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/codegraph/find",
    response_model=CodeGraphResponse,
    dependencies=[Depends(require_authenticated)],
)
async def codegraph_find(request: CodeGraphFindRequest):
    from retrieval.code_graph import CodeGraphRetriever

    retriever = CodeGraphRetriever(repo_path=request.repo_path)
    result = await retriever.search(
        request.query,
        limit=request.limit or 10,
        method="find_code",
    )

    return CodeGraphResponse(
        query=request.query,
        results=result.get("results", []),
        method="find_code",
        count=result.get("total", 0),
    )


@app.post(
    "/codegraph/relationships",
    response_model=CodeGraphResponse,
    dependencies=[Depends(require_authenticated)],
)
async def codegraph_relationships(request: CodeGraphRelationshipRequest):
    from retrieval.code_graph import CodeGraphRetriever

    retriever = CodeGraphRetriever(repo_path=request.repo_path)
    result = await retriever.search(
        f"{request.query_type}:{request.target}",
        limit=20,
        method=request.query_type,
    )

    return CodeGraphResponse(
        query=f"{request.query_type}:{request.target}",
        results=result.get("results", []),
        method="relationships",
        count=result.get("total", 0),
    )


@app.get(
    "/codegraph/complex",
    response_model=CodeGraphResponse,
    dependencies=[Depends(require_authenticated)],
)
async def codegraph_complex(request: CodeGraphComplexRequest = CodeGraphComplexRequest()):
    from retrieval.code_graph import CodeGraphRetriever

    retriever = CodeGraphRetriever(repo_path=request.repo_path)
    result = await retriever.search(
        "most_complex_functions",
        limit=request.limit or 10,
        method="complexity",
    )

    return CodeGraphResponse(
        query="most_complex_functions",
        results=result.get("results", []),
        method="complexity",
        count=result.get("total", 0),
    )


@app.get(
    "/codegraph/dead-code",
    response_model=CodeGraphResponse,
    dependencies=[Depends(require_authenticated)],
)
async def codegraph_dead_code(request: CodeGraphDeadCodeRequest = CodeGraphDeadCodeRequest()):
    from retrieval.code_graph import CodeGraphRetriever

    retriever = CodeGraphRetriever(repo_path=request.repo_path)
    result = await retriever.search(
        "dead_code",
        limit=50,
        method="dead_code",
    )

    return CodeGraphResponse(
        query="dead_code",
        results=result.get("results", []),
        method="dead_code",
        count=result.get("total", 0),
    )


@app.post("/codegraph/visualize", dependencies=[Depends(require_authenticated)])
async def codegraph_visualize(request: CodeGraphVisualizeRequest):
    from graph.cypher_builder import CypherBuilder
    from retrieval.code_graph import CodeGraphRetriever

    # SECURITY: Only allow pre-defined visualization queries — raw Cypher is not supported
    allowed_query_types = {"show_all_nodes", "show_relationships"}
    if request.query_type not in allowed_query_types:
        return {
            "error": f"Unsupported query_type '{request.query_type}'. Allowed: {allowed_query_types}",
            "url": None,
        }

    retriever = CodeGraphRetriever()

    if request.query_type == "show_all_nodes":
        builder = CypherBuilder(
            allowed_types={"Component", "Service", "Function", "Class", "Module", "File", "Entity"}
        )
        builder.match_node(["Entity"], {})
        builder.return_clause("n")
        builder.limit_clause(100)
        cypher, params = builder.build()
    elif request.query_type == "show_relationships":
        if not request.node_name:
            return {"error": "node_name is required for show_relationships query", "url": None}
        from core.security import sanitize_filename

        safe_name = sanitize_filename(request.node_name)
        builder = CypherBuilder(
            allowed_types={"Component", "Service", "Function", "Class", "Module", "File", "Entity"}
        )
        builder.match_node(["Entity"], {"name": safe_name})
        builder.return_clause("n")
        builder.limit_clause(100)
        cypher, params = builder.build()
    else:
        return {"error": "Raw Cypher queries are not supported for security reasons", "url": None}

    result = await retriever.visualize(cypher)

    return {"url": result.get("url"), "query_type": request.query_type}


# ---------------------------------------------------------------------------
# CodeGraph Ingestion Endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/codegraph/index/git",
    response_model=CodeGraphIndexResponse,
    dependencies=[Depends(require_authenticated)],
)
async def codegraph_index_git(request: CodeGraphIndexGitRequest):
    from retrieval.code_graph import index_git_repository

    result = await index_git_repository(
        url=request.url,
        branch=request.branch or "main",
        depth=request.depth or 1,
    )
    return CodeGraphIndexResponse(
        source="git",
        url=request.url,
        branch=request.branch,
        success=result.get("success", False),
        error=result.get("error"),
    )


@app.post(
    "/codegraph/index/zip",
    response_model=CodeGraphIndexResponse,
    dependencies=[Depends(require_authenticated)],
)
async def codegraph_index_zip(request: CodeGraphIndexZipRequest):
    from retrieval.code_graph import index_zip_archive

    content = base64.b64decode(request.content)
    result = await index_zip_archive(content, request.filename or "archive.zip")
    return CodeGraphIndexResponse(
        source="zip",
        filename=request.filename,
        success=result.get("success", False),
        error=result.get("error"),
    )


@app.post(
    "/codegraph/index/url",
    response_model=CodeGraphIndexResponse,
    dependencies=[Depends(require_authenticated)],
)
async def codegraph_index_url(request: CodeGraphIndexURLRequest):
    from retrieval.code_graph import index_from_url

    result = await index_from_url(
        url=request.url,
        url_type=request.url_type or "zip",
    )
    return CodeGraphIndexResponse(
        source="url",
        url=request.url,
        success=result.get("success", False),
        error=result.get("error"),
    )


@app.post(
    "/codegraph/index/markdown",
    response_model=CodeGraphIndexResponse,
    dependencies=[Depends(require_authenticated)],
)
async def codegraph_index_markdown(request: CodeGraphIndexMarkdownRequest):
    from retrieval.code_graph import index_markdown_content

    result = await index_markdown_content(
        content=request.content,
        source_name=request.source_name or "document.md",
    )
    return CodeGraphIndexResponse(
        source="markdown",
        source_name=request.source_name,
        success=result.get("success", False),
        error=result.get("error"),
    )


@app.post(
    "/codegraph/index/confluence",
    response_model=CodeGraphIndexResponse,
    dependencies=[Depends(require_authenticated)],
)
async def codegraph_index_confluence(request: CodeGraphIndexConfluenceRequest):
    from retrieval.code_graph import index_confluence_page

    result = await index_confluence_page(
        base_url=request.base_url,
        page_id=request.page_id,
        api_token=request.api_token,
        email=request.email,
    )
    return CodeGraphIndexResponse(
        source="confluence",
        page_id=request.page_id,
        success=result.get("success", False),
        error=result.get("error"),
    )


@app.post(
    "/codegraph/index/confluence/space",
    response_model=CodeGraphIndexConfluenceSpaceResponse,
    dependencies=[Depends(require_authenticated)],
)
async def codegraph_index_confluence_space(request: CodeGraphIndexConfluenceSpaceRequest):
    from documents.confluence import ConfluenceClient
    from retrieval.code_graph import _html_to_markdown, index_markdown_content

    client = ConfluenceClient(
        url=request.base_url, email=request.email, api_token=request.api_token
    )

    pages = await client.sync_space(
        space_key=request.space_key,
        include_children=request.include_children,
        max_depth=request.max_depth,
    )

    indexed = 0
    errors = []
    for page in pages:
        try:
            content = _html_to_markdown(page.content)
            result = await index_markdown_content(content, f"confluence_{page.page_id}.md")
            if result.get("success"):
                indexed += 1
        except Exception as e:
            errors.append(f"{page.page_id}: {str(e)}")

    attachments_indexed = 0
    if request.include_attachments:
        for page in pages:
            try:
                attachments = await client.get_page_attachments(page.page_id)
                for att in attachments:
                    binary = await client.download_attachment(page.page_id, att.attachment_id)
                    if binary:
                        attachments_indexed += 1
            except Exception:
                pass

    return CodeGraphIndexConfluenceSpaceResponse(
        source="confluence",
        space_key=request.space_key,
        success=indexed > 0,
        pages_indexed=indexed,
        errors=errors,
    )


@app.post(
    "/codegraph/index/confluence/tree",
    response_model=CodeGraphIndexConfluenceTreeResponse,
    dependencies=[Depends(require_authenticated)],
)
async def codegraph_index_confluence_tree(request: CodeGraphIndexConfluenceTreeRequest):
    from documents.confluence import ConfluenceClient
    from retrieval.code_graph import _html_to_markdown, index_markdown_content

    client = ConfluenceClient(
        url=request.base_url, email=request.email, api_token=request.api_token
    )

    page = await client.get_page_tree(
        page_id=request.page_id,
        include_attachments=request.include_attachments,
    )

    pages_indexed = 0

    async def _index_page_recursive(p):
        nonlocal pages_indexed
        try:
            content = _html_to_markdown(p.content)
            result = await index_markdown_content(content, f"confluence_{p.page_id}.md")
            if result.get("success"):
                pages_indexed += 1
        except Exception:
            pass
        for child in p.children:
            await _index_page_recursive(child)

    await _index_page_recursive(page)

    attachments_indexed = 0
    if request.include_attachments:
        attachments = await client.get_page_attachments(request.page_id)
        for att in attachments:
            binary = await client.download_attachment(request.page_id, att.attachment_id)
            if binary:
                attachments_indexed += 1

    return CodeGraphIndexConfluenceTreeResponse(
        source="confluence",
        root_page_id=request.page_id,
        success=pages_indexed > 0,
        pages_indexed=pages_indexed,
        attachments_indexed=attachments_indexed,
    )


@app.post(
    "/codegraph/index/confluence/page",
    response_model=CodeGraphIndexConfluencePageResponse,
    dependencies=[Depends(require_authenticated)],
)
async def codegraph_index_confluence_page(request: CodeGraphIndexConfluencePageRequest):
    from documents.confluence import ConfluenceClient
    from retrieval.code_graph import _html_to_markdown, index_markdown_content

    client = ConfluenceClient(
        url=request.base_url, email=request.email, api_token=request.api_token
    )

    page = await client.get_page(request.page_id)
    if not page:
        return CodeGraphIndexConfluencePageResponse(
            source="confluence",
            page_id=request.page_id,
            success=False,
            indexed=False,
        )

    body = await client.get_page_body(request.page_id)
    content = _html_to_markdown(body or "")
    result = await index_markdown_content(content, f"confluence_{request.page_id}.md")
    indexed = result.get("success", False)

    children_count = 0
    if request.include_children:
        children = await client.get_page_children(request.page_id, depth=request.children_depth)
        children_count = len(children)
        for child in children:
            child_body = await client.get_page_body(child.page_id)
            child_content = _html_to_markdown(child_body or "")
            await index_markdown_content(child_content, f"confluence_{child.page_id}.md")

    attachments_count = 0
    if request.include_attachments:
        attachments = await client.get_page_attachments(request.page_id)
        attachments_count = len(attachments)
        for att in attachments:
            await client.download_attachment(request.page_id, att.attachment_id)

    return CodeGraphIndexConfluencePageResponse(
        source="confluence",
        page_id=request.page_id,
        success=True,
        indexed=indexed,
        attachments_count=attachments_count,
        children_count=children_count,
    )


# ---------------------------------------------------------------------------
# Multi-Modal Search Endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/search/colpal",
    response_model=ColPALSearchResponse,
    dependencies=[Depends(require_authenticated)],
)
async def search_colpal(request: ColPALSearchRequest):
    from ui.retriever import get_ui_retriever

    retriever = get_ui_retriever()
    results = await retriever.search_combined(
        element_types=[request.query], limit=request.limit or 10
    )

    return ColPALSearchResponse(
        query=request.query,
        results=results,
        method="colpal",
        count=len(results),
    )


@app.post(
    "/search/ui-sketch",
    response_model=UISketchSearchResponse,
    dependencies=[Depends(require_authenticated)],
)
async def search_ui_sketch(request: UISketchSearchRequest):
    from ui.retriever import get_ui_retriever

    retriever = get_ui_retriever()
    results = await retriever.search_combined(
        element_types=[request.sketch_data], limit=request.limit or 10
    )

    return UISketchSearchResponse(
        results=results,
        method="ui_sketch",
        count=len(results),
    )


@app.post("/multimodal/diagram/extract", dependencies=[Depends(require_authenticated)])
async def extract_diagram(request: DiagramExtractRequest):
    from multimodal.diagram_ir import get_diagram_ir_builder

    builder = get_diagram_ir_builder()
    if request.image_url:
        ir = await builder.from_image(request.image_url, source=request.source)
    elif request.content:
        ir = await builder.from_text(request.content, source=request.source)
    else:
        from multimodal.diagram_ir import DiagramIR

        ir = DiagramIR(id="empty", diagram_type="unknown")

    if request.enrich and ir.nodes:
        ir = await builder.enrich(ir)

    return DiagramExtractResponse(
        diagram_id=ir.id,
        diagram_type=ir.diagram_type,
        title=ir.title,
        nodes=[n.to_dict() for n in ir.nodes],
        edges=[e.to_dict() for e in ir.edges],
        extraction_confidence=ir.extraction_confidence,
    )


@app.post("/multimodal/diagram/search", dependencies=[Depends(require_authenticated)])
async def search_diagram(request: DiagramSearchRequest):
    from multimodal.diagram_registry import DiagramRegistry

    registry = DiagramRegistry(use_qdrant=False, use_falkor=False)
    results = await registry.search(
        request.query, limit=request.limit or 10, diagram_types=request.diagram_types
    )

    return DiagramSearchResponse(
        results=[r.ir.to_dict() for r in results],
        count=len(results),
    )


@app.get("/multimodal/diagram/{diagram_id}", dependencies=[Depends(require_authenticated)])
async def get_diagram(diagram_id: str):
    from multimodal.diagram_registry import DiagramRegistry

    registry = DiagramRegistry(use_qdrant=False, use_falkor=False)
    ir = await registry.get_by_id(diagram_id)

    if not ir:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Diagram not found")

    return ir.to_dict()


@app.get(
    "/multimodal/diagram/visualize/{diagram_id}", dependencies=[Depends(require_authenticated)]
)
async def visualize_diagram(diagram_id: str):
    from multimodal.diagram_registry import DiagramRegistry

    registry = DiagramRegistry(use_qdrant=False, use_falkor=False)
    graph = await registry.get_graph(diagram_id)

    if not graph:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Diagram not found")

    return {"graph": graph}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


def cli_main():
    """Entry point for the ``eis`` console script (pyproject.toml [project.scripts])."""
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, workers=4)
