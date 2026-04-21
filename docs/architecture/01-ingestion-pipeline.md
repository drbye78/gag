# Ingestion Pipeline Architecture

The ingestion pipeline transforms raw data from various sources into indexed, searchable artifacts. This document provides a comprehensive overview of the architecture, components, and data flows.

## Overview

```
Input → Collect → Normalize → Parse → Chunk → Enrich → Embed → Index
                                              ↓
                                     GraphRAG (optional)
                                              ↓
                              VectorIndexer → Qdrant
                              GraphIndexer → FalkorDB
```

## Pipeline Components

### Core Pipeline (`ingestion/pipeline.py`)

| Class | Responsibility |
|------|----------------|
| `IngestionPipeline` | Main orchestrator: chunk → embed → index flow with job lifecycle |
| `JobRegistry` | In-memory registry with LRU eviction for tracking jobs |
| `JobStatus` | State machine: PENDING → CHUNKING → EMBEDDING → INDEXING → COMPLETED/FAILED |

**Job Lifecycle**:
- Progress: 0% → 20% → 50% → 80% → 100%
- Each job tracks: `job_id`, `source_type`, `chunks`, `embedded_chunks`, `error`

### Coordinator (`ingestion/orchestrator.py`)

| Class | Responsibility |
|------|----------------|
| `IngestionCoordinator` | Coordinates 7 specialized pipelines |
| `IngestionSource` | Enum: GIT, DOCUMENTS, TICKETS, TELEMETRY, KNOWLEDGE_BASE, ARCHITECTURE, REQUIREMENTS |

## Chunkers

The system includes **11 specialized chunkers** for different content types:

| Chunker | File | Purpose |
|--------|------|---------|
| `DocumentChunker` | `chunker.py` | Sentence-aware text chunking with language detection |
| `MarkdownChunker` | `chunker.py` | Line-based markdown chunking with overlap |
| `CodeChunker` | `chunker.py` | Entity extraction (classes, functions) for code |
| `StructuralChunker` | `structural_chunker.py` | Heading-based section extraction |
| `HierarchicalChunker` | `structural_chunker.py` | Depth-limited hierarchical chunking |
| `KubernetesChunker` | `k8s_chunker.py` | K8s manifest parsing (Deployment, Service, ConfigMap) |
| `HelmChartChunker` | `helm_chunker.py` | Helm chart metadata + values parsing |
| `DockerfileChunker` | `dockerfile_chunker.py` | Dockerfile instruction parsing |
| `IstioChunker` | `istio_chunker.py` | Istio CRD parsing (VirtualService, Gateway) |
| `GraphQLChunker` | `graphql_chunker.py` | GraphQL schema type/operation parsing |

### Chunking by Language

| Language | Strategy | Patterns |
|----------|----------|----------|
| Python | Regex entity extraction | `^class \w+`, `^def \w+`, `^async def \w+` |
| JavaScript/TypeScript | Generic function extraction | `function \w+`, brace counting |
| Go, Rust, Java | Fallback generic | Function extraction or fixed-size blocks |
| Markdown | Heading-aware | Line-by-line, respects heading boundaries |
| Dockerfile | Instruction-aware | FROM, RUN, COPY, ENTRYPOINT instructions |
| Kubernetes | Resource-type aware | Deployment, Service, ConfigMap separation |
| GraphQL | Schema-aware | Directive/field parsing |

### Chunker Registry (`chunker.py`, lines 469-505)

Auto-detects file types and routes to appropriate chunker:

```python
CHUNKER_REGISTRY = {
    ".py": "code",
    ".js": "code",
    ".md": "markdown",
    ".yaml": "k8s",
    ".yml": "k8s",
    "Dockerfile": "dockerfile",
    # ... more mappings
}
```

## Parsers

### Document Parsing (`documents/`)

| Parser | File | Supported Formats |
|--------|------|-------------------|
| `HybridDocumentParser` | `documents/parse.py` | PDF, DOCX, PPTX, TXT, Markdown |
| `DiagramParser` | `documents/diagram_parser.py` | UML, C4, BPMN, PlantUML, Mermaid |
| `MultimodalParser` | `documents/multimodal.py` | Images via VLM |

### Client Sources

| Client | File | Purpose |
|--------|------|---------|
| `ConfluenceClient` | `documents/confluence.py` | Fetch Confluence pages |
| `WebDAVClient` | `documents/webdav.py` | WebDAV file access |
| `JiraClient` | `ticket/client.py` | Jira tickets |
| `PrometheusClient` | `telemetry/client.py` | Prometheus metrics |
| `ElasticsearchClient` | `telemetry/client.py` | Elasticsearch logs |
| `LokiClient` | `telemetry/client.py` | Loki log aggregation |

## Indexers

### Vector Indexing (`ingestion/indexer.py`)

| Indexer | Target | Capabilities |
|--------|--------|--------------|
| `VectorIndexer` | Qdrant | Batch upserts, delete by filter, TTL support |

**Index Schema**:
```json
{
  "id": "doc_id",
  "text": "chunked content",
  "source": "gitlab",
  "file_path": "src/main.py",
  "language": "python",
  "metadata": {...}
}
```

### Graph Indexing (`ingestion/indexer.py`)

| Indexer | Target | Edge Types |
|--------|--------|-----------|
| `GraphIndexer` | FalkorDB | CALLS, DEFINES, IMPORTS, RETURNS, CONTAINS, INHERITS, IMPLEMENTS, DEPENDS_ON, RELATED_TO, DOCUMENTED_BY |

## Embedding Pipeline

### Providers (`ingestion/embedder.py`)

| Provider | Model | Notes |
|----------|-------|-------|
| OpenAI | `text-embedding-3-small` | Default |
| Qwen | `text-embedding-v3` | Language-aware |
| Ollama | `nomic-embed-text` | Local deployment |
| Qdrant | Built-in | Fallback |

### Features

- **SHA-256 LRU Cache**: 10,000 entries, 24h TTL
- **Language Detection**: Russian/English model selection
- **Batch Embedding**: Concurrent requests with semaphore control

## GraphRAG Pipeline

When `use_graphrag=true`, entities and relationships are extracted:

```
Document → CrossRef → Structural Chunk → Entity Extract → Relationship Infer → Community Detect → Graph Index
```

### Components

| Component | File | Method |
|-----------|------|--------|
| `DocumentEntityExtractor` | `entity_extractor.py` | LLM-based or regex |
| `LightweightEntityExtractor` | `entity_extractor.py` | Regex-only (faster) |
| `RelationshipInferrer` | `relationship_inferrer.py` | LLM-based |
| `LightweightRelationshipInferrer` | `relationship_inferrer.py` | Co-occurrence |
| `CommunityDetector` | `community_detector.py` | BFS + LLM summarization |

### Entity Types

- `person`, `organization`, `concept`, `event`
- `location`, `product`, `technology`
- `document`, `process`

### Relationship Types

- `related_to`, `part_of`, `works_for`, `uses`
- `depends_on`, `implements`, `inherits_from`

## Specialized Pipelines

### 1. Git Ingestion (`git/pipeline.py`)

Flow: Clone → Parse → Chunk → Embed → Index

| Component | File |
|-----------|------|
| `GitIngestionPipeline` | `git/pipeline.py` |
| `GitRepoManager` | `git/repo.py` |
| `CodeParser` | `git/parser.py` |

### 2. Document Pipeline (`documents/pipeline.py`)

Flow: Upload → Parse → Version → Index

Supports: PDF, DOCX, Confluence, WebDAV

### 3. Ticket Pipeline (`ticket/pipeline.py`)

Sources: Jira, GitHub Issues

### 4. Telemetry Pipeline (`telemetry/pipeline.py`)

Sources: Prometheus, Elasticsearch, Loki

### 5. Knowledge Base Pipeline (`knowledge_base/pipeline.py`)

Sources: StackOverflow, Reddit, Forums

### 6. Architecture Pipeline (`architecture/pipeline.py`)

Sources: Diagrams from Confluence, GitHub, local files

### 7. Requirements Pipeline (`requirements/pipeline.py`)

Sources: Jira Requirements, Confluence, Local files

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/ingestion/ingest` | POST | Single document ingestion |
| `/ingestion/batch` | POST | Batch ingestion |
| `/ingestion/codebase` | POST | Full codebase ingestion |
| `/ingestion/jobs` | GET | List jobs |
| `/ingestion/jobs/{id}` | GET | Job status |
| `/ingestion/jobs/{id}` | DELETE | Cancel job |

## Configuration

| Env Variable | Default | Purpose |
|--------------|---------|---------|
| `EMBEDDING_PROVIDER` | openai | Embedding provider |
| `EMBEDDER_MODEL` | text-embedding-3-small | Model name |
| `GRAPH_RAG_ENABLED` | false | Enable GraphRAG |
| `USE_LLM_EXTRACTION` | false | Use LLM for entity extraction |
| `CHUNK_SIZE` | 1024 | Default chunk size |
| `CHUNK_OVERLAP` | 128 | Chunk overlap |

## Incremental Ingestion

Documents are skipped if their SHA-256 hash matches a previously indexed version. Enable with `incremental: true` in the request.