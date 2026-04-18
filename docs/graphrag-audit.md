# GraphRAG Adoption Audit

## Executive Summary

**Status**: GraphRAG is **partially implemented but underutilized**.

The project has a well-designed GraphRAG pipeline in `ingestion/graphrag/` but it is **not integrated** into the main ingestion flow. The standard `IngestionPipeline` (in `ingestion/pipeline.py`) does not use GraphRAG's entity/relationship extraction, community detection, or knowledge graph building capabilities.

---

## Current GraphRAG Implementation

### Files (5)

| File | Purpose |
|------|---------|
| `ingestion/graphrag/pipeline.py` | Main pipeline orchestrator |
| `ingestion/graphrag/entity_extractor.py` | LLM-based entity extraction (10 entity types) |
| `ingestion/graphrag/relationship_inferrer.py` | Relationship inference (12 relationship types) |
| `ingestion/graphrag/community_detector.py` | Community detection via LLM |
| `ingestion/graphrag/__init__.py` | Exports with factory function |

### Capabilities Implemented

✅ **Entity Extraction** (10 types):
- PERSON, ORGANIZATION, CONCEPT, EVENT, LOCATION
- PRODUCT, TECHNOLOGY, DOCUMENT, PROCESS

✅ **Relationship Inference** (12 types):
- RELATED_TO, PART_OF, WORKS_FOR, LOCATED_AT
- USES, DEPENDS_ON, CREATED_BY, DEFINED_IN
- REFERENCES, CONTAINS, IMPLEMENTS, MANAGES

✅ **Community Detection**:
- LLM-based community extraction
- Hierarchical community structure

✅ **Dual Pipeline Support**:
- `GraphRAGPipeline` - standard
- `IncrementalGraphRAGPipeline` - for updates

---

## Integration Issues

### Problem 1: Not Connected to Main Ingestion

**Location**: `ingestion/pipeline.py` (lines 62-76)

The standard `IngestionPipeline` uses:
- `DocumentChunker` / `CodeChunker`
- `EmbeddingPipeline`
- `VectorIndexer` / `GraphIndexer`

It does **NOT** call `GraphRAGPipeline.process_document()`.

```python
# Current flow (ingestion/pipeline.py):
content → chunking → embedding → vector index + graph index

# Missing:
content → entity extraction → relationship inference → community detection → graph storage
```

### Problem 2: No API Exposure

**Location**: `ingestion/api.py`

The `/ingestion/ingest` endpoint only supports the basic pipeline:
- No parameter to enable GraphRAG processing
- No endpoint to trigger entity extraction
- No way to query extracted entities/relationships

### Problem 3: Retrieval Not GraphRAG-Aware

**Location**: `retrieval/graph.py`, `retrieval/hybrid.py`

- Graph retriever queries FalkorDB with Cypher
- Hybrid retriever can fetch entity context
- **But**: No integration with the GraphRAG extraction results
- Entity data goes nowhere after extraction

### Problem 4: Disconnected Components

```
┌─────────────────────────────────────────────────────┐
│  GraphRAG Pipeline (exists but unused)            │
│  - entity_extractor.py ✓                           │
│  - relationship_inferrer.py ✓                      │
│  - community_detector.py ✓                         │
└─────────────────────────────────────────────────────┘
              ↓ NOT CONNECTED ↓
┌─────────────────────────────────────────────────────┐
│  Main Ingestion Pipeline                            │
│  - chunker.py (basic) ✓                            │
│  - embedder.py ✓                                   │
│  - indexer.py ✓                                    │
└─────────────────────────────────────────────────────┘
              ↓ PARTIALLY CONNECTED ↓
┌─────────────────────────────────────────────────────┐
│  Retrieval (graph.py, hybrid.py)                    │
│  - FalkorDB queries ✓                               │
│  - Entity cache ✓                                   │
│  - BUT: no GraphRAG extracted data                  │
└─────────────────────────────────────────────────────┘
```

---

## Missing Integration Points

| Integration Point | Current State | Required Change |
|-------------------|---------------|------------------|
| API parameter | Doesn't exist | Add `use_graphrag: bool` to `IngestRequest` |
| Pipeline routing | Separate | Route to `GraphRAGPipeline` when enabled |
| Graph storage | FalkorDB exists | Write extracted entities/relationships to FalkorDB |
| Entity indexing | Disconnected | Use extracted entities in vector index with metadata |
| Retrieval enhancement | Limited | Match query against extracted entities first |

---

## Recommendations

### Priority 1: Enable in API

Add to `ingestion/api.py`:
```python
class IngestRequest(BaseModel):
    # ... existing fields
    use_graphrag: bool = False  # NEW
```

Route to appropriate pipeline based on flag.

### Priority 2: Connect to Graph Storage

Modify `GraphRAGPipeline.process_document()` to:
1. Write entities to FalkorDB with typed nodes
2. Write relationships as typed edges
3. Store community metadata as node properties

### Priority 3: Enable Entity-Aware Retrieval

In `retrieval/hybrid.py`:
1. Match query against extracted entities first
2. Expand to relationships for context
3. Use community structure for ranking

### Priority 4: Add GraphRAG Endpoints

In `ingestion/api.py`:
```python
@router.get("/entities/{source_id}")
async def get_entities(source_id: str): ...

@router.get("/relationships/{source_id}")
async def get_relationships(source_id: str): ...

@router.get("/communities/{source_id}")
async def get_communities(source_id: str): ...
```

---

## Conclusion

The GraphRAG implementation is **80% complete** in terms of extraction capability but **0% integrated** into the production flow. The entity extraction, relationship inference, and community detection are all implemented and functional, but:

1. **Not exposed via API**
2. **Not connected to main pipeline**
3. **Not used by retrieval**
4. **Data goes nowhere**

The project needs ~2-3 days of integration work to achieve full GraphRAG adoption.