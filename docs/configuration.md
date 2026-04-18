# Configuration Reference

All settings are loaded from environment variables. The `Settings` class in `core/config.py` is the single source of truth.

## General

| Variable | Default | Description |
|---|---|---|
| `DEBUG` | `false` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

## API

| Variable | Default | Description |
|---|---|---|
| `API_HOST` | `0.0.0.0` | HTTP bind address |
| `API_PORT` | `8000` | HTTP port |
| `CORS_ORIGINS` | `*` | Comma-separated list of allowed origins |
| `MAX_WORKERS` | `4` | Max concurrent workers |
| `REQUEST_TIMEOUT` | `60` | Request timeout in seconds |

## Databases

| Variable | Default | Description |
|---|---|---|
| `QDRANT_HOST` | `localhost` | Qdrant vector DB host |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `FALKORDB_HOST` | `localhost` | FalkorDB graph DB host |
| `FALKORDB_PORT` | `7379` | FalkorDB port |
| `FALKORDB_USER` | | FalkorDB username |
| `FALKORDB_PASS` | | FalkorDB password |
| `REDIS_URL` | `redis://localhost:6379` | Redis URL |

## LLM

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `openrouter` | LLM provider: `openrouter`, `qwen`, `glm` |
| `LLM_MODEL` | `qwen-max` | Model name |
| `LLM_API_KEY` | | API key for the LLM provider |

## Embeddings

| Variable | Default | Description |
|---|---|---|
| `EMBEDDING_PROVIDER` | `openai` | Embedding provider: `openai`, `qwen`, `ollama`, `qdrant` |
| `OPENAI_API_KEY` | | OpenAI API key |
| `DASHSCOPE_API_KEY` | | Alibaba DashScope (Qwen) API key |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |

## VLM / Multimodal

| Variable | Default | Description |
|---|---|---|
| `VLM_PROVIDER` | | Vision model provider |
| `QWEN_API_KEY` | | Qwen API key for VLM |
| `ANTHROPIC_API_KEY` | | Anthropic API key |

## Reranking

| Variable | Default | Description |
|---|---|---|
| `RERANK_PROVIDER` | `cohere` | Rerank provider |
| `RERANK_STRATEGY` | `single` | Strategy: `single`, `cascade`, `ensemble` |
| `RERANK_TOP_K` | `10` | Number of results to rerank |
| `RERANK_MIN_SCORE` | `0.3` | Minimum score threshold |
| `COHERE_API_KEY` | | Cohere API key |
| `JINA_API_KEY` | | Jina API key |

## Chunking

| Variable | Default | Description |
|---|---|---|
| `CHUNKING_CHUNKER_TYPE` | `semantic` | Chunker type: `semantic`, `sentence`, `code`, `markdown`, `json` |
| `CHUNKING_SEMANTIC_CHUNK_THRESHOLD` | `0.5` | Similarity threshold for semantic chunking |
| `CHUNKING_SEMANTIC_EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | Embedding model for semantic chunking |
| `CHUNKING_SENTENCE_CHUNK_SIZE` | `1024` | Max tokens per sentence chunk |
| `CHUNKING_SENTENCE_CHUNK_OVERLAP` | `20` | Token overlap between sentence chunks |
| `CHUNKING_CODE_CHUNK_MAX_LINES` | `100` | Max lines per code chunk |
| `CHUNKING_CHUNK_MIN_LENGTH` | `50` | Min characters per chunk |
| `CHUNKING_CHUNK_MAX_LENGTH` | `2048` | Max characters per chunk |

## ColBERT

| Variable | Default | Description |
|---|---|---|
| `COLBERT_ENABLED` | `false` | Enable ColBERT late-interaction retrieval (opt-in) |
| `COLBERT_MODEL_NAME` | `colbert-ir/colbertv2.0` | ColBERT model |
| `COLBERT_MAX_LENGTH` | `512` | Max sequence length |
| `COLBERT_SIMILARITY_TOP_K` | `10` | Top-K results for ColBERT scoring |
| `COLBERT_RERANK_AFTER` | `true` | Apply reranking after ColBERT retrieval |

## Retrieval Strategy

| Variable | Default | Description |
|---|---|---|
| `RETRIEVAL_DEFAULT_STRATEGY` | `hybrid` | Default: `vector`, `graph`, `hybrid`, `cascade`, `iterative` |
| `RETRIEVAL_FUSION_METHOD` | `rrf` | Fusion: `rrf`, `score_normalized`, `weighted`, `combined` |
| `RETRIEVAL_PARALLEL_RETRIEVAL` | `true` | Enable parallel source retrieval |
| `RETRIEVAL_TIMEOUT_SECONDS` | `30` | Timeout for retrieval operations |
| `RETRIEVAL_FALLBACK_ON_EMPTY` | `true` | Fallback to secondary strategy on empty results |

## Citations

| Variable | Default | Description |
|---|---|---|
| `CITATION_STYLE` | `parenthetical` | Style: `parenthetical`, `verbatim`, `footnote`, `highlight`, `structured` |
| `CITATION_INCLUDE_SCORES` | `true` | Include relevance scores in citations |

## Auth / RBAC

| Variable | Default | Description |
|---|---|---|
| `JWT_SECRET` | `change-me-in-production` | **MUST be changed in production** |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_EXPIRY_MINUTES` | `60` | Token expiry |
| `RATE_LIMIT_REQUESTS` | `100` | Max requests per window |
| `RATE_LIMIT_WINDOW` | `60` | Rate limit window in seconds |

## Jira

| Variable | Default | Description |
|---|---|---|
| `JIRA_URL` | | Jira instance URL |
| `JIRA_EMAIL` | | Jira email |
| `JIRA_API_TOKEN` | | Jira API token |

## GitHub

| Variable | Default | Description |
|---|---|---|
| `GITHUB_OWNER` | | GitHub organization/user |
| `GITHUB_REPO` | | GitHub repository name |
| `GITHUB_TOKEN` | | GitHub personal access token |
| `GITLAB_TOKEN` | | GitLab personal access token |

## Azure DevOps

| Variable | Default | Description |
|---|---|---|
| `AZURE_DEVOPS_USERNAME` | | Azure DevOps username |
| `AZURE_DEVOPS_TOKEN` | | Azure DevOps PAT |

## Git Credentials

| Variable | Default | Description |
|---|---|---|
| `CREDENTIAL_ENCRYPT_KEY` | | **Required** for credential encryption |

## Confluence

| Variable | Default | Description |
|---|---|---|
| `CONFLUENCE_URL` | | Confluence instance URL |
| `CONFLUENCE_EMAIL` | | Confluence email |
| `CONFLUENCE_API_TOKEN` | | Confluence API token |

## WebDAV

| Variable | Default | Description |
|---|---|---|
| `WEBDAV_URL` | | WebDAV server URL |
| `WEBDAV_USER` | | WebDAV username |
| `WEBDAV_PASS` | | WebDAV password |

## Prometheus

| Variable | Default | Description |
|---|---|---|
| `PROMETHEUS_URL` | `http://localhost:9090` | Prometheus URL |
| `PROMETHEUS_USER` | | Prometheus username |
| `PROMETHEUS_PASSWORD` | | Prometheus password |

## Elasticsearch

| Variable | Default | Description |
|---|---|---|
| `ELASTIC_URL` | `http://localhost:9200` | Elasticsearch URL |
| `ELASTICSEARCH_URL` | `http://localhost:9200` | Elasticsearch URL (alias) |
| `ELASTIC_USER` | | Elasticsearch username |
| `ELASTIC_PASS` | | Elasticsearch password |
| `ELASTIC_API_KEY` | | Elasticsearch API key |

## Loki

| Variable | Default | Description |
|---|---|---|
| `LOKI_URL` | `http://localhost:3100` | Loki URL |
| `LOKI_TOKEN` | | Loki auth token |

## Knowledge Base

| Variable | Default | Description |
|---|---|---|
| `STACKOVERFLOW_API_KEY` | | StackOverflow API key |
| `REDDIT_CLIENT_ID` | | Reddit OAuth client ID |
| `REDDIT_CLIENT_SECRET` | | Reddit OAuth client secret |
| `FORUM_BASE_URL` | | Custom forum base URL |
| `FORUM_API_KEY` | | Custom forum API key |

## Requirements

| Variable | Default | Description |
|---|---|---|
| `REQUIREMENTS_PATH` | `requirements` | Local requirements directory |

## Backend Selectors

| Variable | Default | Description |
|---|---|---|
| `TICKET_BACKEND` | | Ticket backend selector |
| `TELEMETRY_BACKEND` | | Telemetry backend selector |
| `DOCS_BACKEND` | | Document backend selector |

## Observability

| Variable | Default | Description |
|---|---|---|
| `ENABLE_METRICS` | `true` | Enable metrics collection |
| `ENABLE_TRACING` | `false` | Enable request tracing |

## Entity-Aware Reasoning

| Variable | Default | Description |
|---|---|---|
| `ENTITY_AWARE_MAX_HOPS` | `3` | Max graph traversal hops |
| `ITERATIVE_MAX_ITERATIONS` | `3` | Max iterative retrieval iterations |
| `ITERATIVE_CONFIDENCE_THRESHOLD` | `0.7` | Confidence threshold to stop iterating |

## GraphRAG

| Variable | Default | Description |
|---|---|---|
| `GRAPH_RAG_ENABLED` | `false` | Enable GraphRAG processing |
| `GRAPH_RAG_USE_LLM` | `false` | Use LLM for entity/relationship extraction (vs regex) |
| `GRAPH_RAG_STRUCTURAL_CHUNKING` | `true` | Use structural chunking for documents |
| `GRAPH_RAG_INCREMENTAL` | `true` | Skip re-processing unchanged documents |
| `GRAPH_RAG_COMMUNITY_DETECTION` | `true` | Run community detection on entities |
| `GRAPH_RAG_MAX_ENTITIES` | `100` | Max entities extracted per document |
| `GRAPH_RAG_DEFAULT_HOPS` | `3` | Default graph traversal depth for queries |
| `GRAPH_RAG_ENTITY_TYPES` | `PERSON,ORGANIZATION,CONCEPT,EVENT,LOCATION,PRODUCT,TECHNOLOGY,DOCUMENT,PROCESS` | Enabled entity types |
| `GRAPH_RAG_RELATIONSHIP_TYPES` | `RELATED_TO,PART_OF,WORKS_FOR,LOCATED_AT,USES,DEPENDS_ON,CREATED_BY,DEFINED_IN,REFERENCES,CONTAINS,IMPLEMENTS,MANAGES` | Enabled relationship types |
