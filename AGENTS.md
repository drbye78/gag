# Engineering Intelligence System - Agent Instructions

## Quick Commands

```bash
# CLI (preferred - no 'uv run' needed)
./eis.py api                    # Start API server
./eis.py test                   # Run all tests
./eis.py test --file test_core.py # Run specific test
./eis.py test --unit           # Run unit tests only
./eis.py test --keyword Health  # Tests matching keyword
./eis.py shell                 # Python shell
./eis.py install               # Install deps
./eis.py check                # Lint + typecheck
./eis.py eval                   # Run evaluation pipeline

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
/home/roger/src/gag5/
├── api/              # FastAPI endpoints, MCP handler
├── agents/           # Planner, Retriever, Reasoner, Executor, Validator
├── core/            # Config, Auth, Cache, Health, Knowledge
│   ├── adapters/    # Platform adapters (SAP, AWS, Azure, GCP, Tanzu, PowerPlatform)
│   ├── knowledge/   # Graph, ontology, taxonomy, constraints, usecases, ADRs
│   ├── patterns/    # Platform patterns (12+)
│   └── constraints/  # Platform constraints
├── unified_ingestion/ # Unified artifact ingestion (27 handlers, 40 artifact types)
├── retrieval/        # Hybrid retriever (11 sources), reranking, citations
├── documents/       # Document parsing, chunking
├── ingestion/       # Ingestion pipelines
├── models/          # Pydantic models
├── multimodal/     # VLM processor
├── tools/           # Tool system (69 MCP tools)
├── graph/           # FalkorDB client
├── llm/            # Multi-provider LLM router
├── ui/              # UI sketch retrieval
├── evaluation/      # Evaluation framework
│   └── results/     # Evaluation run reports
├── git/             # Git repository ingestion
├── tests/          # 713+ tests
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

69 MCP tools organized by PDLC phase:
- **Ideation** (4): idea_generate, brainstorm, technology_recommend, pattern_find
- **Requirements** (5): user_story_generate, acceptance_criteria_generate, requirements_validate, gap_analyze, requirements_import
- **Search & Retrieval** (10): search, hybrid_search, kubernetes_search, helm_search, dockerfile_search, graphql_search, istio_search, entity_search, ingest_source, get_job_status
- **Reasoning** (3): chain_reasoning, entity_reasoning, iterative_reasoning
- **Testing** (6): test_generate, test_execute, coverage_analyze, property_test, contract_test, mutation_test
- **Deployment** (6): cicd_pipeline_generate, deployment_generate, helm_chart_generate, terraform_generate, docker_compose_generate, deployment_validate
- **Observability** (7): metrics_collect, log_aggregate, alert_manager, dashboard_generate, tracing_collect, slo_track, anomaly_detect
- **Feedback** (5): feedback_ingest, sentiment_analyze, trend_analyze, feature_track, churn_predict
- **Day-2 Operations** (7): autoscale, update_orchestrate, incident_detect, root_cause_analyze, runbook_generate, backup_manage, capacity_plan
- **Code Analysis** (6): find_callers, find_callees, find_dead_code, get_complexity, class_hierarchy, get_module_deps
- **Graph** (1): query_graph
- **Infrastructure** (2): security_validate, cost_estimate
- **Multi-modal** (5): extract_from_image, analyze_visual, parse_document_advanced, colpal_search, ui_sketch_search

## CodeGraphContext (retrieval/code_graph.py)

- CLI-only: uses `cgc` CLI subprocess calls
- No MCP imports - direct CLI invocation via subprocess.run()
- Output parsing: JSON or table format from stdout/stderr
- Index: `cgc index .` to index codebase
- Availability check: `_is_cgc_available()` lazy initialization

## Documentation

- [README.md](README.md) - Project overview
- [docs/api.md](docs/api.md) - All 45+ API endpoints
- [docs/architecture/03-orchestration-agents.md](docs/architecture/03-orchestration-agents.md) - Agents
- [docs/architecture/06-platform-adapters.md](docs/architecture/06-platform-adapters.md) - Platform adapters
- [docs/configuration.md](docs/configuration.md) - 126 config vars