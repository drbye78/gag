"""Tooling search and CodeGraph endpoints — extracted from api/main.py."""
import base64
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from core.auth import require_authenticated

logger = logging.getLogger(__name__)
router = APIRouter(tags=["tooling"])


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


# --- CodeGraph models ---

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

class CodeGraphRequest(BaseModel):
    repo_path: Optional[str] = None

class CodeGraphDeadCodeRequest(BaseModel):
    exclude_decorated_with: Optional[List[str]] = []
    repo_path: Optional[str] = None

class CodeGraphVisualizeRequest(BaseModel):
    query_type: str
    node_name: Optional[str] = None

class CodeGraphIndexGitRequest(BaseModel):
    url: str
    branch: Optional[str] = "main"
    depth: Optional[int] = 1

class CodeGraphIndexZipRequest(BaseModel):
    content: str
    filename: Optional[str] = None

class CodeGraphIndexURLRequest(BaseModel):
    url: str
    url_type: Optional[str] = "zip"

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


# --- Tooling search endpoints ---

def _make_tooling_endpoint(tool_name: str, retriever_cls_name: str):
    """Factory for tooling search endpoints."""
    async def endpoint(request: ToolingSearchRequest):
        module_map = {
            "kubernetes": "retrieval.tooling.kubernetes",
            "helm": "retrieval.tooling.helm",
            "dockerfile": "retrieval.tooling.dockerfile",
            "graphql": "retrieval.tooling.graphql",
            "istio": "retrieval.tooling.istio",
        }
        import importlib
        module = importlib.import_module(module_map[tool_name])
        retriever = getattr(module, retriever_cls_name)()
        results = await retriever.search(request.query, limit=request.limit or 10)
        if request.entity_type:
            results = [r for r in results if r.get("entity_type") == request.entity_type]
        return ToolingSearchResponse(query=request.query, results=results, tool=tool_name, count=len(results))
    return endpoint


for tool_name, retriever_cls in [
    ("kubernetes", "KubernetesRetriever"),
    ("helm", "HelmRetriever"),
    ("dockerfile", "DockerfileRetriever"),
    ("graphql", "GraphQLRetriever"),
    ("istio", "IstioRetriever"),
]:
    router.add_api_route(
        f"/search/{tool_name}",
        _make_tooling_endpoint(tool_name, retriever_cls),
        methods=["POST"],
        response_model=ToolingSearchResponse,
        dependencies=[Depends(require_authenticated)],
        name=f"search_{tool_name}",
    )


# --- CodeGraph endpoints ---

@router.post("/codegraph/find", response_model=CodeGraphResponse, dependencies=[Depends(require_authenticated)])
async def codegraph_find(request: CodeGraphFindRequest):
    from retrieval.code_graph import CodeGraphRetriever
    retriever = CodeGraphRetriever(repo_path=request.repo_path)
    result = await retriever.search(request.query, limit=request.limit or 10, method="find_code")
    return CodeGraphResponse(query=request.query, results=result.get("results", []), method="find_code", count=result.get("total", 0))


@router.post("/codegraph/relationships", response_model=CodeGraphResponse, dependencies=[Depends(require_authenticated)])
async def codegraph_relationships(request: CodeGraphRelationshipRequest):
    from retrieval.code_graph import CodeGraphRetriever
    retriever = CodeGraphRetriever(repo_path=request.repo_path)
    result = await retriever.search(f"{request.query_type}:{request.target}", limit=20, method=request.query_type)
    return CodeGraphResponse(query=f"{request.query_type}:{request.target}", results=result.get("results", []), method="relationships", count=result.get("total", 0))


@router.get("/codegraph/complex", response_model=CodeGraphResponse, dependencies=[Depends(require_authenticated)])
async def codegraph_complex(request: CodeGraphComplexRequest = CodeGraphComplexRequest()):
    from retrieval.code_graph import CodeGraphRetriever
    retriever = CodeGraphRetriever(repo_path=request.repo_path)
    result = await retriever.search("most_complex_functions", limit=request.limit or 10, method="complexity")
    return CodeGraphResponse(query="most_complex_functions", results=result.get("results", []), method="complexity", count=result.get("total", 0))


@router.get("/codegraph/dead-code", response_model=CodeGraphResponse, dependencies=[Depends(require_authenticated)])
async def codegraph_dead_code(request: CodeGraphDeadCodeRequest = CodeGraphDeadCodeRequest()):
    from retrieval.code_graph import CodeGraphRetriever
    retriever = CodeGraphRetriever(repo_path=request.repo_path)
    result = await retriever.search("dead_code", limit=50, method="dead_code")
    return CodeGraphResponse(query="dead_code", results=result.get("results", []), method="dead_code", count=result.get("total", 0))


@router.post("/codegraph/visualize", dependencies=[Depends(require_authenticated)])
async def codegraph_visualize(request: CodeGraphVisualizeRequest):
    from graph.cypher_builder import CypherBuilder
    from retrieval.code_graph import CodeGraphRetriever
    allowed_query_types = {"show_all_nodes", "show_relationships"}
    if request.query_type not in allowed_query_types:
        return {"error": f"Unsupported query_type '{request.query_type}'. Allowed: {allowed_query_types}", "url": None}
    retriever = CodeGraphRetriever()
    if request.query_type == "show_all_nodes":
        builder = CypherBuilder(allowed_types={"Component", "Service", "Function", "Class", "Module", "File", "Entity"})
        builder.match_node(["Entity"], {})
        builder.return_clause("n")
        builder.limit_clause(100)
        cypher, params = builder.build()
    elif request.query_type == "show_relationships":
        if not request.node_name:
            return {"error": "node_name is required for show_relationships query", "url": None}
        from core.security import sanitize_filename
        safe_name = sanitize_filename(request.node_name)
        builder = CypherBuilder(allowed_types={"Component", "Service", "Function", "Class", "Module", "File", "Entity"})
        builder.match_node(["Entity"], {"name": safe_name})
        builder.return_clause("n")
        builder.limit_clause(100)
        cypher, params = builder.build()
    else:
        return {"error": "Raw Cypher queries are not supported for security reasons", "url": None}
    result = await retriever.visualize(cypher)
    return {"url": result.get("url"), "query_type": request.query_type}


@router.post("/codegraph/index/git", response_model=CodeGraphIndexResponse, dependencies=[Depends(require_authenticated)])
async def codegraph_index_git(request: CodeGraphIndexGitRequest):
    from retrieval.code_graph import index_git_repository
    result = await index_git_repository(url=request.url, branch=request.branch or "main", depth=request.depth or 1)
    return CodeGraphIndexResponse(source="git", url=request.url, branch=request.branch, success=result.get("success", False), error=result.get("error"))


@router.post("/codegraph/index/zip", response_model=CodeGraphIndexResponse, dependencies=[Depends(require_authenticated)])
async def codegraph_index_zip(request: CodeGraphIndexZipRequest):
    from retrieval.code_graph import index_zip_archive
    content = base64.b64decode(request.content)
    result = await index_zip_archive(content, request.filename or "archive.zip")
    return CodeGraphIndexResponse(source="zip", filename=request.filename, success=result.get("success", False), error=result.get("error"))


@router.post("/codegraph/index/url", response_model=CodeGraphIndexResponse, dependencies=[Depends(require_authenticated)])
async def codegraph_index_url(request: CodeGraphIndexURLRequest):
    from retrieval.code_graph import index_from_url
    result = await index_from_url(url=request.url, url_type=request.url_type or "zip")
    return CodeGraphIndexResponse(source="url", url=request.url, success=result.get("success", False), error=result.get("error"))


@router.post("/codegraph/index/markdown", response_model=CodeGraphIndexResponse, dependencies=[Depends(require_authenticated)])
async def codegraph_index_markdown(request: CodeGraphIndexMarkdownRequest):
    from retrieval.code_graph import index_markdown_content
    result = await index_markdown_content(content=request.content, source_name=request.source_name or "document.md")
    return CodeGraphIndexResponse(source="markdown", success=result.get("success", False), error=result.get("error"))
