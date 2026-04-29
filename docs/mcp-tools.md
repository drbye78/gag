# MCP Tools Reference

Complete reference for all 30+ MCP tools available in the system.

## Tool Categories

### 1. Search Tools

| Tool | Phase | Description |
|------|-------|-------------|
| `SearchTool` | CODING | General search across sources |
| `HybridSearchTool` | CODING | Multi-source hybrid search |
| `RerankTool` | CODING | ML-based reranking |
| `EntitySearchTool` | CODING | Entity graph search |

### 2. Reasoning Tools

| Tool | Phase | Description |
|------|-------|-------------|
| `ChainReasoningTool` | CODING | Chain-of-thought reasoning |
| `EntityReasoningTool` | CODING | Graph-based entity reasoning |
| `IterativeReasoningTool` | CODING | Iterative query refinement |

### 3. Architecture Tools

| Tool | Phase | Description |
|------|-------|-------------|
| `ArchitectureEvaluator` | ARCHITECTURE_DESIGN | Evaluate architecture patterns |
| `SecurityValidator` | ARCHITECTURE_DESIGN | Security validation |
| `CostEstimator` | ARCHITECTURE_DESIGN | Cost estimation |

### 4. Code Analysis Tools

| Tool | Phase | Description |
|------|-------|-------------|
| `FindCallersTool` | CODING | Find functions that call a given function |
| `FindCalleesTool` | CODING | Find functions called by a given function |
| `FindDeadCodeTool` | CODING | Find unused functions |
| `GetComplexityTool` | CODING | Get cyclomatic complexity |
| `ClassHierarchyTool` | CODING | Get class hierarchy |
| `GetModuleDepsTool` | CODING | Get module dependencies |

### 5. Infrastructure Search Tools

| Tool | Phase | Description |
|------|-------|-------------|
| `KubernetesSearchTool` | CODING | Search Kubernetes manifests |
| `HelmSearchTool` | CODING | Search Helm charts |
| `DockerfileSearchTool` | CODING | Search Dockerfiles |
| `GraphQLSearchTool` | CODING | Search GraphQL schemas |
| `IstioSearchTool` | CODING | Search Istio configurations |

### 6. Ingestion Tools

| Tool | Phase | Description |
|------|-------|-------------|
| `IngestSourceTool` | CODING | Ingest data from sources |
| `GetJobStatusTool` | CODING | Get ingestion job status |

### 7. Visual Tools

| Tool | Phase | Description |
|------|-------|-------------|
| `ExtractFromImageTool` | CODING | Extract text from images |
| `AnalyzeVisualTool` | CODING | Analyze visual content |
| `ParseDocumentAdvancedTool` | CODING | Advanced document parsing |

### 8. Day 2 Operations

| Tool | Description |
|------|-------------|
| Operations tools | Deployment, scaling, monitoring |

### 9. Testing

| Tool | Description |
|------|-------------|
| Testing tools | Test generation, mutation testing |

### 10. Feedback

| Tool | Description |
|------|-------------|
| Feedback tools | User feedback collection |

## PDLC Phases

Tools are organized by Product Development Lifecycle phase:

| Phase | ID | Tools |
|-------|-----|-------|
| Ideation | `ideation` | brainstorming, requirement generation |
| Business Requirements | `business_requirements` | stakeholder analysis |
| Architecture Design | `architecture_design` | evaluators, validators, cost estimation |
| Coding | `coding` | search, reasoning, code analysis |
| Testing | `testing` | test generation |
| Deployment | `deployment` | deployment tools |
| Production Observability | `production_observability` | monitoring, alerting |
| Feedback Loop | `feedback_loop` | feedback collection |
| Day 2 Operations | `day2_operations` | operations tooling |

## MCP Error Codes

| Code | Constant | Description |
|------|----------|-------------|
| -32001 | `TOOL_NOT_FOUND` | Tool does not exist |
| -32002 | `INVALID_PARAMS` | Invalid parameters |
| -32003 | `EXECUTION_FAILED` | Tool execution failed |
| -32004 | `RATELIMITED` | Rate limit exceeded |
| -32005 | `RESOURCE_NOT_FOUND` | Resource not found |
| -32006 | `PROMPT_NOT_FOUND` | Prompt not found |
| -32007 | `AUTHENTICATION_FAILED` | Authentication failed |
| -32008 | `AUTHORIZATION_DENIED` | Authorization denied |
| -32009 | `SESSION_EXPIRED` | Session expired |
| -32010 | `BATCH_CANCELLED` | Batch operation cancelled |

## MCP Protocol

### JSON-RPC 2.0

The system uses JSON-RPC 2.0 for MCP communication:

#### Methods

| Method | Purpose |
|--------|---------|
| `initialize` | Initialize MCP session, returns protocol version |
| `tools/list` | List all available tools |
| `tools/call` | Execute a single tool |
| `tools/call/batch` | Execute multiple tools |
| `resources/list` | List available resources |
| `resources/read` | Read a resource |
| `prompts/list` | List prompt templates |
| `prompts/get` | Get a prompt |
| `session/get` | Get session data |
| `session/set` | Set session data |
| `notifications/listen` | Subscribe to notifications |
| `notifications/unsubscribe` | Unsubscribe from notifications |

#### Session Management

```python
# Get session data
result = await mcp.call("session/get", {"key": "user_id"})

# Set session data
result = await mcp.call("session/set", {"key": "user_id", "value": "user123"})
```

#### Rate Limiting

Default: 100 requests per minute (sliding window)

```python
# Check rate limit status
result = await mcp.call("session/get", {"key": "rate_limit_remaining"})
```

## Usage Examples

### Python Client

```python
import httpx

async with httpx.AsyncClient() as client:
    # Initialize
    result = await client.post(
        "http://localhost:8000/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocol_version": "2024-11-05"},
            "id": 1
        }
    )
    
    # List tools
    result = await client.post(
        "http://localhost:8000/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }
    )
    
    # Call tool
    result = await client.post(
        "http://localhost:8000/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "SearchTool",
                "arguments": {"query": "Kubernetes deployment", "limit": 5}
            },
            "id": 3
        }
    )
```

### MCP Client Library

```python
from mcp import Client

async with Client("http://localhost:8000/mcp") as mcp:
    # List available tools
    tools = await mcp.list_tools()
    
    # Call a tool
    result = await mcp.call_tool(
        "SearchTool",
        {"query": "Kubernetes deployment", "limit": 5}
    )
```