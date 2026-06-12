"""
MCP Schema - Model Context Protocol JSON-RPC models.

Defines request/response schemas and tool definitions
for MCP interface.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MCPRequest(BaseModel):
    jsonrpc: str = Field(..., examples=["2.0"])
    id: Optional[str] = Field(None, examples=["req-001"])
    method: str = Field(..., examples=["tools/list"])
    params: Optional[Dict[str, Any]] = Field(
        None, examples=[{"name": "search", "arguments": {"query": "k8s"}}]
    )


class MCPResponse(BaseModel):
    jsonrpc: str = Field("2.0", examples=["2.0"])
    id: Optional[str] = Field(None, examples=["req-001"])
    result: Optional[Dict[str, Any]] = Field(None, examples=[{"tools": []}])
    error: Optional[Dict[str, Any]] = Field(
        None, examples=[{"code": -32001, "message": "Tool not found"}]
    )


class MCPToolDefinition(BaseModel):
    name: str = Field(..., examples=["search"])
    description: str = Field(..., examples=["Search across all document and code sources"])
    input_schema: Dict[str, Any] = Field(
        ...,
        examples=[
            {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
        ],
    )


class MCPToolCall(BaseModel):
    name: str = Field(..., examples=["search"])
    arguments: Dict[str, Any] = Field(..., examples=[{"query": "kubernetes deployment"}])


class MCPToolResult(BaseModel):
    content: List[Dict[str, Any]] = Field(..., examples=[[{"type": "text", "text": "result"}]])
    is_error: Optional[bool] = Field(None, examples=[False])


class MCPInitializeRequest(BaseModel):
    protocol_version: str = Field(..., examples=["1.0"])
    capabilities: Dict[str, Any] = Field(..., examples=[{"tools": True}])
    client_info: Dict[str, Any] = Field(..., examples=[{"name": "test-client", "version": "1.0"}])


class MCPInitializedResponse(BaseModel):
    protocol_version: str = Field(..., examples=["1.0"])
    capabilities: Dict[str, Any] = Field(..., examples=[{"tools": True, "sessions": True}])
    server_info: Dict[str, Any] = Field(
        ..., examples=[{"name": "Engineering Intelligence System", "version": "3.2.0"}]
    )


def get_mcp_tools() -> List[MCPToolDefinition]:
    return [
        MCPToolDefinition(
            name="architecture_evaluate",
            description="Evaluate architecture design for quality, consistency, and best practices",
            input_schema={
                "type": "object",
                "properties": {
                    "architecture_id": {"type": "string"},
                    "criteria": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["architecture_id"],
            },
        ),
        MCPToolDefinition(
            name="security_validate",
            description="Validate security aspects of code or architecture",
            input_schema={
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                    "target_type": {
                        "type": "string",
                        "enum": ["code", "architecture", "deployment"],
                    },
                },
                "required": ["target", "target_type"],
            },
        ),
        MCPToolDefinition(
            name="cost_estimate",
            description="Estimate infrastructure and operational costs",
            input_schema={
                "type": "object",
                "properties": {
                    "architecture_id": {"type": "string"},
                    "traffic_estimate": {"type": "string"},
                },
                "required": ["architecture_id"],
            },
        ),
        MCPToolDefinition(
            name="search",
            description="Search across all document and code sources (supports multilingual)",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                    "language": {"type": "string", "default": "auto"},
                },
                "required": ["query"],
            },
        ),
        MCPToolDefinition(
            name="diagram_search",
            description="Search architecture diagrams (UML, C4, BPMN, PlantUML)",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "diagram_type": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        ),
        MCPToolDefinition(
            name="diagram_index",
            description="Index a diagram for retrieval",
            input_schema={
                "type": "object",
                "properties": {
                    "diagram_content": {"type": "string"},
                    "doc_id": {"type": "string"},
                    "diagram_type": {"type": "string"},
                },
                "required": ["diagram_content", "doc_id"],
            },
        ),
        MCPToolDefinition(
            name="multilingual_detect",
            description="Detect language of text (Russian, English, etc.)",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                },
                "required": ["text"],
            },
        ),
        MCPToolDefinition(
            name="hybrid_search",
            description="Advanced hybrid search with reasoning and reranking",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                    "use_reasoning": {"type": "boolean", "default": True},
                },
                "required": ["query"],
            },
        ),
        MCPToolDefinition(
            name="rerank",
            description="Rerank search results using ML models",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "results": {"type": "array"},
                },
                "required": ["query", "results"],
            },
        ),
        MCPToolDefinition(
            name="chain_reasoning",
            description="Execute chain-of-thoughts reasoning on facts",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "facts": {"type": "array"},
                },
                "required": ["query", "facts"],
            },
        ),
        MCPToolDefinition(
            name="entity_reasoning",
            description="Entity-aware reasoning with graph traversal",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "facts": {"type": "array"},
                    "entity_graph": {"type": "object"},
                },
                "required": ["query"],
            },
        ),
        MCPToolDefinition(
            name="iterative_reasoning",
            description="Iterative retrieval with query refinement",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_iterations": {"type": "integer", "default": 3},
                },
                "required": ["query"],
            },
        ),
        MCPToolDefinition(
            name="query_graph",
            description="Query knowledge graph for relationships",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        ),
        MCPToolDefinition(
            name="entity_search",
            description="Search by entity name with graph traversal",
            input_schema={
                "type": "object",
                "properties": {
                    "entity_name": {"type": "string"},
                    "depth": {"type": "integer", "default": 2},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["entity_name"],
            },
        ),
        MCPToolDefinition(
            name="ingest_source",
            description="Ingest content from a source",
            input_schema={
                "type": "object",
                "properties": {
                    "source_type": {"type": "string"},
                    "content": {"type": "string"},
                    "metadata": {"type": "object"},
                },
                "required": ["source_type"],
            },
        ),
        MCPToolDefinition(
            name="get_job_status",
            description="Get status of ingestion job",
            input_schema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                },
                "required": ["job_id"],
            },
        ),
        MCPToolDefinition(
            name="kubernetes_search",
            description="Search Kubernetes manifests (Deployments, Services, ConfigMaps, etc.)",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                    "kind": {"type": "string"},
                    "namespace": {"type": "string"},
                    "entity_type": {"type": "string"},
                },
                "required": ["query"],
            },
        ),
        MCPToolDefinition(
            name="helm_search",
            description="Search Helm charts",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                    "chart_name": {"type": "string"},
                    "version": {"type": "string"},
                },
                "required": ["query"],
            },
        ),
        MCPToolDefinition(
            name="dockerfile_search",
            description="Search Dockerfiles",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                    "instruction": {"type": "string"},
                    "base_image": {"type": "string"},
                },
                "required": ["query"],
            },
        ),
        MCPToolDefinition(
            name="graphql_search",
            description="Search GraphQL schemas",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                    "kind": {"type": "string"},
                    "type_name": {"type": "string"},
                },
                "required": ["query"],
            },
        ),
        MCPToolDefinition(
            name="istio_search",
            description="Search Istio networking resources (VirtualService, DestinationRule, etc.)",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                    "kind": {"type": "string"},
                    "namespace": {"type": "string"},
                    "host": {"type": "string"},
                },
                "required": ["query"],
            },
        ),
        MCPToolDefinition(
            name="find_callers",
            description="Find functions that call a specific function",
            input_schema={
                "type": "object",
                "properties": {
                    "function_name": {"type": "string"},
                    "limit": {"type": "integer", "default": 20},
                },
                "required": ["function_name"],
            },
        ),
        MCPToolDefinition(
            name="find_callees",
            description="Find functions called by a specific function",
            input_schema={
                "type": "object",
                "properties": {
                    "function_name": {"type": "string"},
                    "limit": {"type": "integer", "default": 20},
                },
                "required": ["function_name"],
            },
        ),
        MCPToolDefinition(
            name="find_dead_code",
            description="Find unused/dead code in the codebase",
            input_schema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 20},
                },
            },
        ),
        MCPToolDefinition(
            name="get_complexity",
            description="Get cyclomatic complexity of a function",
            input_schema={
                "type": "object",
                "properties": {
                    "function_name": {"type": "string"},
                },
                "required": ["function_name"],
            },
        ),
        MCPToolDefinition(
            name="class_hierarchy",
            description="Get class inheritance hierarchy",
            input_schema={
                "type": "object",
                "properties": {
                    "class_name": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["class_name"],
            },
        ),
        MCPToolDefinition(
            name="get_module_deps",
            description="Get module dependencies",
            input_schema={
                "type": "object",
                "properties": {
                    "module": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        ),
        MCPToolDefinition(
            name="extract_from_image",
            description="Extract text from images using VLM (OCR)",
            input_schema={
                "type": "object",
                "properties": {
                    "image_url": {"type": "string"},
                    "prompt": {"type": "string", "default": "Extract all text from this image"},
                },
                "required": ["image_url"],
            },
        ),
        MCPToolDefinition(
            name="analyze_visual",
            description="Analyze images/diagrams using Vision Language Model",
            input_schema={
                "type": "object",
                "properties": {
                    "image_url": {"type": "string"},
                    "prompt": {"type": "string"},
                },
                "required": ["image_url", "prompt"],
            },
        ),
        MCPToolDefinition(
            name="parse_document_advanced",
            description="Parse documents with OCR using Docling",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "url": {"type": "string"},
                    "use_ocr": {"type": "boolean", "default": True},
                },
            },
        ),
        MCPToolDefinition(
            name="colpal_search",
            description="Search images using visual embeddings (ColPali)",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        ),
        MCPToolDefinition(
            name="ui_sketch_search",
            description="Search UI sketches and mockups",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                    "element_type": {"type": "string"},
                },
                "required": ["query"],
            },
        ),
    ]


MCP_TOOLS = get_mcp_tools()
