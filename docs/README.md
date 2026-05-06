# Documentation

Comprehensive documentation for the Engineering Intelligence System.

## CLI Commands

```bash
./eis.py start                   # Start API server
./eis.py setup                  # Initialize configuration
./eis.py test                   # Run tests
./eis.py check                 # Lint + type check
```

## User Guides

| Guide | Description |
|-------|-------------|
| [Installation Guide](installation.md) | Local machine setup, Docker, Kubernetes |
| [Quick Start](README.md) | Get up and running in 5 minutes |

## Architecture

| Document | Description |
|---------|-------------|
| [Ingestion Pipeline](architecture/01-ingestion-pipeline.md) | Data collection, parsing, chunking, embedding |
| [Unified Ingestion](architecture/unified_ingestion.md) | Unified artifact ingestion, platform extensions |
| [Retrieval Pipeline](architecture/02-retrieval-pipeline.md) | Multi-source retrieval, hybrid strategies |
| [Orchestration Agents](architecture/03-orchestration-agents.md) | Planner, Retriever, Reasoner, Validator |
| [Code Understanding](architecture/04-code-understanding.md) | Code graph, entity extraction |
| [Diagrams & Multimodal](architecture/05-multimodal-diagrams.md) | VLM, diagram parsing, visual embeddings |
| [Platform Adapters](architecture/06-platform-adapters.md) | SAP, AWS, Azure, GCP, VMware, Power Platform |

## Developer Guides

| Guide | Description |
|-------|-------------|
| [MCP Tools](mcp-tools.md) | 30+ MCP tools reference |
| [Configuration](configuration.md) | Environment variables (119) |
| [Platform Adapter Architecture](platform-adapter-architecture.md) | Platform adapter patterns |
| [Platform Adapter Development Guide](architecture/platform-adapter-development.md) | Creating complete platform adapters |

## API Reference

| Document | Description |
|-------|-------------|
| [API Reference](api.md) | REST endpoints with examples |

## Version

Current version: **4.0.0**
