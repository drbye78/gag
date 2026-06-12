# Installation Guide

Comprehensive installation instructions for various scenarios.

## Prerequisites

| Requirement | Version | Notes |
|--------------|----------|-------|
| Python | 3.12+ | Mandatory |
| Docker | 20.10+ | For container部署 |
| Docker Compose | 2.0+ | For full stack |
| uv | Latest | Recommended package manager |

## Installation Scenarios

### 1. Local Development (Minimal)

```bash
# Clone repository
git clone https://github.com/drbye78/gag.git
cd gag

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install core only (FastAPI + basic deps)
pip install -e .

# Start API server
uvicorn api.main:app --host 0.0.0.0 --port 8000
# Or use CLI
./eis api
```

### 2. Local Development (Full)

```bash
# Clone and setup
git clone https://github.com/drbye78/gag.git
cd gag
python -m venv .venv
source .venv/bin/activate

# Install all dependencies
pip install -e ".[all]"

# Install development tools
pip install -e ".[dev]"

# Verify installation
./eis check
```

### 3. Docker (Recommended)

```bash
# Full stack with external services
docker-compose up -d

# Check status
docker-compose ps

# View API logs
docker-compose logs -f api

# Access API
curl http://localhost:8000/health
```

### 4. Kubernetes

```bash
# Deploy to cluster
kubectl apply -f k8s/

# Or use Helm
helm install gag ./helm/gag
```

## Dependency Groups

| Group | Packages | Use Case |
|-------|----------|----------|
| (core) | fastapi, uvicorn, pydantic | API only |
| `qdrant` | qdrant-client | Vector search |
| `docs` | python-docx, docling, pdfplumber | Document parsing |
| `embeddings` | sentence-transformers | ML embeddings |
| `cache` | redis | Caching layer |
| `vision` | torch, torchvision | Visual processing |
| `multilingual` | langdetect | Language detection |
| `colbert` | fastembed | Late interaction |
| `otel` | opentelemetry-* | Observability |

### Example Installations

```bash
# Just vector search
pip install -e ".[qdrant]"

# Document-heavy workflow
pip install -e ".[docs,embeddings]"

# Full ML capabilities
pip install -e ".[embeddings,vision,colbert]"

# Production monitoring
pip install -e ".[otel,cache]"
```

## Environment Variables

### Required

```bash
# LLM Configuration
export LLM_PROVIDER=openrouter
export LLM_MODEL=qwen-max
export LLM_API_KEY=your-api-key

# Production Security (change these!)
export JWT_SECRET=<strong-random-secret>
export CREDENTIAL_ENCRYPT_KEY=<32-character-key>
export CORS_ORIGINS=https://your-domain.com
```

### Optional

```bash
# Database Services ( defaults work for Docker)
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
export FALKORDB_HOST=localhost
export FALKORDB_PORT=6378

# Feature Flags
export COLBERT_ENABLED=false
export ENTITY_CACHE_ENABLED=true
export ENABLE_TRACING=true
```

## Verification

### Check Installation

```bash
# Verify Python version
python --version  # Should be 3.12+

# Verify dependencies
./eis check

# Run tests
./eis test --unit
```

### Health Check

```bash
# API health endpoint
curl http://localhost:8000/health

# Full diagnostic
curl http://localhost:8000/health?detailed=true
```

## External Services

### Required for Full Features

| Service | Default Port | Docker Service |
|---------|-------------|----------------|
| Qdrant | 6333 | qdrant |
| FalkorDB | 6378 | falkordb |
| Redis | 6379 | redis |

### Optional External Services

| Service | Purpose | Env Variable |
|---------|---------|--------------|
| Jira | Ticket source | JIRA_URL, JIRA_API_KEY |
| GitHub | Issue source | GITHUB_TOKEN |
| Azure AI | Vision | AZURE_VISION_ENDPOINT |
| OpenAI | Embeddings | OPENAI_API_KEY |

## Troubleshooting

### Import Errors

```bash
# Fix llama_index import errors
pip install llama-index>=0.14.0

# Use correct import paths
from llama_index.core import SimpleDirectoryReader  # NOT llama_index
```

### Async Test Failures

```bash
# Ensure asyncio_mode = auto in pytest.ini
# Or run with explicit flag
pytest tests/ -v -p no:asyncio_mode
```

### Dependency Issues

```bash
# Clean install
pip uninstall -y gag
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"

# Or use uv
uv sync
```

### Docker Issues

```bash
# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Check logs
docker-compose logs -f
docker-compose logs -f qdrant
docker-compose logs -f falkordb
```