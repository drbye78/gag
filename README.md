# Engineering Intelligence System

A production-grade **Cognitive Architecture** for domain-specific reasoning within enterprise AI PDLC pipelines. Goes beyond traditional RAG by combining multimodal understanding, hybrid retrieval (vector + graph + runtime), structured reasoning, tool-augmented decision making, and stateful orchestration.

![Version](https://img.shields.io/badge/version-3.0.0-blue)
![Python](https://img.shields.io/badge/python-3.12+-green)
![Tests](https://img.shields.io/badge/tests-311%20passing-brightgreen)
![License](https://img.shields.io/badge/license-Proprietary-red)

---

## What It Does

This system answers complex engineering questions by reasoning over your codebase, documentation, architecture diagrams, support tickets, and telemetry data — all at once. It doesn't just search; it **plans, retrieves from multiple sources, reasons with a knowledge graph, and validates its own answers**.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Interface Layer                       │
│  REST API  │  MCP (JSON-RPC 2.0)  │  Multimodal (VLM)  │
├─────────────────────────────────────────────────────────┤
│                   Orchestration Layer                     │
│  Plan → Retrieve → Reason → Execute  │  Retry & Metrics │
├─────────────────────────────────────────────────────────┤
│                    Cognitive Layer                       │
│  Planner │ Retrieval Agent │ Reasoning Agent │ Validator│
├─────────────────────────────────────────────────────────┤
│                    Knowledge Layer                       │
│  Hybrid Retriever │ Entity Graph Cache │ Fusion │ Rerank│
├─────────────────────────────────────────────────────────┤
│                   Data Processing Layer                  │
│  Ingestion │ Chunking │ Embedding │ Vector │ Graph │ IR │
└─────────────────────────────────────────────────────────┘
        │ Qdrant │  │ FalkorDB │  │ Redis │  │ LLM Router │
```

---

## Key Features

### 🔍 Hybrid Retrieval
- **5 strategies**: Vector-only, Graph-only, Multi-hop, Cascade, Iterative
- **Entity graph cache**: LRU eviction (500 entries, 1h TTL) with REST API for monitoring
- **4 fusion methods**: RRF, Score-normalized, Weighted, Combined
- **5 rerank providers**: Cohere, BGE, SentenceTransformers, Jina, LlamaIndex
- **5 citation styles**: Parenthetical, Verbatim, Footnote, Highlight, Structured

### 🧠 Cognitive Agents
- **Planner** — Detects intent (design/explain/troubleshoot/optimize), decomposes tasks, assigns tools
- **Retriever** — Parallel, sequential, cascade, and adaptive retrieval with in-memory caching
- **Reasoner** — Direct, chain-of-thought, tree-of-thoughts, reflection, and critique modes
- **Validator** — Checks accuracy, coherence, completeness, and safety of responses

### ⚙️ Orchestration Engine
- State-driven loop: `Plan → Retrieve → Reason → Execute`
- **5 execution modes**: Iterative, Parallel, Sequential, Branching, Recursive
- Retry logic with exponential backoff
- Streaming execution with step-by-step progress yields

### 🖼️ Multimodal & Diagrams
- Vision Language Model (VLM) processor for architecture diagrams
- Supports Qwen Vision and OpenAI vision providers
- IR (Intermediate Representation) builder with entity/relation extraction
- **Diagram Formats**: UML (Class, Sequence, Component, Activity, State), C4, BPMN 2.0, PlantUML, Draw.io, OpenAPI

### 🌐 Multilingual
- Language detection (Russian, English, and 20+ languages)
- Russian text normalization (Cyrillic, ё→е equivalence)
- Language-aware chunking and sentence splitting
- Multilingual reranking with `rerank-multilingual-v3.0`

### 📥 Ingestion Pipeline
- **7 source types**: Git repositories, Documents, Tickets, Telemetry, Knowledge Base, Architecture, Requirements
- Full pipeline: Collect → Normalize → Parse → Chunk → Enrich → Embed → Index
- Code chunking with entity extraction (Python, JS/TS, Go, Rust, Java)
- Structural and hierarchical chunking for markdown

### 🔧 Tool System (MCP)
- **13 tools** exposed via Model Context Protocol: architecture evaluation, security validation, cost estimation, search, hybrid search, reranking, chain/entity/iterative reasoning, graph queries, entity search, ingestion, job status

---

## Quick Start

### Prerequisites
- Python 3.12+
- Docker & Docker Compose

### Run with Docker Compose

```bash
# Set required environment variables
export LLM_PROVIDER=openrouter
export LLM_MODEL=qwen-max
export LLM_API_KEY=your-key-here

# Start the full stack (API + Qdrant + FalkorDB + Redis)
docker-compose up -d
```

The API is available at `http://localhost:8000`.

### Manual Setup

```bash
# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run with uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Service info |
| `/health` | GET | Health check with dependency status |
| `/query` | POST | Main query endpoint (orchestration engine) |
| `/mcp` | POST/GET | MCP JSON-RPC 2.0 handler |
| `/multimodal/extract` | POST | Extract text from images via VLM |
| `/reasoning/chain` | POST | Chain-of-thoughts reasoning |
| `/reasoning/entity` | POST | Entity-aware reasoning with graph traversal |
| `/rerank` | POST | ML-based reranking |
| `/citations` | POST | Citation generation |
| `/hybrid/enhanced` | POST | Enhanced hybrid search with entity cache |
| `/entity/cache/stats` | GET | Entity cache statistics |
| `/entity/cache/invalidate` | POST | Invalidate entity cache |
| `/ingestion/ingest` | POST | Ingest a single document |
| `/ingestion/batch` | POST | Batch ingest documents |
| `/ingestion/codebase` | POST | Ingest a codebase |
| `/ingestion/jobs` | GET | List ingestion jobs |

Full API reference: [docs/api.md](docs/api.md)

---

## Configuration

All settings are loaded from environment variables. See [docs/configuration.md](docs/configuration.md) for the complete reference (70+ variables).

**Required for production:**

```bash
export JWT_SECRET=<strong-random-key>          # MUST change from default
export CREDENTIAL_ENCRYPT_KEY=<32-char-key>     # Required for credential encryption
export CORS_ORIGINS=https://your-domain.com     # Don't use wildcard in production
export LLM_API_KEY=your-api-key
```

---

## Project Structure

```
├── agents/             # Planner, Retriever, Reasoning, Executor, Validator
├── api/                # FastAPI REST endpoints and MCP handler
├── core/               # Config, auth/RBAC, caching, memory, health, metrics
├── documents/          # Document ingestion with versioning, Confluence, WebDAV
├── evaluation/         # Evaluation test cases and scoring
├── git/                # Git repository ingestion pipeline
├── graph/              # FalkorDB graph database client
├── ingestion/          # Data ingestion: chunking, embedding, indexing
├── llm/                # Multi-provider LLM router (OpenRouter, Qwen, GLM)
├── models/             # Pydantic data models (IR, graph, retrieval, MCP)
├── multimodal/         # VLM processor and IR builder
├── retrieval/          # Hybrid retrieval, reranking, citations, fusion
├── tools/              # Tool registry (13 tools via MCP)
├── docs/               # Architecture, API, deployment, configuration docs
└── tests/              # 182 unit and integration tests
```

---

## Tech Stack

| Component | Technology |
|---|---|
| **API** | FastAPI + Uvicorn |
| **Vector DB** | Qdrant |
| **Graph DB** | FalkorDB |
| **Cache** | Redis (optional) + in-memory TTL |
| **LLM** | OpenRouter, Qwen (DashScope), GLM |
| **Embeddings** | OpenAI, Qwen, Ollama |
| **Reranking** | Cohere, BGE, SentenceTransformers, Jina, LlamaIndex |
| **Document Parsing** | Docling, python-docx, openpyxl, python-pptx, PyMuPDF |
| **Testing** | pytest + pytest-asyncio |

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_core.py -v          # Core infrastructure
python -m pytest tests/test_agents.py -v        # Agent system
python -m pytest tests/test_ingestion.py -v     # Ingestion pipeline
python -m pytest tests/test_retrieval.py -v     # Retrieval layer
python -m pytest tests/test_new_features.py -v  # Entity cache, LLM router, config
```

**182 tests, all passing.**

---

## Documentation

- [API Reference](docs/api.md) — All 40+ endpoints with examples
- [Architecture](docs/architecture.md) — System design and layers
- [Deployment](docs/deployment.md) — Docker, Kubernetes, production setup
- [Configuration](docs/configuration.md) — Complete env var reference
- [Entity Cache](docs/entity-cache.md) — Cache architecture and monitoring
- [Agents](docs/agents.md) — Agent system details

---

## Version History

| Version | Highlights |
|---|---|
| **v2.4** | Entity graph cache, lazy retriever init, config consolidation, input validation, Cypher injection prevention, logging, CORS config, embedding cache |
| **v2.3** | Unit tests, new API endpoints, configuration settings, pipeline integration |
| **v2.2** | GraphRAG, cross-reference extraction, structural chunking, entity-centric retrieval |
| **v2.1** | Code graph context, reranking subsystem (5 providers, 3 strategies), citations (5 styles) |
| **v2.0** | Memory system, cascading/iterative retrieval, validator agent, RBAC, branching/recursive execution |

---

## License

Proprietary — All rights reserved.
