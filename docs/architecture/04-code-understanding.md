# Source Code Understanding Architecture

The system provides deep code understanding through entity extraction, relationship inference, and graph-based queries. This document covers the components and capabilities.

## Architecture Overview

```
Code Source → Chunking → Entity Extraction → Relationship Inference → Graph Indexing
                                                                           ↓
                                               Query ← CodeGraphRetriever (MCP + CLI)
```

## Core Components

### GraphRAG Pipeline (`ingestion/graphrag/pipeline.py`)

Primary entity extraction and relationship inference pipeline:

```
Document → CrossRef → Structural Chunk → Entity Extract → Relationship Infer → Community Detect → Graph Index
```

| Component | File | Purpose |
|-----------|------|---------|
| `GraphRAGPipeline` | `pipeline.py` | Main orchestrator |
| `DocumentEntityExtractor` | `entity_extractor.py` | LLM-based entity extraction |
| `LightweightEntityExtractor` | `entity_extractor.py` | Regex-based (faster) |
| `RelationshipInferrer` | `relationship_inferrer.py` | LLM-based relationship inference |
| `LightweightRelationshipInferrer` | `relationship_inferrer.py` | Co-occurrence based |
| `CommunityDetector` | `community_detector.py` | Graph clustering + summarization |

## Entity Extraction

### Entity Types (`entity_extractor.py`)

| Type | Example |
|------|---------|
| `person` | "John Doe", "Alice" |
| `organization` | "Acme Corp", "Google" |
| `concept` | "Authentication", "REST API" |
| `event` | "Deployment", "Release v2.0" |
| `location` | "US-East", "eu-west-1" |
| `product` | "Lambda", "Kubernetes" |
| `technology` | "Python", "PostgreSQL" |
| `document` | "README.md", "API Spec" |
| `process` | "CI/CD Pipeline", "Deployment" |

### Extraction Methods

#### LLM-Based (`DocumentEntityExtractor`)

```python
# Uses LLM to extract entities from text chunks
extractor = DocumentEntityExtractor()
entities = await extractor.extract_entities(
    text="The function handles JWT authentication using Python.",
    chunk_id="chunk_123"
)
# Results: [Entity(type="technology", value="JWT"), Entity(type="technology", value="Python")]
```

#### Lightweight (`LightweightEntityExtractor`)

Regex-based for faster processing:

```python
# Patterns for technology detection
TECH_PATTERNS = [
    r"\b(Python|JavaScript|Go|Rust|Java|TypeScript)\b",
    r"\b(Kubernetes|Docker|Redis|PostgreSQL)\b",
    r"\b(API|gRPC|REST|JWT|OAuth)\b",
]
```

## Relationship Inference

### Relationship Types (`relationship_inferrer.py`)

| Type | Direction | Example |
|------|-----------|----------|
| `related_to` | Bidirectional | User ↔ Profile |
| `part_of` | A → B | Address → User |
| `works_for` | Person → Org | Alice → Acme Corp |
| `uses` | A → B | LoginService → AuthService |
| `depends_on` | A → B | Frontend → Backend API |
| `implements` | A → B | MyClass → Interface |
| `inherits_from` | A → B | Dog → Animal |

### Inference Methods

#### LLM-Based

```python
inferrer = RelationshipInferrer()
relationships = await inferrer.infer_relationships(
    entities=[Entity1, Entity2],
    context="The service calls the authentication API"
)
# Results: [Relationship(source=Entity1, target=Entity2, type="uses")]
```

#### Lightweight (Co-occurrence)

```python
# If two entities appear within 200 characters, mark as related
if entity_distance(entity_a, entity_b) < 200:
    relationships.append(Relationship(type="related_to"))
```

## Community Detection

### BFS-Based Detection

```python
detector = CommunityDetector()
communities = detector.detect_communities(relationships, min_size=3)

# Each community represents a cluster of related entities
for community in communities:
    summary = await detector.summarize(community)
    # LLM generates natural language summary
```

## Code Chunking by Language

### Python (`CodeChunker._extract_python_entities()`)

```python
# Extract classes and functions with full body
PATTERNS = [
    r'^class (\w+).*?:',      # class MyClass:
    r'^def (\w+).*?:',       # def my_function():
    r'^async def (\w+).*:',  # async def async_func():
]
```

### JavaScript/TypeScript (`CodeChunker._extract_generic_entities()`)

```python
# Generic function extraction with brace counting
PATTERNS = [
    r'function (\w+)',
    r'const (\w+) = \(',
    r'(\w+):.*?=>',          # arrow functions
]
```

### Language Support Summary

| Language | Strategy | Notes |
|----------|----------|-------|
| Python | Entity extraction | Classes, functions, async |
| JavaScript | Generic | Functions, arrow, const |
| TypeScript | Generic | Types, interfaces |
| Go | Generic fallthrough | Function extraction |
| Rust | Generic fallthrough | Function extraction |
| Java | Generic fallthrough | Classes, methods |

## Tooling Chunkers

Specialized chunkers for infrastructure-as-code:

| Chunker | File | Parses |
|--------|------|--------|
| `KubernetesChunker` | `k8s_chunker.py` | Deployment, Service, ConfigMap, Ingress |
| `HelmChartChunker` | `helm_chunker.py` | Chart.yaml, values.yaml templates |
| `DockerfileChunker` | `dockerfile_chunker.py` | FROM, RUN, COPY, ENTRYPOINT, CMD |
| `IstioChunker` | `istio_chunker.py` | VirtualService, DestinationRule, Gateway |
| `GraphQLChunker` | `graphql_chunker.py` | Types, Queries, Mutations, Subscriptions |

## Code Graph Retrieval (`retrieval/code_graph.py`)

### CodeGraphRetriever

MCP-compatible wrapper for CodeGraphContext with CLI fallback:

| Query Type | Method | Description |
|------------|--------|-------------|
| find_callers | `find_callers()` | Functions that call a given function |
| find_callees | `find_callees()` | Functions called by a given function |
| find_all_callers | `find_all_callers()` | Transitive callers (whole call graph) |
| find_all_callees | `find_all_callees()` | Transitive callees |
| class_hierarchy | `get_class_hierarchy()` | Parent classes |
| dead_code | `find_dead_code()` | Unused functions |
| complexity | `calculate_cyclomatic_complexity()` | Cyclomatic complexity |
| module_deps | `get_module_deps()` | Module dependencies |
| execute_cypher | `execute_cypher()` | Raw graph queries (read-only) |
| visualize | `visualize()` | Generate Mermaid from Cypher |

#### MCP + CLI Fallback

The retriever tries MCP imports first, falls back to `cgc` CLI:

```python
# Try MCP first
try:
    from CodeGraphContext_find_code import find_code
    CODEGRAPH_AVAILABLE = True
except ImportError:
    # CLI fallback
    CODEGRAPH_AVAILABLE = _check_cgc_available()
    # Uses: subprocess.run(["cgc", "find", "pattern", query])
```

**CLI Notes:**
- Table output goes to stderr, parse with combined streams
- Index: `cgc index .` to index codebase
- MCP unavailable when `codegraphcontext` package not installed

## MCP Tool Integration

### API Handler (`api/mcp.py`)

JSON-RPC 2.0 server with session management, rate limiting, and subscriptions:

| Method | Purpose |
|--------|---------|
| `initialize` | Returns protocol version, capabilities |
| `tools/list` | Lists all 33+ tools |
| `tools/call` | Executes a single tool |
| `tools/call/batch` | Batch execution |
| `resources/list` | Data resources |
| `resources/read` | Read resource |
| `prompts/list` | Prompt templates |
| `prompts/get` | Get prompt |
| `query` | Direct query execution |
| `notifications/listen` | Subscribe to topics |
| `notifications/unsubscribe` | Cancel subscription |
| `session/get` | Get session state |
| `session/set` | Set session state |

**Features:**
- Session management via `_sessions` dict
- Rate limiting: 100 calls/minute per client_id
- Sliding window algorithm

### CodeGraph Tools (`tools/base.py`)

| Tool | MCP Method |
|------|------------|
| `FindCallersTool` | `retriever.find_callers()` |
| `FindCalleesTool` | `retriever.find_callees()` |
| `FindDeadCodeTool` | `retriever.get_dead_code()` |
| `GetComplexityTool` | `retriever.get_complexity()` |
| `ClassHierarchyTool` | `retriever.get_class_hierarchy()` |
| `GetModuleDepsTool` | `retriever.get_module_deps()` |

## Live Code Indexing

### Watch Directory (`code_graph.py`)

```python
# Real-time code watching
graph.watch_directory(
    path="/path/to/code",
    extensions=[".py", ".js", ".ts"]
)
```

### Multi-Repository

Switch between codebases:

```python
graph.switch_context(path="/different/repo")
```

### Bundles

Load pre-indexed bundles:

```python
graph.load_bundle(bundle_name="flask")
graph.load_bundle(bundle_name="django")
```

## Configuration

| Env Variable | Default | Purpose |
|--------------|---------|---------|
| `USE_LLM_EXTRACTION` | false | Use LLM for entity extraction |
| `USE_STRUCTURAL_CHUNKING` | true | Use heading-aware chunking |
| `INCREMENTAL_INDEXING` | true | Skip unchanged documents |
| `CODEGRAPH_CONTEXT` | - | Directory to index |

## Edge Types in Graph Index

| Edge Type | Direction | Meaning |
|-----------|-----------|---------|
| `CALLS` | Function → Function | Function A calls Function B |
| `DEFINES` | File → Function | File defines Function A |
| `IMPORTS` | File → File | File A imports File B |
| `RETURNS` | Function → Type | Function returns Type A |
| `CONTAINS` | Class → Attribute | Class contains Attribute A |
| `INHERITS` | Class → Class | Class A inherits Class B |
| `IMPLEMENTS` | Class → Interface | Class implements Interface A |
| `DEPENDS_ON` | File → Dependency | File depends on Package A |
| `RELATED_TO` | Any → Any | General relationship |
| `DOCUMENTED_BY` | Any → Document | Element documented by Doc A |