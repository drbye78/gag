import base64

from fastapi import APIRouter, Depends

from api.models.request import (
    CodeGraphComplexRequest,
    CodeGraphDeadCodeRequest,
    CodeGraphFindRequest,
    CodeGraphIndexConfluencePageRequest,
    CodeGraphIndexConfluenceRequest,
    CodeGraphIndexConfluenceSpaceRequest,
    CodeGraphIndexConfluenceTreeRequest,
    CodeGraphIndexGitRequest,
    CodeGraphIndexMarkdownRequest,
    CodeGraphIndexURLRequest,
    CodeGraphIndexZipRequest,
    CodeGraphRelationshipRequest,
    CodeGraphRequest,
    CodeGraphVisualizeRequest,
    ColPALSearchRequest,
    DiagramSearchRequest,
    EntityCacheInvalidateRequest,
    QueryRequest,
    ToolingSearchRequest,
    UISketchSearchRequest,
)
from api.models.response import (
    CodeGraphIndexConfluencePageResponse,
    CodeGraphIndexConfluenceSpaceResponse,
    CodeGraphIndexConfluenceTreeResponse,
    CodeGraphIndexResponse,
    CodeGraphResponse,
    ColPALSearchResponse,
    DiagramSearchResponse,
    EntityCacheInvalidateResponse,
    EntityCacheStatsResponse,
    ToolingSearchResponse,
    UISketchSearchResponse,
)
from core.auth import require_authenticated

router = APIRouter(prefix="", tags=["retrieval"])


@router.post("/hybrid/enhanced", dependencies=[Depends(require_authenticated)])
async def enhanced_search(request: QueryRequest):
    from retrieval.hybrid import get_enhanced_hybrid_retriever

    retriever = get_enhanced_hybrid_retriever()
    result = await retriever.search_with_enhanced_reasoning(
        request.query,
        limit=request.limit or 10,
    )

    return result


@router.get("/entity/cache/stats", response_model=EntityCacheStatsResponse, dependencies=[Depends(require_authenticated)])
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


@router.post("/entity/cache/invalidate", response_model=EntityCacheInvalidateResponse, dependencies=[Depends(require_authenticated)])
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


@router.post("/search/kubernetes", response_model=ToolingSearchResponse, dependencies=[Depends(require_authenticated)])
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


@router.post("/search/helm", response_model=ToolingSearchResponse, dependencies=[Depends(require_authenticated)])
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


@router.post("/search/dockerfile", response_model=ToolingSearchResponse, dependencies=[Depends(require_authenticated)])
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


@router.post("/search/graphql", response_model=ToolingSearchResponse, dependencies=[Depends(require_authenticated)])
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


@router.post("/search/istio", response_model=ToolingSearchResponse, dependencies=[Depends(require_authenticated)])
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


@router.post("/codegraph/find", response_model=CodeGraphResponse, dependencies=[Depends(require_authenticated)])
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


@router.post("/codegraph/relationships", response_model=CodeGraphResponse, dependencies=[Depends(require_authenticated)])
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


@router.post("/codegraph/complex", response_model=CodeGraphResponse, dependencies=[Depends(require_authenticated)])
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


@router.get("/codegraph/complexity/{function_name}", response_model=CodeGraphResponse, dependencies=[Depends(require_authenticated)])
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


@router.get("/codegraph/callers/{function_name}", response_model=CodeGraphResponse, dependencies=[Depends(require_authenticated)])
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


@router.get("/codegraph/callees/{function_name}", response_model=CodeGraphResponse, dependencies=[Depends(require_authenticated)])
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


@router.get("/codegraph/deps/{module_name}", response_model=CodeGraphResponse, dependencies=[Depends(require_authenticated)])
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


@router.get("/codegraph/dead-code", response_model=CodeGraphResponse, dependencies=[Depends(require_authenticated)])
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
        cypher, _ = builder.build()
    elif request.query_type == "show_relationships":
        if not request.node_name:
            return {"error": "node_name is required for show_relationships query", "url": None}
        from core.security import sanitize_filename
        safe_name = sanitize_filename(request.node_name)
        builder = CypherBuilder(allowed_types={"Component", "Service", "Function", "Class", "Module", "File", "Entity"})
        builder.match_node(["Entity"], {"name": safe_name})
        builder.return_clause("n")
        builder.limit_clause(100)
        cypher, _ = builder.build()
    else:
        return {"error": "Raw Cypher queries are not supported for security reasons", "url": None}

    result = await retriever.visualize(cypher)

    return {"url": result.get("url"), "query_type": request.query_type}


@router.post("/codegraph/index/git", response_model=CodeGraphIndexResponse, dependencies=[Depends(require_authenticated)])
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


@router.post("/codegraph/index/zip", response_model=CodeGraphIndexResponse, dependencies=[Depends(require_authenticated)])
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


@router.post("/codegraph/index/url", response_model=CodeGraphIndexResponse, dependencies=[Depends(require_authenticated)])
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


@router.post("/codegraph/index/markdown", response_model=CodeGraphIndexResponse, dependencies=[Depends(require_authenticated)])
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


@router.post("/codegraph/index/confluence", response_model=CodeGraphIndexResponse, dependencies=[Depends(require_authenticated)])
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


@router.post("/codegraph/index/confluence/space", response_model=CodeGraphIndexConfluenceSpaceResponse, dependencies=[Depends(require_authenticated)])
async def codegraph_index_confluence_space(request: CodeGraphIndexConfluenceSpaceRequest):
    from documents.confluence import ConfluenceClient
    from retrieval.code_graph import _html_to_markdown, index_markdown_content

    client = ConfluenceClient(url=request.base_url, email=request.email, api_token=request.api_token)

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


@router.post("/codegraph/index/confluence/tree", response_model=CodeGraphIndexConfluenceTreeResponse, dependencies=[Depends(require_authenticated)])
async def codegraph_index_confluence_tree(request: CodeGraphIndexConfluenceTreeRequest):
    from documents.confluence import ConfluenceClient
    from retrieval.code_graph import _html_to_markdown, index_markdown_content

    client = ConfluenceClient(url=request.base_url, email=request.email, api_token=request.api_token)

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


@router.post("/codegraph/index/confluence/page", response_model=CodeGraphIndexConfluencePageResponse, dependencies=[Depends(require_authenticated)])
async def codegraph_index_confluence_page(request: CodeGraphIndexConfluencePageRequest):
    from documents.confluence import ConfluenceClient
    from retrieval.code_graph import _html_to_markdown, index_markdown_content

    client = ConfluenceClient(url=request.base_url, email=request.email, api_token=request.api_token)

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


@router.post("/search/colpal", response_model=ColPALSearchResponse, dependencies=[Depends(require_authenticated)])
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


@router.post("/search/ui-sketch", response_model=UISketchSearchResponse, dependencies=[Depends(require_authenticated)])
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


@router.post("/diagram/search", response_model=DiagramSearchResponse, dependencies=[Depends(require_authenticated)])
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
