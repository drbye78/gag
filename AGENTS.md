# Engineering Intelligence System - Agent Instructions

## Quick Commands

```bash
# CLI (preferred - no 'uv run' needed)
./eis api                    # Start API server
./eis test                   # Run all tests
./eis test --file test_core.py # Run specific test
./eis test --unit           # Run unit tests only
./eis test --keyword Health  # Run tests matching keyword
./eis shell                 # Start Python shell
./eis install               # Install dependencies
./eis check                # Run linting & type checking

# Manual (using uv)
uv run pytest tests/
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000
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
├── tools/           # Tool system (10+ modules: ideation, day2, requirements, testing, etc.)
├── graph/           # FalkorDB client
├── llm/            # Multi-provider LLM router
├── ui/              # UI sketch retrieval
├── evaluation/      # Evaluation framework
├── git/             # Git repository ingestion
├── tests/          # 382 tests
└── docs/           # API, Architecture, Configuration
```

## Key Entry Points

- **API**: `api/main.py` - FastAPI app with routes
- **Orchestration**: `agents/orchestration.py` - Plan → Retrieve → Reason → Execute
- **Platform Adapters**: `core/adapters/` - SAP, AWS, Azure, GCP, Tanzu, PowerPlatform
- **Knowledge**: `core/knowledge/` - Graph, patterns, constraints

## Platform-Adapters Architecture

Six pluggable adapters in `core/adapters/`:
- **SAP BTP**: XSUAA, HANA, Kyma
- **AWS**: Lambda, S3, DynamoDB, EKS
- **Azure**: Functions, Cosmos DB, AKS
- **GCP**: Cloud Functions, Firestore, GKE
- **VMware Tanzu**: Kubernetes, Spring
- **Power Platform**: PowerApps, Dataverse

Knowledge layer with:
- Use cases (7 pre-built)
- ADRs (5 architecture decisions)
- Reference architectures (8 patterns)

## Important Conventions

1. **Testing**: `pytest-asyncio` with `asyncio_mode = auto` in pyproject.toml
2. **Type Checking**: `mypy` with config in pyproject.toml
3. **Linting**: `ruff` with config in pyproject.toml
4. **Dependencies**: `uv sync` or `pip install -e ".[all]"`
5. **Python**: 3.12+ required
6. **LlamaIndex**: Use `llama_index.core.*` paths (v0.14+)

## Required Env Variables

```bash
# Development
LLM_PROVIDER=openrouter
LLM_MODEL=qwen-max
LLM_API_KEY=your-key

# Production (required)
JWT_SECRET=<strong-random-key>
CREDENTIAL_ENCRYPT_KEY=<32-char-key>
```

## Docker

```bash
docker-compose up -d  # Start full stack (API + Qdrant + FalkorDB + Redis)
# API: http://localhost:8000
```

## Common Issues

1. **llama_index import errors**: Use `llama_index.core.*` paths
2. **Async test failures**: Ensure `asyncio_mode = auto` in pytest.ini
3. **Missing deps**: Run `uv pip sync`

## Documentation

- [README.md](README.md) - Project overview
- [docs/architecture/README.md](docs/architecture/README.md) - Architecture documentation index
- [docs/architecture/01-ingestion-pipeline.md](docs/architecture/01-ingestion-pipeline.md) - Ingestion pipeline
- [docs/architecture/02-retrieval-pipeline.md](docs/architecture/02-retrieval-pipeline.md) - Retrieval pipeline
- [docs/architecture/03-orchestration-agents.md](docs/architecture/03-orchestration-agents.md) - Orchestration & agents
- [docs/architecture/04-code-understanding.md](docs/architecture/04-code-understanding.md) - Code understanding
- [docs/architecture/05-multimodal-diagrams.md](docs/architecture/05-multimodal-diagrams.md) - Multimodal & diagrams
- [docs/architecture/06-platform-adapters.md](docs/architecture/06-platform-adapters.md) - Platform adapters
- [docs/api.md](docs/api.md) - API endpoints
- [docs/configuration.md](docs/configuration.md) - 70+ config vars