# Comprehensive Fix Plan for GAG v3.2.0

Based on the audit report, this plan addresses all 70+ confirmed issues. No backward compatibility requirements.

## Priority Classification

- **P0 (Critical)**: Runtime crashes, data corruption, security vulnerabilities
- **P1 (High)**: Features non-functional, integration failures
- **P2 (Medium)**: Logic bugs, quality issues

---

## P0 - Critical Fixes (Must Fix Before Deployment)

### 1. Dependency Issues

| Item | File | Fix |
|------|------|-----|
| P0-1 | `pyproject.toml`, `requirements.txt` | Add `pydantic-settings` to dependencies |

### 2. Kubernetes Configuration

| Item | File | Fix |
|------|------|-----|
| P0-2 | `k8s/base/configmap.yaml` | Replace `QDRANT_URL` with `QDRANT_HOST` + `QDRANT_PORT` |
| P0-3 | `k8s/base/configmap.yaml` | Replace `FALKORDB_URL` with `FALKORDB_HOST` + `FALKORDB_PORT` |
| P0-4 | `k8s/base/configmap.yaml` | Change FalkorDB port from 7474 to 7379 |

### 3. Runtime-Breaking Bugs

| Item | File | Fix |
|------|------|-----|
| P0-5 | `core/logging_config.py:10` | Add `timezone` to import: `from datetime import datetime, timezone` |
| P0-6 | `core/secrets/__init__.py:100` | Parse SecretString with `json.loads(response["SecretString"])` before .get() |
| P0-7 | `core/secrets/__init__.py:169` | Use sync `for` loop OR import `from azure.keyvault.secrets.aio import SecretClient` |

### 4. Security Vulnerabilities

| Item | File | Fix |
|------|------|-----|
| P0-8 | `ui/graph_builder.py:52,65-67,97-101` | Use parameterized Cypher: `CREATE (s:UISketch $props)` with `parameters={props}` |
| P0-9 | `api/main.py:780-787` | Add Cypher query validation - block DETACH DELETE, DROP, MERGE with (n) |
| P0-10 | `documents/confluence.py:166-177` | Check ALL resolved IPs, not just first: iterate through `addr_info` list |
| P0-11 | `documents/webdav.py:115-163` | Replace regex with `xml.etree.ElementTree` or `defusedxml` |

---

## P1 - High Priority Fixes

### 5. Stub Implementations

| Item | File | Fix |
|------|------|-----|
| P1-1 | `core/metrics.py:19-31` | Implement actual metrics collection (push to Prometheus/OTel) |
| P1-2 | `core/adapters/clouds.py:127-138,287-298,444-455` | Implement real IR analysis using pattern matching |
| P1-3 | `core/adapters/base.py:89,120-123` | Set default adapter or implement proper auto-detection |
| P1-4 | `core/knowledge/resolver.py:42` | Compute confidence from analysis results |

### 6. Fallback Fabricated Data (13+ tools)

| Item | File | Fix |
|------|------|-----|
| P1-5 | `tools/feedback.py:378-383` | Return `ToolOutput(error="LLM unavailable", result=None)` instead of fake data |
| P1-6 | `tools/feedback.py:234-244` | Same pattern for MetricTrendAnalyzer |
| P1-7 | `tools/day2.py:70-80` | Same pattern for AutoScalerTool |
| P1-8 | `tools/day2.py:291-296` | Same pattern for RootCauseAnalyzer |
| P1-9 | `tools/day2.py:161-166` | Same pattern for BackupManager |
| P1-10 | `tools/observability.py:69-81` | Same pattern for MetricsCollector |
| P1-11 | `tools/observability.py:455-463` | Same pattern for SLOTracker |
| P1-12 | `tools/base.py:53-113` | Implement real evaluation with actual code analysis |

### 7. Integration Failures

| Item | File | Fix |
|------|------|-----|
| P1-13 | `retrieval/orchestrator.py:118-195` (10 methods) | Add `logger.exception(f" retrieval failed: {e}")` to all bare except clauses |
| P1-14 | `llm/router.py:150-154` | Cache `EmbeddingPipeline()` in `__init__`, reuse in `embed()` |

### 8. Documents Module

| Item | File | Fix |
|------|------|-----|
| P1-15 | `documents/parse.py:147` | Remove `DoclingProxyOcr()` reference or implement the class |
| P1-16 | `documents/parse.py:73-84` | Import missing readers or remove from reader_map |
| P1-17 | `documents/colpali.py:15` | Make conditional: `try: import torch; except ImportError: torch = None` |

### 9. CI/CD Pipeline

| Item | File | Fix |
|------|------|-----|
| P1-18 | `.github/workflows/ci.yml:38-39` | Run all tests: `pytest tests/ -v` (not just 2 files) |
| P1-19 | `.github/workflows/ci.yml:69,74` | Remove `|| true` from pip-audit and bandit |

---

## P2 - Medium Priority Fixes

### 10. Logic Bugs

| Item | File | Fix |
|------|------|-----|
| P2-1 | `agents/validator.py:288` | Change filter from `len(w) > 4` to `len(w) >= 3` |
| P2-2 | `agents/orchestration.py:509-512`, `agents/retrieval.py:273-276` | Use proper EMA: `new * alpha + old * (1 - alpha)` |
| P2-3 | `agents/orchestration.py:338-343` | Propagate context: `context = {**context, **step_results[i-1]}` |

### 11. Pseudo-AI Reasoning Engine

| Item | File | Fix |
|------|------|-----|
| P2-4 | `retrieval/reasoning.py` (all modes) | Either implement real LLM reasoning or rename to remove "AI" claims |

### 12. Entity/Community Detection

| Item | File | Fix |
|------|------|-----|
| P2-5 | `ingestion/graphrag/entity_extractor.py:125-150` | Add logging on JSON parse failure |
| P2-6 | `ingestion/graphrag/community_detector.py:57-112` | Implement Louvain/Leiden algorithm |

### 13. Documents (Additional)

| Item | File | Fix |
|------|------|-----|
| P2-7 | `documents/confluence.py:208-249,371-413` | Remove duplicate `get_page_children` method |
| P2-8 | `multimodal/ir_builder.py:124-125` | Store task: `task = loop.create_task(...)`, track for completion |

### 14. CD Pipeline

| Item | File | Fix |
|------|------|-----|
| P2-9 | `.github/workflows/cd.yml:5,51` | Fix dev deployment trigger (add develop branch to on.push or remove condition) |

---

## Execution Order

```
Phase 1 (Week 1): Critical Runtime & Security
├── P0-1 through P0-4 (Dependencies & K8s Config)
├── P0-5 through P0-7 (Runtime Bugs)
├── P0-8 through P0-11 (Security)
└── P1-18, P1-19 (CI fixes)

Phase 2 (Week 2): Integration & Stubs
├── P1-1 through P1-4 (Core stubs)
├── P1-5 through P1-12 (Fallback fixes)
├── P1-13, P1-14 (Integration)
└── P1-15 through P1-17 (Documents)

Phase 3 (Week 3): Logic & Quality
├── P2-1 through P2-3 (Logic bugs)
├── P2-4 (Reasoning engine)
├── P2-5, P2-6 (Entity/Community)
├── P2-7 through P2-9 (Remaining)
└── Testing & Validation
```

---

## Files to Modify (Summary)

| Module | Files | Issues |
|--------|-------|--------|
| `core/` | config.py, logging_config.py, metrics.py, secrets/__init__.py | 7 |
| `core/adapters/` | base.py, clouds.py, registry.py | 4 |
| `core/knowledge/` | resolver.py | 1 |
| `agents/` | validator.py, orchestration.py, retrieval.py | 3 |
| `tools/` | feedback.py, day2.py, observability.py, base.py | 4 |
| `retrieval/` | orchestrator.py, hybrid.py, reasoning.py, entity_extractor.py, community_detector.py | 5 |
| `llm/` | router.py | 1 |
| `documents/` | parse.py, confluence.py, webdav.py, colpali.py | 4 |
| `ui/` | graph_builder.py | 1 |
| `api/` | main.py | 1 |
| `k8s/` | base/configmap.yaml | 1 |
| `.github/workflows/` | ci.yml, cd.yml | 2 |
| Project root | pyproject.toml, requirements.txt | 2 |

**Total: 35 files across 13 modules**

---

## Verification Commands

After fixes, run:

```bash
# Type checking
./eis check

# Tests
./eis test

# Security
bandit -r . -x ./tests,./docs
pip-audit -r requirements.txt
```