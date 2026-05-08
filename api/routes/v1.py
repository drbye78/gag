"""
V1 API Routes - All endpoints under /v1 prefix.
"""

import asyncio
import base64
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from core.auth import require_authenticated
from models.mcp import MCPRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["v1"], dependencies=[Depends(require_authenticated)])
_semaphore = asyncio.Semaphore(50)

try:
    from ingestion.api import router as ingestion_router

    router.include_router(ingestion_router)
except ImportError as e:
    logger.warning("Ingestion API not available: %s", e)

try:
    from git.api import router as git_router

    router.include_router(git_router)
except ImportError as e:
    logger.warning("Git API not available: %s", e)

try:
    from documents.api import router as documents_router

    router.include_router(documents_router)
except ImportError as e:
    logger.warning("Documents API not available: %s", e)

try:
    from ui.api import router as ui_router

    router.include_router(ui_router)
except ImportError as e:
    logger.warning("UI API not available: %s", e)

try:
    from api.graphrag import router as graphrag_router

    router.include_router(graphrag_router)
except ImportError as e:
    logger.warning("GraphRAG API not available: %s", e)

try:
    from api.adapters import router as adapter_router

    router.include_router(adapter_router)
except ImportError as e:
    logger.warning("Adapter API not available: %s", e)

try:
    from api.knowledge import router as knowledge_router

    router.include_router(knowledge_router)
except ImportError as e:
    logger.warning("Knowledge API not available: %s", e)

try:
    from unified_ingestion.api import router as unified_ingestion_router

    router.include_router(unified_ingestion_router)
except ImportError as e:
    logger.warning("Unified Ingestion API not available: %s", e)


class QueryRequest(BaseModel):
    query: str
    sources: list[str] | None = None
    limit: int | None = 10
    temperature: float | None = None

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must not be empty")
        return v.strip()

    @field_validator("temperature")
    @classmethod
    def temperature_valid(cls, v: float | None) -> float | None:
        if v is not None and (v < 0 or v > 2.0):
            raise ValueError("temperature must be between 0 and 2.0")
        return v


class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: list[dict[str, Any]]
    metadata: dict[str, Any]


class ImageExtractionRequest(BaseModel):
    image_url: str
    prompt: str | None = "Extract all text from this image"

    @field_validator("image_url")
    @classmethod
    def image_url_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("image_url must not be empty")
        return v.strip()


class ImageExtractionResponse(BaseModel):
    text: str
    metadata: dict[str, Any]


class ReasoningRequest(BaseModel):
    query: str
    facts: list[dict[str, Any]]
    mode: str | None = "chain_of_thoughts"

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
    steps: list[dict[str, Any]]


class RerankRequest(BaseModel):
    query: str
    results: list[dict[str, Any]]
    provider: str | None = "cohere"
    strategy: str | None = "single"

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must not be empty")
        return v.strip()


class RerankResponse(BaseModel):
    query: str
    results: list[dict[str, Any]]
    reranked: bool


class CitationRequest(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    style: str | None = "parenthetical"

    @field_validator("answer")
    @classmethod
    def answer_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("answer must not be empty")
        return v.strip()


class CitationResponse(BaseModel):
    answer: str
    citations: list[dict[str, Any]]
    sources: list[dict[str, Any]]


class EntityCacheStatsResponse(BaseModel):
    size: int
    capacity: int
    hit_rate: float
    hits: int
    misses: int
    utilization_pct: float
    oldest_entry: dict[str, Any] | None


class EntityCacheInvalidateRequest(BaseModel):
    entity_name: str | None = None


class EntityCacheInvalidateResponse(BaseModel):
    invalidated: bool
    entity_name: str | None = None
    message: str


class ToolingSearchRequest(BaseModel):
    query: str
    limit: int | None = 10
    entity_type: str | None = None

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


class CodeGraphFindRequest(BaseModel):
    query: str
    fuzzy: bool | None = False
    edit_distance: int | None = 2
    repo_path: str | None = None
    limit: int | None = 10


class CodeGraphRelationshipRequest(BaseModel):
    query_type: str
    target: str
    context: str | None = None
    repo_path: str | None = None


class CodeGraphComplexRequest(BaseModel):
    limit: int | None = 10
    repo_path: str | None = None


class CodeGraphRequest(BaseModel):
    repo_path: str | None = None


class CodeGraphDeadCodeRequest(BaseModel):
    exclude_decorated_with: list[str] | None = []
    repo_path: str | None = None


class CodeGraphVisualizeRequest(BaseModel):
    query_type: str
    node_name: str | None = None


class CodeGraphIndexGitRequest(BaseModel):
    url: str
    branch: str | None = "main"
    depth: int | None = 1


class CodeGraphIndexZipRequest(BaseModel):
    content: str
    filename: str | None = None

    @field_validator("content")
    @classmethod
    def content_size_limit(cls, v: str) -> str:
        max_size = 50 * 1024 * 1024
        decoded = base64.b64decode(v)
        if len(decoded) > max_size:
            raise ValueError(f"Content exceeds maximum size of {max_size // (1024 * 1024)}MB")
        return v


class CodeGraphIndexURLRequest(BaseModel):
    url: str
    url_type: str | None = "zip"


class CodeGraphIndexMarkdownRequest(BaseModel):
    content: str
    source_name: str | None = "document.md"


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
    errors: list[str] = []


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
    error: str | None = None
    url: str | None = None
    branch: str | None = None
    filename: str | None = None


class CodeGraphResponse(BaseModel):
    query: str
    results: Any
    method: str
    count: int


class ColPALSearchRequest(BaseModel):
    query: str
    limit: int | None = 10


class ColPALSearchResponse(BaseModel):
    query: str
    results: Any
    method: str = "colpal"
    count: int


class UISketchSearchRequest(BaseModel):
    sketch_data: str
    limit: int | None = 10


class UISketchSearchResponse(BaseModel):
    results: Any
    method: str = "ui_sketch"
    count: int


class DiagramExtractRequest(BaseModel):
    content: str | None = None
    image_url: str | None = None
    source: str | None = None
    enrich: bool = False


class DiagramExtractResponse(BaseModel):
    diagram_id: str
    diagram_type: str
    title: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    extraction_confidence: float


class DiagramSearchRequest(BaseModel):
    query: str
    limit: int | None = 10
    diagram_types: list[str] | None = None


class DiagramSearchResponse(BaseModel):
    results: list[dict[str, Any]]
    count: int


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    from agents.orchestration import get_orchestration_engine

    async with _semaphore:
        engine = get_orchestration_engine()
        result = await engine.execute(request.query)

    return QueryResponse(
        query=result["query"],
        answer=result["answer"],
        sources=result.get("retrieval_results", {}).get("results", []),
        metadata=result.get("metadata", {}),
    )


@router.post("/mcp")
async def mcp(request: MCPRequest):
    from api.mcp import get_mcp_handler

    handler = get_mcp_handler()
    result = await handler.handle_request(request)

    if result.error:
        raise HTTPException(status_code=400, detail=result.error)

    return result


@router.get("/mcp")
async def mcp_list():
    from api.mcp import MCP_JSON_SCHEMA
    from tools.base import get_tool_registry

    registry = get_tool_registry()
    tools = registry.list_tools()

    return {"tools": tools, "schema": MCP_JSON_SCHEMA}


@router.post("/multimodal/extract", response_model=ImageExtractionResponse)
async def extract_from_image(request: ImageExtractionRequest):
    from multimodal.vlm import get_vlm_processor

    processor = get_vlm_processor()
    result = await processor.extract_for_ir(request.image_url, title=None)

    return ImageExtractionResponse(
        text=result.get("content", ""),
        metadata={},
    )


@router.post("/reasoning/chain", response_model=ReasoningResponse)
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


@router.post("/reasoning/entity", response_model=ReasoningResponse)
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


@router.post("/rerank", response_model=RerankResponse)
async def rerank(request: RerankRequest):
    from retrieval.rerank import get_rerank_pipeline

    pipeline = get_rerank_pipeline()
    reranked = await pipeline.rerank(request.query, request.results)

    return RerankResponse(
        query=request.query,
        results=[{"content": r.content, "score": r.score, "id": r.node_id} for r in reranked],
        reranked=True,
    )


@router.post("/citations", response_model=CitationResponse)
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


@router.post("/hybrid/enhanced")
async def enhanced_search(request: QueryRequest):
    from retrieval.hybrid import get_enhanced_hybrid_retriever

    retriever = get_enhanced_hybrid_retriever()
    result = await retriever.search_with_enhanced_reasoning(
        request.query,
        limit=request.limit or 10,
    )

    return result


@router.get("/entity/cache/stats", response_model=EntityCacheStatsResponse)
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


@router.post("/entity/cache/invalidate", response_model=EntityCacheInvalidateResponse)
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


@router.post("/search/kubernetes", response_model=ToolingSearchResponse)
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


@router.post("/search/helm", response_model=ToolingSearchResponse)
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


@router.post("/search/dockerfile", response_model=ToolingSearchResponse)
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


@router.post("/search/graphql", response_model=ToolingSearchResponse)
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


@router.post("/search/istio", response_model=ToolingSearchResponse)
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


@router.post("/codegraph/find", response_model=CodeGraphResponse)
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


@router.post("/codegraph/relationships", response_model=CodeGraphResponse)
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


@router.post("/codegraph/complex", response_model=CodeGraphResponse)
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


@router.get("/codegraph/complexity/{function_name}", response_model=CodeGraphResponse)
async def codegraph_complexity(function_name: str, request: CodeGraphRequest = CodeGraphRequest()):
    from retrieval.code_graph import CodeGraphRetriever

    retriever = CodeGraphRetriever(repo_path=request.repo_path)
    result = await retriever.get_complexity(function_name)

    return CodeGraphResponse(
        query=f"complexity:{function_name}",
        results=[{"function": function_name, "complexity": result.get("complexity", 0)}],
        method="complexity",
        count=1,
    )


@router.get("/codegraph/callers/{function_name}", response_model=CodeGraphResponse)
async def codegraph_callers(function_name: str, request: CodeGraphRequest = CodeGraphRequest()):
    from retrieval.code_graph import CodeGraphRetriever

    retriever = CodeGraphRetriever(repo_path=request.repo_path)
    result = await retriever.find_callers(function_name)

    return CodeGraphResponse(
        query=f"callers:{function_name}",
        results=result.get("results", []),
        method="callers",
        count=result.get("total", 0),
    )


@router.get("/codegraph/callees/{function_name}", response_model=CodeGraphResponse)
async def codegraph_callees(function_name: str, request: CodeGraphRequest = CodeGraphRequest()):
    from retrieval.code_graph import CodeGraphRetriever

    retriever = CodeGraphRetriever(repo_path=request.repo_path)
    result = await retriever.find_callees(function_name)

    return CodeGraphResponse(
        query=f"callees:{function_name}",
        results=result.get("results", []),
        method="callees",
        count=result.get("total", 0),
    )


@router.get("/codegraph/deps/{module_name}", response_model=CodeGraphResponse)
async def codegraph_deps(module_name: str, request: CodeGraphRequest = CodeGraphRequest()):
    from retrieval.code_graph import CodeGraphRetriever

    retriever = CodeGraphRetriever(repo_path=request.repo_path)
    result = await retriever.get_module_deps(module_name)

    return CodeGraphResponse(
        query=f"deps:{module_name}",
        results=result.get("dependencies", []),
        method="deps",
        count=len(result.get("dependencies", [])),
    )


@router.post("/codegraph/dead-code", response_model=CodeGraphResponse)
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


@router.post("/codegraph/visualize")
async def codegraph_visualize(request: CodeGraphVisualizeRequest):
    from graph.cypher_builder import CypherBuilder
    from retrieval.code_graph import CodeGraphRetriever

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
        cypher, _ = builder.build()
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
        cypher, _ = builder.build()
    else:
        return {"error": "Raw Cypher queries are not supported for security reasons", "url": None}

    result = await retriever.visualize(cypher)

    return {"url": result.get("url"), "query_type": request.query_type}


@router.post("/codegraph/index/git", response_model=CodeGraphIndexResponse)
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


@router.post("/codegraph/index/zip", response_model=CodeGraphIndexResponse)
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


@router.post("/codegraph/index/url", response_model=CodeGraphIndexResponse)
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


@router.post("/codegraph/index/markdown", response_model=CodeGraphIndexResponse)
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


@router.post("/codegraph/index/confluence", response_model=CodeGraphIndexResponse)
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


@router.post(
    "/codegraph/index/confluence/space", response_model=CodeGraphIndexConfluenceSpaceResponse
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
            errors.append(f"{page.page_id}: {e!s}")

    attachments_indexed = 0
    if request.include_attachments:
        for page in pages:
            try:
                from unified_ingestion.handlers.confluence import ConfluenceAttachmentHandler

                handler = ConfluenceAttachmentHandler()
                attachments = await client.get_page_attachments(page.page_id)
                for att in attachments:
                    binary = await client.download_attachment(page.page_id, att.attachment_id)
                    if binary:
                        result = await handler.handle(
                            content=binary,
                            path=att.title,
                            metadata={
                                "mime_type": att.mime_type,
                                "title": att.title,
                                "attachment_id": att.attachment_id,
                                "page_id": page.page_id,
                            },
                        )
                        if result.chunks:
                            from ingestion.indexer import VectorIndexer

                            indexer = VectorIndexer()
                            for chunk in result.chunks:
                                await indexer.index(
                                    collection="confluence_attachments",
                                    text=chunk.content,
                                    metadata={
                                        "source": "confluence_attachment",
                                        "page_id": page.page_id,
                                        "attachment_id": att.attachment_id,
                                        "handler_type": result.metadata.get("handler_type"),
                                        "title": att.title,
                                    },
                                )
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


@router.post(
    "/codegraph/index/confluence/tree", response_model=CodeGraphIndexConfluenceTreeResponse
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
        from unified_ingestion.handlers.confluence import ConfluenceAttachmentHandler

        handler = ConfluenceAttachmentHandler()
        attachments = await client.get_page_attachments(request.page_id)
        for att in attachments:
            binary = await client.download_attachment(request.page_id, att.attachment_id)
            if binary:
                result = await handler.handle(
                    content=binary,
                    path=att.title,
                    metadata={
                        "mime_type": att.mime_type,
                        "title": att.title,
                        "attachment_id": att.attachment_id,
                        "page_id": request.page_id,
                    },
                )
                if result.chunks:
                    from ingestion.indexer import VectorIndexer

                    indexer = VectorIndexer()
                    for chunk in result.chunks:
                        await indexer.index(
                            collection="confluence_attachments",
                            text=chunk.content,
                            metadata={
                                "source": "confluence_attachment",
                                "page_id": request.page_id,
                                "attachment_id": att.attachment_id,
                                "handler_type": result.metadata.get("handler_type"),
                                "title": att.title,
                            },
                        )
                    attachments_indexed += 1

    return CodeGraphIndexConfluenceTreeResponse(
        source="confluence",
        root_page_id=request.page_id,
        success=pages_indexed > 0,
        pages_indexed=pages_indexed,
        attachments_indexed=attachments_indexed,
    )


@router.post(
    "/codegraph/index/confluence/page", response_model=CodeGraphIndexConfluencePageResponse
)
async def codegraph_index_confluence_page(request: CodeGraphIndexConfluencePageRequest):
    from documents.confluence import ConfluenceClient
    from retrieval.code_graph import _html_to_markdown, index_markdown_content

    client = ConfluenceClient(
        url=request.base_url, email=request.email, api_token=request.api_token
    )

    page = client.get_page(request.page_id)
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


@router.post("/search/colpal", response_model=ColPALSearchResponse)
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


@router.post("/search/ui-sketch", response_model=UISketchSearchResponse)
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


@router.post("/multimodal/diagram/extract", response_model=DiagramExtractResponse)
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


@router.post("/multimodal/diagram/search", response_model=DiagramSearchResponse)
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


@router.get("/multimodal/diagram/{diagram_id}")
async def get_diagram(diagram_id: str):
    from multimodal.diagram_registry import DiagramRegistry

    registry = DiagramRegistry(use_qdrant=False, use_falkor=False)
    ir = await registry.get_by_id(diagram_id)

    if not ir:
        raise HTTPException(status_code=404, detail="Diagram not found")

    return ir.to_dict()


@router.get("/multimodal/diagram/visualize/{diagram_id}")
async def visualize_diagram(diagram_id: str):
    from multimodal.diagram_registry import DiagramRegistry

    registry = DiagramRegistry(use_qdrant=False, use_falkor=False)
    graph = await registry.get_graph(diagram_id)

    if not graph:
        raise HTTPException(status_code=404, detail="Diagram not found")

    return {"graph": graph}


__all__ = ["router"]
