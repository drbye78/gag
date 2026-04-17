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
├── api/           # FastAPI endpoints
├── agents/        # Planner, Retriever, Reasoner, Validator agents
├── core/          # Config, Auth, Memory, Cache, Health
├── retrieval/     # Hybrid retriever (vector + graph + runtime)
├── documents/     # Document parsing, chunking, multimodal
├── ingestion/     # Ingestion pipelines (Git, Docs, Tickets, etc.)
├── models/        # Pydantic models (IR, MCP, Graph, Retrieval)
├── multimodal/    # VLM processor, IR builder
├── tests/         # 311 tests, run with pytest-asyncio
└── docs/          # API, Architecture, Configuration docs
```

## Key Entry Points

- **API**: `api/main.py` - FastAPI app with routes
- **Orchestration**: `agents/orchestration.py` - Plan → Retrieve → Reason → Execute
- **Config**: `core/config.py` - Settings from environment variables
- **Auth**: `core/auth.py` - RBAC, JWT tokens, password hashing

## Important Conventions

1. **Testing**: Use `pytest-asyncio` with `asyncio_mode = auto` in pytest.ini
2. **Type Checking**: Run `mypy` with config in `pyproject.toml` (ignore_missing_imports=true)
3. **Linting**: Use `ruff` with config in `pyproject.toml`
4. **Dependencies**: Install with `uv pip install -r requirements.txt` or `uv sync`
5. **Virtual Environment**: Use `.venv` directory, activate with `source .venv/bin/activate`

## LlamaIndex Version Note

This project uses **llama-index v0.14+**. Import paths changed:
- `llama_index.readers.file` → `llama_index.core.SimpleDirectoryReader`
- `llama_index.core.node_parser.SemanticChunker` → `llama_index.core.node_parser.SemanticSplitterNodeParser`
- `llama_index.core.TextNode` → `llama_index.core.schema.TextNode`

## Required Environment Variables

```bash
# For local development
LLM_PROVIDER=openrouter
LLM_MODEL=qwen-max
LLM_API_KEY=your-key

# Required for production
JWT_SECRET=<strong-random-key>
CREDENTIAL_ENCRYPT_KEY=<32-char-key>
```

## Docker Services

```bash
# Start full stack (API + Qdrant + FalkorDB + Redis)
docker-compose up -d

# Access API at http://localhost:8000
```

## Common Issues

1. **Import errors with llama_index**: Use `llama_index.core.*` paths, not old `llama_index.readers.*`
2. **Async test failures**: Ensure pytest-asyncio is installed and `asyncio_mode = auto` in pytest.ini
3. **Missing dependencies**: Run `uv pip sync` or `pip install -r requirements.txt`

## Documentation

- [README.md](README.md) - Project overview
- [docs/api.md](docs/api.md) - API endpoints
- [docs/configuration.md](docs/configuration.md) - 70+ config variables
- [docs/architecture.md](docs/architecture.md) - System design