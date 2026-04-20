# Architecture Documentation

Comprehensive technical documentation for the Engineering Intelligence System.

## Documentation Index

| Document | Description |
|----------|-------------|
| [01-ingestion-pipeline.md](01-ingestion-pipeline.md) | Data ingestion, parsers, chunkers, indexers, embeddings |
| [02-retrieval-pipeline.md](02-retrieval-pipeline.md) | Multi-source retrieval, hybrid strategies, fusion, reranking |
| [03-orchestration-agents.md](03-orchestration-agents.md) | Orchestration engine, agents, execution modes, memory |
| [04-code-understanding.md](04-code-understanding.md) | Entity extraction, relationships, code graph, MCP tools |
| [05-multimodal-diagrams.md](05-multimodal-diagrams.md) | VLM processing, diagram parsing, visual embeddings |
| [06-platform-adapters.md](06-platform-adapters.md) | Platform adapters, knowledge layer, cross-platform reasoning |

## Quick Reference

### Technology Stack

| Component | Technology |
|-----------|------------|
| API | FastAPI + Uvicorn |
| Vector DB | Qdrant |
| Graph DB | FalkorDB |
| Cache | Redis (optional) + in-memory LRU |
| LLM | OpenRouter, Qwen, GLM |
| Embeddings | OpenAI, Qwen, Ollama |
| Reranking | Cohere, BGE, SentenceTransformers |
| Testing | pytest + pytest-asyncio |

### Key Paths

```
/home/roger/src/gag/
├── api/                    # FastAPI endpoints
├── agents/                 # Planner, Retriever, Reasoner, Executor, Validator
├── core/
│   ├── adapters/          # Platform adapters (SAP, AWS, Azure, GCP, Tanzu)
│   ├── knowledge/         # Graph, ontology, taxonomy, constraints
│   ├── pipeline.py       # KnowledgeProcessingPipeline
│   └── memory.py         # Three-tier memory system
├── retrieval/             # 11 retrieval sources
├── ingestion/              # Pipeline, chunkers, indexers
├── documents/              # Parsing, diagrams
├── multimodal/             # VLM processing
└── tools/                  # 30+ MCP tools
```

### Commands

```bash
./eis api                    # Start API
./eis test                   # Run tests
./eis check                  # Lint + type check
docker-compose up -d         # Full stack
```

### Environment Variables

```bash
# Required
LLM_API_KEY=<key>
JWT_SECRET=<strong-random>
CREDENTIAL_ENCRYPT_KEY=<32-char>

# Optional
LLM_PROVIDER=openrouter
LLM_MODEL=qwen-max
EMBEDDER_PROVIDER=openai
```

## Version

Current version: **3.2.0**