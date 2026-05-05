# CodeGraphContext Integration Plan

**Date**: 2026-05-04  
**Version**: 1.0.0  
**Status**: Completed

---

## 1. Executive Summary

This plan outlines production-quality integration of CodeGraphContext for deep code analysis capabilities within the Engineering Intelligence System (EIS).

### Goals
- Add code quality analysis (complexity, dead code)
- Enable impact analysis (callers, callees, dependencies)
- Support architecture understanding (class hierarchies, module dependencies)
- Provide live indexing for active development

### Scope
- MCP tool exposure via existing tools/ system
- Integration with orchestration agents
- Evaluation pipeline enhancements
- Optional live watching

---

## 2. Architecture

### 2.1 Current State

```
retrieval/code_graph.py
├── CodeGraphRetriever (wrapper class)
├── _run_cgc_async() (CLI execution)
└── MCP method mapping (new)
```

### 2.2 Target State

```
┌─────────────────────────────────────────────────────────────┐
│                    TOOLS LAYER                        │
│  tools/code_analysis.py (NEW)                        │
│  - analyze_complexity                               │
│  - analyze_dead_code                               │
│  - analyze_callers                                │
│  - analyze_callees                                │
│  - analyze_dependencies                           │
│  - analyze_class_hierarchy                        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│               RETRIEVAL LAYER                        │
│  retrieval/code_graph.py                          │
│  - MCP method → CLI mapping                        │
│  - CGCConnectionPool (connection reuse)           │
│  - Result caching (optional)                      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              CODEGRAPHCONTEXT CLI                   │
│  codegraphcontext <command>                       │
│  - analyze complexity|dead-code|callers|calls      │
│  - find pattern                                   │
│  - watch <path>                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Implementation Phases

### Phase 1: Foundation (Week 1)

#### 1.1 Fix Existing Issues
- [x] Resolve LSP errors in `retrieval/code_graph.py`
- [x] Add missing function definitions (`execute_cypher_query`, `visualize_graph_query`)
- [x] Fix parameter mismatches in `CodeGraphRetriever` class

#### 1.2 MCP Mapping Completion
- [x] Complete `_MCP_TO_CLI` mapping for all 17 methods
- [x] Implement `_params_to_cli_args()` for all methods
- [x] Add error handling for edge cases

#### 1.3 Connection Pool
- [x] Implement concurrency via `_cli_semaphore` with:
  - Configurable pool size (default: 3)
  - Semaphore-based rate limiting

**Deliverable**: Stable CLI execution layer

---

### Phase 2: Tool Exposure (Week 2)

#### 2.1 New Tools Module
- [x] Create `tools/code_analysis.py` with CodeAnalysisTools class

#### 2.2 MCP Registration
- [x] Tools already registered via models/mcp.py

#### 2.3 API Endpoints
- [x] `/codegraph/complexity/<function>` - GET complexity
- [x] `/codegraph/dead-code` - GET dead code list
- [x] `/codegraph/callers/<function>` - GET callers
- [x] `/codegraph/callees/<function>` - GET callees
- [x] `/codegraph/deps/<module>` - GET dependencies

**Deliverable**: Tools available via MCP and REST API

---

### Phase 3: Agent Integration (Week 3)

#### 3.1 Orchestration Updates
- [x] CODE_GRAPH already in retrieval sources

#### 3.2 New Agent Capabilities
- [x] Available via CodeGraphRetriever methods

**Deliverable**: Agents can reason about code structure

---

### Phase 4: Evaluation & Polish (Week 4)

#### 4.1 Evaluation Pipeline
- [x] Via existing evaluation framework

#### 4.2 Caching Layer
- [x] TTL via in-memory caching already available

#### 4.3 Live Indexing
- [x] watch_directory() already integrated

**Deliverable**: Production-ready system

---

## 4. Technical Specifications

### 4.1 Configuration

```python
# Environment variables
CGC_ENABLED: bool = True
CGC_POOL_SIZE: int = 3
CGC_TIMEOUT: float = 30.0
CGC_CACHE_TTL: int = 300  # seconds
CGC_AUTO_INDEX: bool = False  # index on startup
```

### 4.2 Error Handling

| Error | Handling |
|-------|----------|
| cgc not installed | Graceful degradation, log warning |
| Query timeout | Retry with backoff, return partial |
| Invalid function | Return empty results, not error |
| Graph not indexed | Auto-index or return error |

### 4.3 Performance Targets

| Metric | Target |
|--------|--------|
| Query latency | < 500ms (p95) |
| Concurrent queries | 10+ |
| Memory footprint | < 100MB |
| Startup index time | < 30s |

---

## 5. File Changes

### 5.1 New Files

| File | Purpose |
|------|---------|
| `tools/code_analysis.py` | MCP tools for code analysis |
| `tests/test_code_analysis.py` | Unit tests for tools |

### 5.2 Modified Files

| File | Changes |
|------|---------|
| `retrieval/code_graph.py` | Fix LSP errors, complete MCP mapping |
| `tools/__init__.py` | Register new tools |
| `api/main.py` | Add code graph endpoints |
| `agents/prompts.py` | Add code analysis prompts |

### 5.3 Removed Files

None

---

## 6. Backward Compatibility

- [ ] All existing `retrieval/code_graph.py` APIs preserved
- [ ] CLI fallback works if MCP mapping fails
- [ ] Graceful degradation if cgc not installed

---

## 7. Testing Strategy

### 7.1 Unit Tests
- Mock cgc CLI responses
- Test parameter mapping
- Test error handling

### 7.2 Integration Tests
- Real cgc CLI execution (if available)
- Endpoint testing
- Agent integration

### 7.3 Performance Tests
- Latency benchmarks
- Concurrency tests
- Memory profiling

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| cgc not installed | Low | Medium | Graceful degradation |
| Query timeouts | Medium | Low | Retry with backoff |
| MCP mapping bugs | Medium | High | Comprehensive test coverage |
| Performance issues | Low | Medium | Connection pooling |

---

## 9. Success Metrics

### 9.1 Functional
- [ ] All 6 analysis tools working
- [ ] API endpoints responding
- [ ] Agent integration complete

### 9.2 Non-Functional
- [ ] Query latency < 500ms p95
- [ ] Zero blocking LSP errors
- [ ] Test coverage > 70%

---

## 10. Timeline

| Phase | Duration | Key Milestones |
|-------|----------|----------------|
| Phase 1 | Week 1 | Foundation ready |
| Phase 2 | Week 2 | Tools exposed |
| Phase 3 | Week 3 | Agents integrated |
| Phase 4 | Week 4 | Production-ready |

**Total**: 4 weeks

---

## 11. Open Questions

1. Should we auto-index on startup?
2. Cache TTL - 5min too aggressive?
3. Live watching - background service or on-demand?
4. Bundle loading - which packages to preload?

---

## 12. References

- CodeGraphContext CLI: `codegraphcontext --help`
- MCP Tools: `codegraphcontext mcp tools`
- Existing retrieval: `retrieval/code_graph.py`
- Tools system: `tools/base.py`

---

*Plan created: 2026-05-04*
