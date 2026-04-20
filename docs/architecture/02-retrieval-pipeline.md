# Retrieval Pipeline Architecture

The retrieval pipeline provides multi-source, hybrid search capabilities across diverse data sources. This document covers the architecture, strategies, and components.

## Overview

```
Query → Preprocess → Source Selection → Parallel Retrieval → Fusion → Rerank → Citation → Response
```

## Retrieval Sources

The system supports **11 retrieval sources**:

| Source | File | Target | Use Case |
|--------|------|--------|----------|
| `DOCS` | `docs.py` | Qdrant | Documentation search |
| `CODE` | `code.py` | Qdrant | Code search |
| `GRAPH` | `graph.py` | FalkorDB | Knowledge graph queries |
| `CODE_GRAPH` | `code_graph.py` | CodeGraphContext | Code relationships |
| `TICKETS` | `ticket.py` | Qdrant | Jira/GitHub issues |
| `TELEMETRY` | `telemetry.py` | Elastic/Metrics | Logs and metrics |
| `DIAGRAM` | `diagram.py` | Qdrant + FalkorDB | Architecture diagrams |
| `UI_SKETCH` | `ui/retriever.py` | FalkorDB | UI component search |
| `COLBERT` | `colbert.py` | Qdrant | Late interaction embeddings |
| `KNOWLEDGE` | `knowledge.py` | Knowledge Graph | Platform patterns, ADRs |
| `MULTIMODAL` | - | VLM | Visual content |

## Core Components

### Retrieval Orchestrator (`retrieval/orchestrator.py`)

```python
class RetrievalOrchestrator:
    def __init__(self):
        self.docs_retriever = get_docs_retriever()
        self.code_retriever = get_code_retriever()
        self.graph_retriever = get_graph_retriever()
        # ... all 11 sources
```

| Method | Purpose |
|--------|---------|
| `retrieve()` | Main entry point, parallel/sequential retrieval |
| `route_hybrid()` | Route to enhanced hybrid retriever |
| `route_by_intent()` | Intent-based routing |
| `detect_platform_from_query()` | Platform detection (AWS/Azure/GCP) |

### Hybrid Retrieval (`retrieval/hybrid.py`)

| Class | Strategy |
|-------|----------|
| `HybridRetriever` | Single-source fallback |
| `EnhancedHybridRetriever` | Multi-source with entity cache |

## Hybrid Strategies

### 1. Vector-Only

Pure semantic search using embeddings.

### 2. Graph-Only

FalkorDB queries with Cypher.

### 3. Multi-Hop

Iterative traversal (1-hop → 2-hop → 3-hop neighbors).

### 4. Cascade

Stop when threshold is met.

### 5. Iterative

Query refinement loop (max 3 iterations).

## Fusion Methods

### 1. RRF (Reciprocal Rank Fusion)

```python
def reciprocal_rank_fusion(results_lists, k=60):
    scores = {}
    for results in results_lists:
        for rank, doc in enumerate(results):
            scores[doc.id] += scores.get(doc.id, 0) + 1 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

### 2. Score-Normalized

Min-max normalize scores across sources.

### 3. Weighted

Weights defined per source type.

### 4. Combined

Weighted + RRF hybrid.

## Reranking Pipeline

### Providers (`retrieval/rerank/`)

| Provider | Model | Language |
|----------|-------|----------|
| Cohere | rerank-english-v3.0 | English |
| BTE | BGE-reranker-base | Multilingual |
| SentenceTransformer | ms-marco-MiniLM-6 | English |
| Jina | jina-reranker-base-v1 | Multilingual |
| LlamaIndex | BGE | Multilingual |

### Strategies

| Strategy | Behavior |
|----------|----------|
| `SINGLE` | Single provider |
| `CASCADE` | Fallback to next provider |
| `ENSEMBLE` | Combine provider scores |

## Entity Cache

### Configuration

| Property | Value |
|----------|-------|
| Capacity | 500 entries |
| TTL | 1 hour |
| Eviction | LRU |

### Usage

```python
# Automatic caching in hybrid retrieval
result = await hybrid_retriever.search(
    query="function implementation",
    use_cache=True
)
```

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/entity/cache/stats` | GET | Cache statistics |
| `/entity/cache/invalidate` | POST | Clear cache |

## Citation Generation

### Styles (`retrieval/citations/`)

| Style | Format |
|-------|--------|
| `PARENTHETICAL` | `[source]` inline |
| `VERBATIM` | Quoted text snippets |
| `FOOTNOTE` | Numbered citations |
| `HIGLIGHT` | Bold text for matches |
| `STRUCTURED` | JSON with metadata |

### Citation Builder (`citations/builder.py`)

```python
class CitationBuilder:
    def build_citations(results, style=CitationStyle.PARENTHETICAL):
        # Map sources to citations
        # Format based on style
        return AnnotatedAnswer(text, citations)
```

## Knowledge Integration

### Knowledge Retriever (`retrieval/knowledge.py`)

Platform-aware retrieval querying:

| Repository | Content |
|------------|---------|
| Knowledge Graph | Platforms, services, technologies |
| Use Cases | 7 pre-built per platform |
| ADRs | 5 architecture decisions |
| Reference Architectures | 8 patterns |

### Platform Detection

Auto-detects from query keywords:

```python
DETECT_KEYWORDS = {
    "aws": ["lambda", "s3", "dynamodb", "ec2", "ecs", "eks"],
    "azure": ["function", "cosmos", "aks", "app service"],
    "gcp": ["cloud", "gke", "firestore", "cloudfunctions"],
    "sap": ["btp", "hana", "xsuaa", "kyma", "cap"],
    "tanzu": ["kubernetes", "spring", "pivotal"],
    "powerplatform": ["powerapps", "powerautomate", "dataverse"],
}
```

## Late Interaction (ColBERT)

### ColPali Integration (`retrieval/colbert.py`)

| Component | Purpose |
|-----------|---------|
| `ColBERTRetriever` | Qdrant-based retrieval |
| `ColBERTQdrantRetriever` | Qdrant + ColBERT hybrid |
| `ColBERTSearchClient` | MCP-compatible client |

### Usage

```python
# Late interaction for enhanced semantic search
result = await colbert_retriever.search(
    query="button component with icon",
    limit=10
)
```

## Query Classification

### Classifier (`retrieval/classifier.py`)

| Intent | Detection Pattern |
|--------|-----------------|
| `CODE_SEARCH` | Function names, "find", "implement" |
| `DOCS_SEARCH` | "how to", "documentation" |
| `TROUBLESHOOT` | "error", "issue", "not working" |
| `ARCHITECTURE` | "diagram", "design", "architecture" |

## Configuration

| Env Variable | Default | Purpose |
|--------------|---------|---------|
| `DEFAULT_RETRIEVAL_SOURCES` | All | Sources to query |
| `FUSION_METHOD` | rrf | Fusion algorithm |
| `DEFAULT_LIMIT` | 10 | Results per source |
| `ENTITY_CACHE_TTL` | 3600 | Cache TTL in seconds |
| `COLBERT_ENABLED` | false | Enable late interaction |

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/query` | POST | Main orchestration endpoint |
| `/hybrid/enhanced` | POST | Hybrid search with entity cache |
| `/rerank` | POST | ML-based reranking |
| `/citations` | POST | Citation generation |
| `/reasoning/chain` | POST | Chain-of-thoughts reasoning |
| `/reasoning/entity` | POST | Entity-aware reasoning |