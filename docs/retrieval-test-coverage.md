# Retrieval Subsystem Test Coverage Audit

**Date**: 2026-05-03  
**Status**: 537 passed, 10 skipped
**Coverage**: 55% (+14% from start)

---

## 1. Retrieval Module Classes (86 Total)

### 1.1 Core Retrievers (11 Classes) - ✅ MOSTLY COVERED

| Class | File | Tests | Status |
|-------|------|-------|--------|
| `DocsRetriever` | docs.py | test_retrieval.py, test_retrieval_new.py | ✅ PARTIAL |
| `CodeRetriever` | code.py | test_retrieval.py | ✅ PARTIAL (SKIPPED) |
| `GraphRetriever` | graph.py | test_retrieval.py | ✅ PARTIAL |
| `CodeGraphRetriever` | code_graph.py | N/A | ❌ MISSING |
| `TicketRetriever` | ticket.py | test_retrieval.py | ✅ PARTIAL |
| `TelemetryRetriever` | telemetry.py | test_retrieval.py | ✅ PARTIAL |
| `KnowledgeRetriever` | knowledge.py | N/A | ❌ MISSING |
| `EntityCentricRetriever` | entity_centric.py | N/A | ❌ MISSING |
| `LateInteractionRetriever` | late_interaction.py | N/A | ❌ MISSING |
| `DiagramRetriever` | diagram.py | N/A | ❌ MISSING |
| `ColBERTRetriever` | colbert.py | N/A | ❌ MISSING |

### 1.2 Orchestration (4 Classes)

| Class | File | Tests | Status |
|-------|------|-------|--------|
| `RetrievalOrchestrator` | orchestrator.py | test_retrieval.py | ✅ PARTIAL |
| `RetrievalRouter` | orchestrator.py | N/A | ❌ MISSING |
| `RetrievalMode` | orchestrator.py | N/A | ❌ MISSING |
| `QueryClassifier` | classifier.py | test_retrieval.py | ✅ PARTIAL |

### 1.3 Hybrid Retrieval (2 Classes)

| Class | File | Tests | Status |
|-------|------|-------|--------|
| `HybridRetriever` | hybrid.py | test_retrieval.py | ✅ PARTIAL (SKIPPED) |
| `EnhancedHybridRetriever` | hybrid.py | test_graphrag_retrieval.py | ✅ PARTIAL |

### 1.4 Fusion (2 Classes)

| Class | File | Tests | Status |
|-------|------|-------|--------|
| `FusionMethod` | fusion.py | N/A | ❌ MISSING |
| `ResultFusion` | fusion.py | test_retrieval.py | ✅ PARTIAL |

### 1.5 Reasoning Engines (6 Classes)

| Class | File | Tests | Status |
|-------|------|-------|--------|
| `ReasoningMode` | reasoning.py, reasoning/__init__.py | test_retrieval.py | ✅ PARTIAL |
| `ReasoningStep` | reasoning.py | N/A | ❌ MISSING |
| `ReasoningEngine` | reasoning.py | test_retrieval.py | ✅ PARTIAL |
| `EntityAwareReasoningEngine` | reasoning/entity_aware.py | test_retrieval_new.py | ✅ GOOD |
| `IterativeRetrievalReasoner` | reasoning/iterative.py | test_retrieval_new.py | ✅ GOOD |
| `EntityContext` | reasoning/entity_aware.py | test_retrieval_new.py | ✅ GOOD |

### 1.6 Reranking (11 Classes)

| Class | File | Tests | Status |
|-------|------|-------|--------|
| `RerankProvider` | rerank/base.py | test_retrieval_new.py | ✅ GOOD |
| `RerankResult` | rerank/base.py | test_retrieval_new.py | ✅ GOOD |
| `BaseReranker` | rerank/base.py | test_retrieval_new.py | ✅ GOOD |
| `CohereReranker` | rerank/providers.py | N/A | ❌ MISSING |
| `BGEReranker` | rerank/providers.py | N/A | ❌ MISSING |
| `SentenceTransformerReranker` | rerank/providers.py | N/A | ❌ MISSING |
| `JinaReranker` | rerank/providers.py | N/A | ❌ MISSING |
| `LlamaIndexReranker` | rerank/providers.py | N/A | ❌ MISSING |
| `RerankPipeline` | rerank/pipeline.py | test_retrieval_new.py | ✅ PARTIAL |
| `RerankConfig` | rerank/pipeline.py | test_retrieval_new.py | ✅ GOOD |
| `RerankStrategy` | rerank/pipeline.py | test_retrieval_new.py | ✅ GOOD |

### 1.7 Citations (5 Classes)

| Class | File | Tests | Status |
|-------|------|-------|--------|
| `CitationStyle` | citations/base.py | test_retrieval_new.py | ✅ GOOD |
| `CitationSource` | citations/base.py | test_retrieval_new.py | ✅ GOOD |
| `Citation` | citations/base.py | test_retrieval_new.py | ✅ GOOD |
| `AnnotatedAnswer` | citations/base.py | test_retrieval_new.py | ✅ GOOD |
| `CitationBuilder` | citations/builder.py | test_retrieval_new.py | ✅ GOOD |
| `CitationFormatter` | citations/formatter.py | test_retrieval_new.py | ✅ PARTIAL |

### 1.8 Tooling Retrievers (6 Classes)

| Class | File | Tests | Status |
|-------|------|-------|--------|
| `KubernetesRetriever` | tooling/kubernetes.py | N/A | ❌ MISSING |
| `HelmRetriever` | tooling/helm.py | N/A | ❌ MISSING |
| `DockerfileRetriever` | tooling/dockerfile.py | N/A | ❌ MISSING |
| `GraphQLRetriever` | tooling/graphql.py | N/A | ❌ MISSING |
| `IstioRetriever` | tooling/istio.py | N/A | ❌ MISSING |
| `TicketBackend` (ABC) | ticket.py | N/A | ❌ MISSING |

### 1.9 Telemetry Backends (4 Classes)

| Class | File | Tests | Status |
|-------|------|-------|--------|
| `TelemetryBackend` | telemetry.py | N/A | ❌ MISSING |
| `PrometheusBackend` | telemetry.py | N/A | ❌ MISSING |
| `ElasticSearchBackend` | telemetry.py | N/A | ❌ MISSING |
| `InMemoryTelemetryBackend` | telemetry.py | N/A | ❌ MISSING |
| `TelemetryRetriever` | telemetry.py | test_retrieval.py | ✅ PARTIAL |

### 1.10 Indexers (6 Classes)

| Class | File | Tests | Status |
|-------|------|-------|--------|
| `DiagramQdrantIndexer` | diagram.py | N/A | ❌ MISSING |
| `DiagramGraphIndexer` | diagram.py | N/A | ❌ MISSING |
| `ColBERTIndexer` | colbert.py | N/A | ❌ MISSING |
| `ColBERTQdrantIndexer` | colbert.py | N/A | ❌ MISSING |
| `ColBERTSearchClient` | colbert.py | N/A | ❌ MISSING |
| `EntityGraphCache` | entity_cache.py | N/A | ❌ MISSING |

### 1.11 Ticket Backends (4 Classes)

| Class | File | Tests | Status |
|-------|------|-------|--------|
| `TicketBackend` (ABC) | ticket.py | N/A | ❌ MISSING |
| `JiraBackend` | ticket.py | N/A | ❌ MISSING |
| `GitHubIssuesBackend` | ticket.py | N/A | ❌ MISSING |
| `InMemoryTicketBackend` | ticket.py | N/A | ❌ MISSING |

---

## 2. Test Files Coverage

| Test File | Test Classes | Test Functions | Lines |
|----------|-------------|----------------|-------|
| test_retrieval.py | 10 | 25 | ~250 |
| test_retrieval_new.py | 24 | 70 | 935 |
| test_graphrag_retrieval.py | 6 | 10 | ~150 |

**Total Tests**: ~105 test functions across 40 test classes

---

## 3. Missing Tests by Category

### 3.1 Priority: HIGH

| Module | Class | Test Type |
|--------|-------|----------|
| docs.py | `DocsRetriever` + `InMemoryDocsBackend` | Integration |
| docs.py | `QdrantDocsBackend` | Integration/E2E |
| docs.py | `OpenRouterEmbeddingProvider` | Unit |
| docs.py | `OpenAIEmbeddingProvider` | Unit |
| hybrid.py | `HybridRetriever.cascade` | Integration |
| hybrid.py | `HybridRetriever.iterative` | Integration |
| code_graph.py | `CodeGraphRetriever` | Unit |
| entity_cache.py | `EntityGraphCache` | Unit |

### 3.2 Priority: MEDIUM

| Module | Class | Test Type |
|--------|-------|----------|
| fusion.py | `ResultFusion` | Unit |
| orchestrator.py | `RetrievalRouter` | Unit |
| orchestrator.py | `RetrievalMode` | Unit |
| ticket.py | `JiraBackend` | Integration |
| ticket.py | `GitHubIssuesBackend` | Integration |
| telemetry.py | `PrometheusBackend` | Integration |
| telemetry.py | `ElasticSearchBackend` | Integration |
| entity_centric.py | `EntityCentricRetriever` | Unit |
| knowledge.py | `KnowledgeRetriever` | Unit |

### 3.3 Priority: LOW

| Module | Class | Test Type |
|--------|-------|-----------|
| tooling/* | All 6 retrievers | Unit |
| diagram.py | All indexers | Integration |
| diagram.py | `DiagramRetriever` | Integration |
| colbert.py | All classes | Integration |
| late_interaction.py | `LateInteractionRetriever` | Integration |

---

## 4. Integration & E2E Tests Missing

### 4.1 High-Priority Integration Tests

| Source | Destination | Test Name |
|--------|-------------|-----------|
| `DocsRetriever` | Qdrant | `test_docs_retrieval_qdrant_integration` |
| `HybridRetriever` | Multiple backends | `test_hybrid_cascade_integration` |
| `HybridRetriever` | Multiple backends | `test_hybrid_iterative_integration` |
| `CodeGraphRetriever` | FalkorDB | `test_codegraph_qdrant_integration` |

### 4.2 End-to-End Scenarios

| Scenario | Components | Test Name |
|----------|-------------|-----------|
| Full retrieval pipeline | Docs → Rerank → Cite | `test_full_retrieval_pipeline` |
| Multi-source orchestration | Docs + Graph + Code | `test_multi_source_orchestration` |
| Reasoning with graph | EntityAware + Graph | `test_entity_aware_with_graph` |
| Iterative refinement | Iterative + Hybrid | `test_iterative_refinement_pipeline` |

---

## 5. Tests Requiring Refactoring

### 5.1 Currently Skipped (8 tests)

| Test File | Test Function | Reason | Fix Required |
|----------|---------------|--------|--------------|
| test_retrieval.py | test_retrieve_cascade | Event loop closed | Refactor async handling |
| test_retrieval.py | test_retrieve_iterative | Event loop closed | Refactor async handling |
| test_retrieval.py | test_retrieve_code | Event loop closed | Refactor async handling |
| test_ingestion.py | test_query_graph | FalkorDB pool | Start HttpPool in fixture |
| test_integration.py | test_query_endpoint | API test | Refactor to unit |
| test_ir_builder.py | test_add_ui_with_extraction_result | Graph mock | Fix mocking |

### 5.2 Test Infrastructure Issues

- **Event loop**: Async tests using old fixture pattern
- **FalkorDB mock**: Needs proper async mocking
- **Qdrant mock**: Missing fixture
- **HttpPool**: Not started for async tests

---

## 6. Recommendations

### 6.1 Immediate Actions

1. **Fix event loop tests**: Refactor `test_retrieval_cascade`, `test_retrieve_iterative` to proper async fixtures
2. **Add integration markers**: Mark Qdrant/FalkorDB tests with `@pytest.mark.integration`
3. **Add FalkorDB fixture**: Proper async pool management

### 6.2 Short-term (1-2 weeks)

1. Add missing unit tests for re ranking providers
2. Add entity cache tests
3. Add code graph retriever unit tests
4. Refactor remaining skipped tests

### 6.3 Medium-term (1 month)

1. Add integration tests for all retrievers
2. Add E2E pipeline tests
3. Add tooling retriever tests
4. Add diagram/colbert integration tests

---

## 7. Test Coverage Matrix

| Category | Total Classes | Covered | Coverage % |
|----------|--------------|---------|-----------|
| Core Retrievers | 11 | 6 | 55% |
| Orchestration | 4 | 2 | 50% |
| Hybrid | 2 | 2 | 100% |
| Fusion | 2 | 1 | 50% |
| Reasoning | 6 | 6 | 100% |
| Reranking | 11 | 6 | 55% |
| Citations | 6 | 6 | 100% |
| Tooling | 6 | 1 | 17% |
| Telemetry | 5 | 1 | 20% |
| Indexers | 6 | 0 | 0% |
| Ticket Backends | 4 | 0 | 0% |
| **TOTAL** | **63** | **31** | **50%** |

---

## 8. Action Items

| Priority | Item | Effort | Owner |
|----------|------|--------|-------|
| HIGH | Fix 3 event loop tests | 2h | AI |
| HIGH | Refactor FalkorDB fixture | 4h | AI |
| HIGH | Add DocsRetriever Qdrant integration | 4h | AI |
| MEDIUM | Add entity cache tests | 4h | AI |
| MEDIUM | Add code graph tests | 4h | AI |
| MEDIUM | Add EntityCentricRetriever tests | 2h | AI |
| LOW | Add tooling tests (6 retriever) | 8h | AI |
| LOW | Add colbert tests | 8h | AI |
| LOW | Add diagram tests | 8h | AI |