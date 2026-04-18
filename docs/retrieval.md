# Retrieval Strategy Guide

This guide explains the different retrieval strategies available in the Engineering Intelligence System and when to use them.

## Overview

The system supports multiple retrieval strategies that can be configured via environment variables:

| Strategy | Config Value | Best For |
|---|---|---|
| Vector-only | `vector` | Simple keyword/semantic search |
| Graph-only | `graph` | Relationship-heavy queries |
| Hybrid (default) | `hybrid` | Best overall relevance |
| Cascade | `cascade` | Multi-stage refinement |
| Iterative | `iterative` | Complex multi-step queries |

## Hybrid Retrieval (Default)

The hybrid strategy combines results from multiple sources:

- **Vector search** (docs, code)
- **Graph traversal** (entity relationships)
- **ColBERT** (when enabled)

Results are fused using Reciprocal Rank Fusion (RRF) by default.

### Configuration

```bash
RETRIEVAL_DEFAULT_STRATEGY=hybrid
RETRIEVAL_FUSION_METHOD=rrf  # rrf, score_normalized, weighted, combined
RETRIEVAL_PARALLEL_RETRIEVAL=true
```

### Fusion Methods

| Method | Description |
|---|---|
| `rrf` | Reciprocal Rank Fusion - rank-based |
| `score_normalized` | Min-max normalized score fusion |
| `weighted` | Weighted average with configurable weights |
| `combined` | Score + rank combined |

## ColBERT Late Interaction

ColBERT provides late-interaction scoring where query tokens are matched against document tokens independently, then max-pooled. This often outperforms standard sentence-level embeddings.

### Enable ColBERT

```bash
COLBERT_ENABLED=true
COLBERT_MODEL_NAME=colbert-ir/colbertv2.0
COLBERT_MAX_LENGTH=512
COLBERT_SIMILARITY_TOP_K=10
COLBERT_RERANK_AFTER=true
```

### ColBERT vs ColPali

- **ColBERT**: Late-interaction on text. Best for text-heavy corpora.
- **ColPali**: Visual late-interaction on document images. Best for PDF/image-heavy corpora.

## Chunking Strategies

The system supports multiple chunkers for different content types:

| Chunker | Type | Best For |
|---|---|---|
| `semantic` | Similarity-based | General text with clear semantic boundaries |
| `sentence` | Token-based | Precise control over chunk size |
| `code` | AST-based | Programming language files |
| `markdown` | Structure-aware | Markdown with headers/lists |
| `json` | Structure-aware | JSON data |

### Configuration

```bash
CHUNKING_CHUNKER_TYPE=semantic

# Semantic chunker options
CHUNKING_SEMANTIC_CHUNK_THRESHOLD=0.5
CHUNKING_SEMANTIC_EMBED_MODEL=BAAI/bge-small-en-v1.5

# Sentence chunker options
CHUNKING_SENTENCE_CHUNK_SIZE=1024
CHUNKING_SENTENCE_CHUNK_OVERLAP=20

# Code chunker options
CHUNKING_CODE_CHUNK_MAX_LINES=100

# General limits
CHUNKING_CHUNK_MIN_LENGTH=50
CHUNKING_CHUNK_MAX_LENGTH=2048
```

## Auto-Detection

The system auto-selects chunker based on file extension:

| Extension | Chunker |
|---|---|
| `.py`, `.js`, `.ts`, `.go`, `.java`, `.rs` | `code` |
| `.md`, `.markdown` | `markdown` |
| `.json` | `json` |
| Everything else | `semantic` (default) |

## Using via API

### Basic Retrieval

```bash
curl -X POST http://localhost:8000/hybrid/search \
  -H "Content-Type: application/json" \
  -d '{"query": "how does auth work?", "limit": 10}'
```

### Specify Strategy

```bash
curl -X POST http://localhost:8000/hybrid/search \
  -H "Content-Type: application/json" \
  -d '{"query": "find related functions", "strategy": "iterative", "limit": 10}'
```

### Via Orchestrator

```bash
curl -X POST http://localhost:8000/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "auth middleware",
    "sources": ["docs", "code", "colbert"],
    "limit": 10
  }'
```

## Performance Tuning

| Setting | Recommendation |
|---|---|
| `RETRIEVAL_TIMEOUT_SECONDS` | Increase for complex queries |
| `RETRIEVAL_PARALLEL_RETRIEVAL` | Keep true for latency |
| `COLBERT_RERANK_AFTER` | Keep true for better relevance |