# Local Development (No Docker)

This guide covers running the project directly on the host without Docker.

## Prerequisites

- Python 3.12+ (via pyenv, uv, or system)
- Redis (optional, for caching)
- Qdrant (optional, for vector search)
- FalkorDB (optional, for graph)

## Quick Start

### 1. Setup Python with uv

```bash
# Using uv (recommended - handles Python version)
UV_PYTHON=3.12 uv sync

# Install core dependencies + extras you need
UV_PYTHON=3.12 uv sync -E qdrant -E docs -E embeddings -E cache
```

### 2. Install Extras

Choose the extras you need:

```bash
# Core (API works, limited features)
uv sync

# With vector DB (Qdrant)
uv sync -E qdrant

# With documents parsing
uv sync -E docs

# With embeddings + reranking
uv sync -E embeddings

# With Redis caching
uv sync -E cache

# Full stack (all features)
uv sync -E all
```

### 2. Start Optional Infrastructure

```bash
# Start Redis (cache)
docker run --rm -p 6379:6379 redis:7.4-alpine

# Start Qdrant (vector DB)
docker run --rm -p 6333:6333 qdrant/qdrant:v1.7.4

# Start FalkorDB (graph DB)
docker run --rm -p 6379:6379 falkordb/falkordb:v4.18.0

# Or start all three
docker compose up -d qdrant falkordb redis
```

### 3. Run the API

```bash
# Set required environment variables
export LLM_API_KEY=your-openrouter-key
export JWT_SECRET=$(openssl rand -hex 32)
export CREDENTIAL_ENCRYPT_KEY=$(openssl rand -hex 32)

# Optional: use local services
export QDRANT_HOST=localhost
export FALKORDB_HOST=localhost
export REDIS_URL=redis://localhost:6379

# Run with uvicorn
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 4. Verify

```bash
curl http://localhost:8000/health
curl http://localhost:8000/
```

## Using the CLI

```bash
./eis.py api                    # Start API
./eis.py test                   # Run tests
./eis.py check                 # Lint + type check
```

## Required Environment Variables

| Variable | Description | Default |
|----------|--------------|---------|
| `JWT_SECRET` | Secret for JWT tokens (REQUIRED) | - |
| `CREDENTIAL_ENCRYPT_KEY` | Key for encrypting secrets (REQUIRED) | - |
| `LLM_API_KEY` | LLM provider API key (REQUIRED) | - |
| `LLM_PROVIDER` | LLM provider | `openrouter` |
| `LLM_MODEL` | Model name | `qwen-max` |

## Optional: Use All External Services

```bash
# Point to external services
export QDRANT_HOST=qdrant.example.com
export FALKORDB_HOST=falkordb.example.com
export REDIS_URL=redis://redis.example.com:6379
export CORS_ORIGINS=https://your-domain.com

uv run uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## Running Without qdrant/falkordb/redis

The API still works with in-memory fallbacks for most features. You'll need `llama_index` for document ingestion:

```bash
# Minimum for API to start
UV_PYTHON=3.12 uv sync -E docs

# Run with in-memory fallbacks
export JWT_SECRET=$(openssl rand -hex 32)
export CREDENTIAL_ENCRYPT_KEY=$(openssl rand -hex 32)
export LLM_API_KEY=your-key

uv run uvicorn api.main:app
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `JWT_SECRET is using the default` | Set `JWT_SECRET` env var |
| `CREDENTIAL_ENCRYPT_KEY required` | Set `CREDENTIAL_ENCRYPT_KEY` env var |
| `Python 3.12+ required` | `UV_PYTHON=3.12 uv sync` |
| `No module named 'llama_index'` | `uv sync -E docs` or `-E all` |
| Connection refused | Start local/remote service |