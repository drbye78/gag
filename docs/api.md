# API Reference

Base URL: `http://localhost:8000`

## Core Endpoints

### `GET /`
Returns service information and available endpoints.

```json
{
  "service": "SAP BTP Engineering Intelligence",
  "version": "3.0.0",
  "endpoints": ["/health", "/query", "/mcp", "/search/*", "/codegraph/*", ...]
}
```

### `GET /health`
Health check with dependency status.

```json
{
  "status": "healthy",
  "version": "3.0.0"
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

## GraphRAG Endpoints

GraphRAG provides entity-aware querying with knowledge graph integration.

### `POST /graphrag/query`
Query with entity-aware reasoning and knowledge graph traversal.

**Request:**
```json
{
  "query": "How is John related to Acme Corp?",
  "include_entities": true,
  "include_relationships": true,
  "include_communities": false,
  "max_hops": 3
}
```

**Response:**
```json
{
  "query": "How is John related to Acme Corp?",
  "answer": "John works at Acme Corp...",
  "entities": [{"name": "John", "type": "PERSON"}, {"name": "Acme Corp", "type": "ORGANIZATION"}],
  "relationships": [{"node": {"name": "Acme Corp"}, "relationship": "WORKS_FOR"}],
  "communities": [],
  "confidence": 0.85,
  "sources": [{"content": "...", "score": 0.9}],
  "took_ms": 250
}
```

### `GET /graphrag/entities`
List all entities in the knowledge graph.

**Query Parameters:**
- `source_id` (optional) — Filter by source document
- `entity_type` (optional) — Filter by entity type (PERSON, ORGANIZATION, etc.)
- `limit` (default: 100) — Max results

**Response:**
```json
{
  "entities": [{"id": "...", "name": "John", "type": "PERSON"}],
  "total": 1
}
```

### `GET /graphrag/entities/{entity_id}`
Get specific entity with its relationships.

**Response:**
```json
{
  "entity": {"id": "...", "name": "John", "type": "PERSON", "description": "..."},
  "relationships": [{"node": {"name": "Acme Corp"}, "relationship": "WORKS_FOR"}]
}
```

### `GET /graphrag/relationships`
List all relationships in the knowledge graph.

**Query Parameters:**
- `source_id` (optional) — Filter by source
- `relationship_type` (optional) — Filter by type
- `limit` (default: 100) — Max results

### `GET /graphrag/communities`
List all communities (entity clusters).

**Query Parameters:**
- `source_id` (optional) — Filter by source
- `min_size` (default: 1) — Minimum community size
- `limit` (default: 50) — Max results

**Response:**
```json
[
  {
    "id": "community-1",
    "name": "AI Team",
    "members": [{"name": "John", "type": "PERSON"}],
    "size": 3
  }
]
```

### `GET /graphrag/communities/{community_id}`
Get specific community details.

### `GET /graphrag/stats`
Get GraphRAG system statistics.

**Response:**
```json
{
  "total_entities": 150,
  "total_relationships": 320,
  "total_communities": 12,
  "entity_types": {"PERSON": 50, "ORGANIZATION": 30, "TECHNOLOGY": 70},
  "relationship_types": {"WORKS_FOR": 40, "DEPENDS_ON": 80},
  "avg_entities_per_community": 12.5
}
```

---

## Tooling Search

Search across Kubernetes manifests, Helm charts, Dockerfiles, GraphQL schemas, and Istio configurations.

### `POST /search/kubernetes`
Search Kubernetes manifests.

**Request:**
```json
{
  "query": "deployment replicas",
  "limit": 10,
  "entity_type": "Deployment"
}
```

**Response:**
```json
{
  "query": "deployment replicas",
  "results": [{"content": "...", "metadata": {"kind": "Deployment", "namespace": "default"}}],
  "tool": "kubernetes",
  "count": 1
}
```

Supported entity types: `Deployment`, `Service`, `ConfigMap`, `Pod`, `Ingress`, `Secret`, `StatefulSet`, `DaemonSet`

### `POST /search/helm`
Search Helm charts.

**Request:**
```json
{
  "query": "values image",
  "limit": 10
}
```

### `POST /search/dockerfile`
Search Dockerfiles.

**Request:**
```json
{
  "query": "npm install",
  "limit": 10
}
```

### `POST /search/graphql`
Search GraphQL schemas.

**Request:**
```json
{
  "query": "type Query",
  "limit": 10
}
```

### `POST /search/istio`
Search Istio configurations.

**Request:**
```json
{
  "query": "VirtualService",
  "limit": 10
}
```

---

## CodeGraph

Code analysis via CodeGraphContext MCP - find code relationships, complexity, and visualize call graphs.

### `POST /codegraph/find`
Find code snippets matching a query.

**Request:**
```json
{
  "query": "get_user",
  "fuzzy": false,
  "edit_distance": 2,
  "repo_path": "/path/to/repo",
  "limit": 10
}
```

**Response:**
```json
{
  "query": "get_user",
  "results": [{"name": "get_user", "path": "src/auth.py", "line": 42}],
  "method": "find_code",
  "count": 1
}
```

### `POST /codegraph/relationships`
Find code relationships (callers, callees, imports, etc.).

**Request:**
```json
{
  "query_type": "find_callers",
  "target": "process_request",
  "context": "src/handler.py",
  "repo_path": "/path/to/repo"
}
```

Supported query types: `find_callers`, `find_callees`, `find_all_callers`, `find_all_callees`, `find_importers`, `class_hierarchy`, `overrides`, `dead_code`, `complexity`, `call_chain`, `module_deps`

### `GET /codegraph/complex`
Find most complex functions.

**Query Parameters:**
- `limit` (default: 10)
- `repo_path` (optional)

### `GET /codegraph/dead-code`
Find unused functions.

**Query Parameters:**
- `repo_path` (optional)
- `exclude_decorated_with` (optional, e.g., `["@app.route"]`)

### `POST /codegraph/visualize`
Generate visualization URL for a Cypher query.

**Request:**
```json
{
  "cypher_query": "MATCH (f:Function)-[:CALLS]->(g:Function) RETURN f.name, g.name"
}
```

**Response:**
```json
{
  "url": "https://...",
  "cypher_query": "MATCH ..."
}
```

---

## Multi-Modal Search

Search using visual embeddings and UI sketch similarity.

### `POST /search/colpal`
Search using ColPali visual embeddings.

**Request:**
```json
{
  "query": "login form",
  "limit": 10
}
```

**Response:**
```json
{
  "query": "login form",
  "results": [{"sketch_id": "...", "title": "Login Screen"}],
  "method": "colpal",
  "count": 1
}
```

### `POST /search/ui-sketch`
Find similar UI sketches by structural elements.

**Request:**
```json
{
  "sketch_data": "Button",
  "limit": 10
}
```

**Response:**
```json
{
  "results": [{"sketch_id": "...", "title": "Submit Form"}],
  "method": "ui_sketch",
  "count": 1
}
```

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
