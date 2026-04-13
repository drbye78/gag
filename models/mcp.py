"""
MCP Schema - Model Context Protocol JSON-RPC models.

Defines request/response schemas and tool definitions
for MCP interface.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class MCPRequest(BaseModel):
    jsonrpc: str
    id: Optional[str]
    method: str
    params: Optional[Dict[str, Any]]


class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class MCPToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]


class MCPToolResult(BaseModel):
    content: List[Dict[str, Any]]
    is_error: Optional[bool]


class MCPInitializeRequest(BaseModel):
    protocol_version: str
    capabilities: Dict[str, Any]
    client_info: Dict[str, Any]


class MCPInitializedResponse(BaseModel):
    protocol_version: str
    capabilities: Dict[str, Any]
    server_info: Dict[str, Any]


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
            description="Search across all document and code sources",
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
    ]


MCP_TOOLS = get_mcp_tools()
