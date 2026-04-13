# API Reference

Base URL: `http://localhost:8000`

## Core Endpoints

### `GET /`
Returns service information and available endpoints.

```json
{
  "service": "SAP BTP Engineering Intelligence",
  "version": "2.4.0",
  "endpoints": ["/health", "/query", "/mcp", ...]
}
```

### `GET /health`
Health check with dependency status.

```json
{
  "status": "healthy",
  "version": "2.4.0"
}
```

Status values: `healthy`, `degraded`, `unhealthy`

### `POST /query`
Main query endpoint. Sends the query through the orchestration engine (Plan → Retrieve → Reason → Execute).

**Request:**
```json
{
  "query": "How does authentication work?",
  "sources": ["docs", "code"],
  "limit": 10
}
```

**Response:**
```json
{
  "query": "How does authentication work?",
  "answer": "Authentication uses JWT tokens...",
  "sources": [{"id": "1", "content": "...", "score": 0.9}],
  "metadata": {"intent": "explain", "execution": {"iterations": 1, "took_ms": 250}}
}
```

---

## MCP (Model Context Protocol)

### `POST /mcp`
JSON-RPC 2.0 handler for MCP clients.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/call",
  "params": {"name": "search", "arguments": {"query": "auth"}}
}
```

Supported methods: `initialize`, `tools/list`, `tools/call`, `tools/call/batch`, `resources/list`, `resources/read`, `prompts/list`, `prompts/get`, `query`

### `GET /mcp`
Lists all available MCP tools and schema.

---

## Multimodal

### `POST /multimodal/extract`
Extract text from images using Vision Language Model.

**Request:**
```json
{
  "image_url": "https://example.com/diagram.png",
  "prompt": "Extract all text from this image"
}
```

---

## Reasoning

### `POST /reasoning/chain`
Chain-of-thoughts reasoning on a set of facts.

**Request:**
```json
{
  "query": "What is the relationship between AuthService and APIGateway?",
  "facts": [{"content": "AuthService validates tokens for APIGateway"}],
  "mode": "chain_of_thoughts"
}
```

**Response:**
```json
{
  "query": "...",
  "answer": "AuthService is responsible for...",
  "reasoning_mode": "chain_of_thoughts",
  "confidence": 0.85,
  "steps": [{"thought": "...", "action": "...", "observation": "..."}]
}
```

### `POST /reasoning/entity`
Entity-aware reasoning with knowledge graph traversal.

Same request/response format as `/reasoning/chain` but uses graph context.

---

## Retrieval

### `POST /rerank`
Rerank search results using ML models.

**Request:**
```json
{
  "query": "authentication",
  "results": [{"content": "...", "score": 0.7}],
  "provider": "cohere",
  "strategy": "single"
}
```

**Response:**
```json
{
  "query": "authentication",
  "results": [{"content": "...", "score": 0.85, "id": "1"}],
  "reranked": true
}
```

### `POST /citations`
Generate citations for an answer.

**Request:**
```json
{
  "answer": "The system uses JWT for auth",
  "sources": [{"source_id": "doc1", "content": "..."}],
  "style": "parenthetical"
}
```

Supported styles: `parenthetical`, `verbatim`, `footnote`, `highlight`, `structured`

### `POST /hybrid/enhanced`
Enhanced hybrid search with entity graph caching and reasoning.

**Request:** Same as `POST /query`

**Response:** Includes `cache_stats` with hit rate, size, and utilization.

---

## Entity Graph Cache

### `GET /entity/cache/stats`
Returns entity cache statistics.

```json
{
  "size": 42,
  "capacity": 500,
  "hit_rate": 0.73,
  "hits": 156,
  "misses": 58,
  "utilization_pct": 8.4,
  "oldest_entry": {"entity_name": "AuthService", "age_seconds": 3600, "hit_count": 12}
}
```

### `POST /entity/cache/invalidate`
Invalidate cache entries.

**Request:**
```json
{"entity_name": "AuthService"}
```
Or `{}` to clear entire cache.

**Response:**
```json
{"invalidated": true, "entity_name": "AuthService", "message": "Invalidated 'AuthService'"}
```

---

## Ingestion

### `POST /ingestion/ingest`
Ingest a single document.

**Request:**
```json
{
  "content": "Document text content...",
  "source_id": "doc-123",
  "source_type": "document",
  "metadata": {"author": "John"},
  "index": true
}
```

### `POST /ingestion/batch`
Ingest multiple documents.

**Request:**
```json
{
  "documents": [
    {"content": "...", "id": "doc1", "type": "document"},
    {"content": "...", "id": "doc2", "type": "document"}
  ],
  "parallel": true
}
```

### `POST /ingestion/codebase`
Ingest a codebase.

**Request:**
```json
{
  "files": {"src/main.py": "def hello(): ...", "src/utils.py": "..."},
  "index_graph": false
}
```

### `GET /ingestion/jobs`
List recent ingestion jobs. Query param: `limit` (default 50).

### `GET /ingestion/jobs/{job_id}`
Get job status.

### `DELETE /ingestion/jobs/{job_id}`
Cancel a pending/processing job.

---

## Git

### `POST /git/clone`
Clone and ingest a git repository.

### `GET /git/repos`
List ingested repositories.

### `GET /git/repos/{repo_id}`
Get repository details.

### `GET /git/repos/{repo_id}/files`
List files in a repository.

### `GET /git/repos/{repo_id}/files/{file_path:path}`
Get file content.

### `POST /git/credentials`
Store git credentials.

### `GET /git/credentials`
List stored credentials.

### `DELETE /git/credentials/{credential_id}`
Remove a credential.

### `GET /git/jobs`, `GET /git/jobs/{job_id}`, `DELETE /git/jobs/{job_id}`
Job management.

---

## Documents

### `POST /documents/upload`
Upload a document for ingestion.

### `POST /documents/upload/batch`
Batch upload documents.

### `GET /documents/`
List all documents.

### `GET /documents/{document_id}`
Get document metadata.

### `GET /documents/{document_id}/content`
Get document content.

### `GET /documents/{document_id}/versions`
List document versions.

### `POST /documents/confluence/space`
Ingest a Confluence space.

### `POST /documents/confluence/pages`
Ingest specific Confluence pages.

### `POST /documents/webdav/sync`
Sync documents from WebDAV.

---

## Error Responses

All endpoints return structured JSON errors:

```json
{
  "error": "Validation Error",
  "detail": "query: Value error, query must not be empty",
  "status_code": 422
}
```

Common status codes:
- `400` — Bad Request (invalid JSON, missing fields)
- `401` — Unauthorized
- `403` — Forbidden (missing permission)
- `404` — Not Found
- `422` — Validation Error (Pydantic validation failed)
- `429` — Rate Limited
- `500` — Internal Server Error
