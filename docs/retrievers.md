# Retrievers

Reference for all retrieval components in the system.

## Available Retrievers

| Retriever | Source | Description |
|----------|--------|-------------|
| `QdrantDocsRetriever` | Qdrant | Vector search in document embeddings |
| `KnowledgeRetriever` | FalkorDB | Knowledge graph queries |
| `GraphRetriever` | FalkorDB | Graph traversal for entities |
| `TicketRetriever` | Jira | Support ticket search |
| `TelemetryRetriever` | Prometheus/Elastic | Metrics/time series |
| `CodeRetriever` | Code graph | Code parsing |
| `CodeGraphRetriever` | CLI | CodeGraphContext (MCP) |
| `EntityCentricRetriever` | FalkorDB | Entity-level search |
| `ColBERTRetriever` | Qdrant | Late interaction |

## Quick Usage

```python
from retrieval.registry import get_retriever

docs = get_retriever("docs")
results = await docs.search("how to authenticate users")

knowledge = get_retriever("knowledge")
results = await knowledge.search("AWS serverless patterns")
```

## Per-Retriever Details

### QdrantDocsRetriever

Vector search using Qdrant embeddings.

```python
from retrieval.docs import QdrantDocsBackend

backend = QdrantDocsBackend(
    host="localhost",
    port=6333,
    collection="documents",
)
results = await backend.search("authentication", limit=10)
```

**Environment:**
- `QDRANT_HOST`, `QDRANT_PORT`
- `EMBEDDING_PROVIDER`

### KnowledgeRetriever

Knowledge graph queries via FalkorDB.

```python
from retrieval.knowledge import KnowledgeRetriever

retriever = KnowledgeRetriever(
    host="localhost",
    port=7379,
)
results = await retriever.search("pattern:micro*", limit=20)
```

**Environment:**
- `FALKORDB_HOST`, `FALKORDB_PORT`

### GraphRetriever

Generic graph search.

```python
from retrieval.graph import GraphRetriever

retriever = GraphRetriever(host="localhost", port=7379)
results = await retriever.search(query="MATCH (n) RETURN n LIMIT 10")
```

### TicketRetriever

Jira ticket search.

```python
from retrieval.ticket import TicketRetriever

retriever = TicketRetriever(
    url="https://company.atlassian.net",
    email="user@company.com",
    api_token="...",
)
results = await retriever.search("login error", status="open")
```

**Environment:**
- `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`

### TelemetryRetriever

Metrics retrieval from Prometheus/Elasticsearch.

```python
from retrieval.telemetry import TelemetryRetriever

retriever = TelemetryRetriever(
    url="http://localhost:9090",
)

# Query Prometheus
results = await retriever.query_prometheus('rate(requests_total[5m])')

# Query Elasticsearch
results = await retriever.query_elasticsearch({
    "query": {"match_all": {}}
})
```

**Environment:**
- `PROMETHEUS_URL`, `ELASTIC_URL`

### EntityCentricRetriever

Entity-level graph search with validation.

```python
from retrieval.entity_centric import EntityCentricRetriever

retriever = EntityCentricRetriever(
    host="localhost",
    port=7379,
)
results = await retriever.search_by_entity(
    "AuthenticationService",
    entity_type="Service",
    depth=2,
    limit=20,
)
```

**Validation:**
- Entity types: Person, Company, Document, UIElement, UISketch
- Relationship types: CONTAINS, DEPENDS_ON, IMPLEMENTS, EXTENDS, CALLS, REFERENCES

### ColBERTRetriever

Late-interaction retrieval using ColBERT.

```python
from retrieval.colbert import ColBERTRetriever

retriever = ColBERTRetriever(
    url="http://localhost:6333",
)
results = await retriever.search("JWT authentication", top_k=10)
```

**Environment:**
- `COLBERT_ENABLED=true`

## Registry

All retrievers auto-register on import. Add new retrievers:

```python
from retrieval.registry import registry

@registry.register("myretriever", module_path=__name__)
def create_my_retriever():
    return MyRetriever()
```

## Custom Retriever

```python
from retrieval.base import BaseRetriever

class MyRetriever(BaseRetriever):
    name = "myretriever"
    
    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict]:
        # Implementation
        return results
```

## Configuration

| Retriever | Priority | Fallback |
|-----------|----------|----------|
| docs | 10 | In-memory |
| knowledge | 20 | None |
| graph | 30 | None |
| code | 40 | None |
| codegraph | 50 | None |
| telemetry | 60 | None |
| ticket | 70 | None |