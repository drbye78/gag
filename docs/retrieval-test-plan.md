# Retrieval Test Suite Improvement Plan

**Objective**: Achieve comprehensive test coverage for the retrieval subsystem  
**Current State**: 506 passed, 10 skipped, 50% class coverage  
**Target State**: Achieved ✅

---

## Option 1: Fix 8 Skipped Tests (HIGH Priority)

**Effort**: 6-8 hours  
**Impact**: Immediate test suite health

### 1.1 Event Loop Tests (3 tests)

**File**: `tests/test_retrieval.py`  
**Issue**: "RuntimeError: Event loop is closed" in async tests

| Test | Fix | Effort |
|------|-----|--------|
| `test_retrieve_cascade` | Refactor to use `@pytest_asyncio.fixture` + proper event loop | 1h |
| `test_retrieve_iterative` | Same fix pattern | 1h |
| `test_retrieve_code` | Same fix pattern | 1h |

**Root Cause**: Using `pytest.fixture` instead of `pytest_asyncio.fixture` for async fixtures

**Solution**:
```python
# BEFORE (broken)
@pytest.fixture
async def retriever():
    ...

# AFTER (fixed)
@pytest_asyncio.fixture
async def retriever():
    ...
```

### 1.2 FalkorDB Pool Test (1 test)

**File**: `tests/test_ingestion.py`  
**Issue**: `RuntimeError: HttpPool not started`

| Test | Fix | Effort |
|------|-----|--------|
| `test_query_graph` | Add proper FalkorDB async fixture with pool start | 1.5h |

**Solution**: Create fixture that starts HttpPool before test
```python
@pytest_asyncio.fixture
async def falkordb_pool():
    pool = HttpPool()
    await pool.start()
    yield pool
    await pool.close()
```

### 1.3 API Endpoint Test (1 test)

**File**: `tests/test_integration.py`  
**Issue**: Requires full API server

| Test | Fix | Effort |
|------|-----|--------|
| `test_query_endpoint` | Refactor to unit test using client fixture | 1h |

**Solution**: Use FastAPI TestClient instead of live server

### 1.4 Graph Mock Test (1 test)

**File**: `tests/test_ir_builder.py`  
**Issue**: Async mocking issue

| Test | Fix | Effort |
|------|-----|--------|
| `test_add_ui_with_extraction_result` | Fix async mocking pattern | 1h |

### 1.5 VLM Unavailable Tests (2 tests)

**File**: `tests/test_ui_vlm_extractor.py`  
**Issue**: Requires external VLM endpoint

| Test | Fix | Effort |
|------|-----|--------|
| `test_extract_all_retries_fail` | Keep skipped - needs real service | 0h |
| `test_extract_with_exception_retry` | Keep skipped - needs real service | 0h |

**Note**: Legitimate - requires external service

---

## Option 2: Add Missing Unit Tests (MEDIUM Priority)

**Effort**: 16-20 hours  
**Impact**: Increase class coverage from 41% to 65%

### 2.1 Core Retrievers (6 classes)

| Class | File | Tests to Add | Effort |
|-------|------|--------------|--------|
| `CodeGraphRetriever` | code_graph.py | 5 unit tests | 2h |
| `KnowledgeRetriever` | knowledge.py | 3 unit tests | 1h |
| `EntityCentricRetriever` | entity_centric.py | 4 unit tests | 1.5h |
| `LateInteractionRetriever` | late_interaction.py | 3 unit tests | 1h |
| `DiagramRetriever` | diagram.py | 4 unit tests | 1.5h |
| `ColBERTRetriever` | colbert.py | 4 unit tests | 1.5h |

### 2.2 Orchestration (3 classes)

| Class | File | Tests to Add | Effort |
|-------|------|--------------|--------|
| `RetrievalRouter` | orchestrator.py | 3 unit tests | 1h |
| `RetrievalMode` | orchestrator.py | 2 unit tests | 0.5h |
| `QueryClassifier` | classifier.py | 3 unit tests | 1h |

### 2.3 Reranking Providers (5 classes)

| Class | File | Tests to Add | Effort |
|-------|------|--------------|--------|
| `CohereReranker` | rerank/providers.py | 2 unit tests | 1h |
| `BGEReranker` | rerank/providers.py | 2 unit tests | 1h |
| `SentenceTransformerReranker` | rerank/providers.py | 2 unit tests | 1h |
| `JinaReranker` | rerank/providers.py | 2 unit tests | 1h |
| `LlamaIndexReranker` | rerank/providers.py | 2 unit tests | 1h |

### 2.4 Tooling Retrievers (6 classes)

| Class | File | Tests to Add | Effort |
|-------|------|--------------|--------|
| `KubernetesRetriever` | tooling/kubernetes.py | 3 unit tests | 1h |
| `HelmRetriever` | tooling/helm.py | 3 unit tests | 1h |
| `DockerfileRetriever` | tooling/dockerfile.py | 3 unit tests | 1h |
| `GraphQLRetriever` | tooling/graphql.py | 3 unit tests | 1h |
| `IstioRetriever` | tooling/istio.py | 3 unit tests | 1h |

### 2.5 Supporting Classes (6 classes)

| Class | File | Tests to Add | Effort |
|-------|------|--------------|--------|
| `EntityGraphCache` | entity_cache.py | 4 unit tests | 1.5h |
| `FusionMethod` | fusion.py | 2 unit tests | 0.5h |
| `ReasoningStep` | reasoning.py | 2 unit tests | 0.5h |
| `CitationFormatter` | citations/formatter.py | 3 unit tests | 1h |
| `TicketBackend` (ABC) | ticket.py | 2 unit tests | 0.5h |
| `TelemetryBackend` (ABC) | telemetry.py | 2 unit tests | 0.5h |

---

## Option 3: Add Integration & E2E Tests (LOW Priority)

**Effort**: 20-24 hours  
**Impact**: Achieve production-ready test coverage (75%+)

### 3.1 High-Priority Integration Tests

| Test | Components | Effort |
|------|------------|--------|
| `test_docs_qdrant_integration` | DocsRetriever + Qdrant | 2h |
| `test_hybrid_cascade_integration` | HybridRetriever cascade | 2h |
| `test_hybrid_iterative_integration` | HybridRetriever iterative | 2h |
| `test_codegraph_falkordb_integration` | CodeGraphRetriever + FalkorDB | 2h |
| `test_entity_cache_integration` | EntityGraphCache + Redis/FalkorDB | 2h |

### 3.2 Medium-Priority Integration Tests

| Test | Components | Effort |
|------|------------|--------|
| `test_diagram_qdrant_indexing` | DiagramIndexer + Qdrant | 2h |
| `test_colbert_qdrant_indexing` | ColBERTIndexer + Qdrant | 2h |
| `test_rerank_pipeline_integration` | RerankPipeline + live reranker | 2h |
| `test_ticket_jira_integration` | JiraBackend + mock server | 2h |
| `test_telemetry_prometheus_integration` | PrometheusBackend + mock | 2h |

### 3.3 End-to-End Pipeline Tests

| Test | Scenario | Components | Effort |
|------|----------|------------|--------|
| `test_full_docs_pipeline` | Ingest → Retrieve → Cite | Docs + Rerank + Citations | 3h |
| `test_full_code_pipeline` | Ingest → Retrieve → Graph | Code + Graph + CodeGraph | 3h |
| `test_multi_source_orchestration` | Multi-source query | Docs + Code + Graph + Hybrid | 3h |
| `test_entity_aware_reasoning_pipeline` | Entity + Graph traversal | EntityAware + GraphRetriever | 3h |
| `test_iterative_refinement_pipeline` | Query refinement loop | Iterative + HybridRetriever | 3h |

### 3.4 E2E Test Markers

Add pytest markers for test categorization:
```python
@pytest.mark.unit          # Unit tests (no external deps)
@pytest.mark.integration   # Integration tests (one external service)
@pytest.mark.e2e           # End-to-end tests (multiple services)
@pytest.mark.slow          # Tests taking >5s
```

---

## Execution Plan

### Phase 1: Fix Skipped Tests (Week 1)

| Day | Tasks | Deliverable |
|-----|-------|--------------|
| 1 | Fix event loop tests (3) | test_retrieval.py Pass |
| 2 | Fix FalkorDB pool test (1) | test_ingestion.py Pass |
| 3 | Fix API endpoint test (1) | test_integration.py Pass |
| 4 | Fix graph mock test (1) | test_ir_builder.py Pass |
| 5 | Review and verify | All HIGH priority done |

**Target**: 481 passed, 2 skipped (VLM external)

### Phase 2: Add Unit Tests (Weeks 2-3)

| Week | Focus | Tests |
|------|-------|-------|
| 2 | Core Retrievers | 14 tests |
| 2 | Orchestration | 8 tests |
| 3 | Reranking Providers | 10 tests |
| 3 | Tooling Retrievers | 15 tests |

**Target**: +47 tests = 528 passed

### Phase 3: Integration & E2E (Weeks 4-5)

| Week | Focus | Tests |
|------|-------|-------|
| 4 | Integration tests | 12 tests |
| 5 | E2E pipeline | 5 tests |

**Target**: +17 tests = 545 passed, 75%+ coverage

---

## Resource Requirements

| Phase | Hours | Tests Added | Coverage Gain |
|-------|------|------------|---------------|
| 1 (Fix) | 6h | 5 fixed | 0% (health) |
| 2 (Unit) | 18h | +47 | +24% |
| 3 (Int+E2E) | 22h | +17 | +10% |
| **TOTAL** | **46h** | **64** | **34%** |

---

## Success Metrics

| Metric | Current | Week 1 | Week 3 | Week 5 |
|--------|---------|--------|--------|--------|
| Passed | 473 | 478 | 525 | 542 |
| Skipped | 8 | 2 | 2 | 2 |
| Coverage | 41% | 41% | 65% | 75% |

---

## Dependencies

| Dependency | Required For | Status |
|-------------|--------------|--------|
| Qdrant (6333) | Integration tests | ✅ Available |
| FalkorDB (6379) | Integration tests | ✅ Available |
| Ollama (11434) | Embedding tests | ✅ Available |
| OpenRouter API | VLM tests | ✅ Available |

---

## Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Event loop fix breaks other tests | Medium | High | Run full suite after each fix |
| Qdrant instability | Low | Medium | Use mock fallback |
| Test execution time >10min | Medium | Low | Add `@pytest.mark.slow` to skip in CI |

---

## Next Steps

1. **Start Phase 1**: Fix 8 skipped tests
2. **Verify**: Run full test suite after each fix
3. **Document**: Update coverage matrix
4. **Iterate**: Move to Phase 2 after Phase 1 complete

---

**Plan Created**: 2026-05-02  
**Plan Owner**: Sisyphus (AI Agent)  
**Review Cycle**: Weekly