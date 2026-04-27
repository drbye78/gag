# Engineering Intelligence System - Agent Instructions

## Quick Commands

```bash
# CLI (preferred - no 'uv run' needed)
./eis api                    # Start API server
./eis test                   # Run all tests
./eis test --file test_core.py # Run specific test
./eis test --unit           # Run unit tests only
./eis test --keyword Health  # Tests matching keyword
./eis shell                 # Python shell
./eis install               # Install deps
./eis check                # Lint + typecheck

# Manual (using uv)
uv run pytest tests/ -v
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## Core Commands (verify first)

```bash
# Always run before committing
ruff check .
ruff format --check .
pyright .

# Install all deps
uv sync          # or: pip install -e ".[all]"
```

## Project Structure

```
/home/roger/src/gag/
├── api/              # FastAPI endpoints, MCP handler
├── agents/           # Planner, Retriever, Reasoner, Executor, Validator
├── core/            # Config, Auth, Cache, Health, Knowledge
│   ├── adapters/    # Platform adapters (SAP, AWS, Azure, GCP, Tanzu, PowerPlatform)
│   ├── knowledge/   # Graph, ontology, taxonomy, constraints, usecases, ADRs
│   ├── patterns/    # Platform patterns (12+)
│   └── constraints/  # Platform constraints
├── retrieval/        # Hybrid retriever (11 sources), reranking, citations
├── documents/       # Document parsing, chunking
├── ingestion/       # Ingestion pipelines
├── models/          # Pydantic models
├── multimodal/     # VLM processor
├── tools/           # Tool system (30+ MCP tools)
├── graph/           # FalkorDB client
├── llm/            # Multi-provider LLM router
├── ui/              # UI sketch retrieval
├── evaluation/      # Evaluation framework
├── git/             # Git repository ingestion
├── tests/          # 382 tests
└── docs/           # API, Architecture, Configuration
```

## Important Conventions

- **Testing**: `pytest-asyncio` with `asyncio_mode = auto` in pyproject.toml
- **Type Checking**: `pyright` (not mypy - configured in pyproject.toml)
- **Linting**: `ruff` (config in pyproject.toml)
- **Python**: 3.12+ required
- **LlamaIndex**: Use `llama_index.core.*` import paths (v0.14+)
- **Async tests**: Must have `asyncio_mode = auto` in pytest.ini

## Required Env Variables

```bash
# Development
LLM_PROVIDER=openrouter
LLM_MODEL=qwen-max
LLM_API_KEY=your-key

# Production (required)
JWT_SECRET=<strong-random-key>
CREDENTIAL_ENCRYPT_KEY=<32-char-key>
CORS_ORIGINS=https://your-domain.com
```

## Docker

```bash
docker-compose up -d  # Full stack: API + Qdrant + FalkorDB + Redis
# API: http://localhost:8000
```

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| `llama_index` import errors | Use `llama_index.core.*` paths |
| Async test failures | Add `asyncio_mode = auto` to pytest.ini |
| Missing deps | Run `uv pip sync` |
| Type errors with Docling | Check docling v2.x API (`DocumentConverter`) |

## Tool Categories (MCP)

- **Search**: Kubernetes, Helm, Docker, GraphQL, Istio
- **Reasoning**: Chain-of-thought, Tree-of-thoughts, Reflection
- **Code Analysis**: Find callers, callees, dead code, complexity
- **Graph**: FalkorDB integration
- **Multi-modal**: VLM for diagrams

## CodeGraphContext (retrieval/code_graph.py)

- MCP-first: tries `CodeGraphContext_*` imports
- CLI fallback: uses `cgc` CLI when MCP unavailable
- Output parsing: stderr contains table output
- Index: `cgc index .` to index codebase

## Documentation

- [README.md](README.md) - Project overview
- [docs/api.md](docs/api.md) - All 40+ API endpoints
- [docs/architecture/03-orchestration-agents.md](docs/architecture/03-orchestration-agents.md) - Agents
- [docs/architecture/06-platform-adapters.md](docs/architecture/06-platform-adapters.md) - Platform adapters
- [docs/configuration.md](docs/configuration.md) - 70+ config vars