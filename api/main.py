"""
FastAPI Main - REST API endpoints.

Provides /health, /query, /mcp, /multimodal/extract,
/reasoning, /rerank, /citations, /hybrid/enhanced,
/ingestion, /git, and /documents endpoints.
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from typing import Any, Dict, List, Optional

import models.mcp
from core.middleware import setup_middleware

app = FastAPI(
    title="Engineering Intelligence System API",
    description="Production-grade engineering intelligence system with multi-RAG, multimodal diagrams, and multilingual support",
    version="3.2.0",
)

# Configure CORS from Settings (not hardcoded wildcard)
from core.config import get_settings

_cors_settings = get_settings()
_cors_origins = (
    _cors_settings.cors_origins if _cors_settings.cors_origins != ["*"] else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        return v.strip()


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
        return v.strip()


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
        return v.strip()


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
        return v.strip()


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
        return v.strip()


class CitationResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
async def health():
    from core.health import get_health_checker

    checker = get_health_checker()
    status_info = await checker.get_status()

    return HealthResponse(
        status=status_info["status"],
        version="3.2.0",
    )


@app.get("/")
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


@app.post("/query", response_model=QueryResponse)
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


@app.post("/mcp")
async def mcp(request: models.mcp.MCPRequest):
    from api.mcp import get_mcp_handler

    handler = get_mcp_handler()
    result = await handler.handle_request(request)

    if result.error:
        raise HTTPException(status_code=400, detail=result.error)

    return result


@app.get("/mcp")
async def mcp_list():
    from api.mcp import MCP_JSON_SCHEMA
    from tools.base import get_tool_registry

    registry = get_tool_registry()
    tools = registry.list_tools()

    return {"tools": tools, "schema": MCP_JSON_SCHEMA}


@app.post("/multimodal/extract", response_model=ImageExtractionResponse)
async def extract_from_image(request: ImageExtractionRequest):
    from multimodal.vlm import get_vlm_processor

    processor = get_vlm_processor()
    result = await processor.extract_for_ir(request.image_url, title=None)

    return ImageExtractionResponse(
        text=result.get("content", ""),
        metadata={},
    )


@app.post("/reasoning/chain", response_model=ReasoningResponse)
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
            {"thought": s.thought, "action": s.action, "observation": s.observation}
            for s in result.get("steps", [])
        ],
    )


@app.post("/reasoning/entity", response_model=ReasoningResponse)
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
            {"thought": s.thought, "action": s.action, "observation": s.observation}
            for s in result.get("steps", [])
        ],
    )


@app.post("/rerank", response_model=RerankResponse)
async def rerank(request: RerankRequest):
    from retrieval.rerank import get_rerank_pipeline

    pipeline = get_rerank_pipeline()
    reranked = await pipeline.rerank(request.query, request.results)

    return RerankResponse(
        query=request.query,
        results=[
            {"content": r.content, "score": r.score, "id": r.node_id} for r in reranked
        ],
        reranked=True,
    )


@app.post("/citations", response_model=CitationResponse)
async def generate_citations(request: CitationRequest):
    from retrieval.citations import CitationBuilder, CitationStyle

    style = (
        CitationStyle(request.style) if request.style else CitationStyle.PARENTHETICAL
    )
    builder = CitationBuilder(style=style)

    annotated = builder.build(request.answer, request.sources)

    return CitationResponse(
        answer=annotated.answer,
        citations=[
            {"id": c.id, "confidence": c.confidence} for c in annotated.citations
        ],
        sources=[
            {"source_id": s.source_id, "content": s.content[:100]}
            for s in annotated.sources
        ],
    )


@app.post("/hybrid/enhanced")
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


@app.get("/entity/cache/stats", response_model=EntityCacheStatsResponse)
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


@app.post("/entity/cache/invalidate", response_model=EntityCacheInvalidateResponse)
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
        return v.strip()


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
    cypher_query: str


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


# ---------------------------------------------------------------------------
# Tooling Search Endpoints
# ---------------------------------------------------------------------------


@app.post("/search/kubernetes", response_model=ToolingSearchResponse)
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


@app.post("/search/helm", response_model=ToolingSearchResponse)
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


@app.post("/search/dockerfile", response_model=ToolingSearchResponse)
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


@app.post("/search/graphql", response_model=ToolingSearchResponse)
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


@app.post("/search/istio", response_model=ToolingSearchResponse)
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


@app.post("/codegraph/find", response_model=CodeGraphResponse)
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


@app.post("/codegraph/relationships", response_model=CodeGraphResponse)
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


@app.get("/codegraph/complex", response_model=CodeGraphResponse)
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


@app.get("/codegraph/dead-code", response_model=CodeGraphResponse)
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


@app.post("/codegraph/visualize")
async def codegraph_visualize(request: CodeGraphVisualizeRequest):
    from retrieval.code_graph import CodeGraphRetriever

    retriever = CodeGraphRetriever()
    result = await retriever.visualize(request.cypher_query)

    return {"url": result.get("url"), "cypher_query": request.cypher_query}


# ---------------------------------------------------------------------------
# Multi-Modal Search Endpoints
# ---------------------------------------------------------------------------


@app.post("/search/colpal", response_model=ColPALSearchResponse)
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


@app.post("/search/ui-sketch", response_model=UISketchSearchResponse)
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
