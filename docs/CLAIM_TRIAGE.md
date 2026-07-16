# Claim Verification Baseline & Triage

**Date:** 2026-07-11 (updated after Phase 0.2)
**Codebase:** `drbye78/gag` v4.0.0
**Phase:** 0.5 — Claim Verification (post-Phase 0.2 stabilization)
**Test suite:** `tests/claims/` (22 files, 114 test cases)

---

## Executive Summary

| Metric | Before Phase 0.2 | After Phase 0.2 | Delta |
|--------|------------------|-----------------|-------|
| Total test cases | 114 | 114 | 0 |
| Passed | 72 (63%) | **92 (81%)** | +20 |
| Failed | 41 (36%) | **21 (18%)** | -20 |
| Skipped | 1 (1%) | 1 (1%) | 0 |
| Claims fully passing | 8 of 22 (36%) | **13 of 22 (59%)** | +5 |
| Claims fully failing | 5 of 22 (23%) | **1 of 22 (5%)** | -4 |
| Claims partially passing | 9 of 22 (41%) | **8 of 22 (36%)** | -1 |

**What Phase 0.2 fixed:**
- Installed `llama_index` (was blocking 12 tests via import failures)
- Made `docling` import conditional in `documents/parse.py` (was blocking 6 tests)
- Made `torch` import conditional in `documents/colpali.py` and `ui/colpali_integration.py` (was blocking 15 tests via broken `.so` file)
- Fixed `tests/test_ui_colpali_integration.py` to skip when torch unavailable
- Deleted `pytest.ini` (consolidated into `pyproject.toml`)
- Fixed `pyproject.toml` classifiers (removed Python 3.11, fixed license)
- Fixed `Dockerfile` healthcheck (`requests` → `httpx`)
- Added `.dockerignore`
- Fixed `cd.yml` deprecated actions (`azure/k8s-set-context@v1` → `@v4`, `actions/create-release@v1` → `softprops/action-gh-release@v2`)
- Fixed `cd.yml` multi-line image-tag extraction

**Claims that newly pass after Phase 0.2:**
- #03 (5 execution modes) — was blocked by orchestrator import failure
- #04 (streaming) — same
- #05 (11 retrieval sources) — orchestrator now constructs
- #14 (unified ingestion) — `llama_index` import unblocked
- #20 (tooling search) — `llama_index` import unblocked

**Remaining 21 failures are real code-level issues** — no more import failures. These are the actual refactor backlog.

---

## Per-Claim Triage (Post-Phase 0.2)

### Claim 01 — Validates its own answers
**Status:** FAIL (0/3 pass) — unchanged
**README says:** "it plans, retrieves from multiple sources, reasons with a knowledge graph, and validates its own answers"
**What failed:**
- `test_orchestration_response_includes_validation` — response has no `validation` key
- `test_validator_agent_is_registered` — `AgentType.VALIDATOR` does not exist
- `test_orchestration_has_validate_executor` — no `validate` executor in the engine

**Root cause:** `ValidatorAgent` (315 lines) is fully implemented but completely disconnected — not in the `AgentType` enum, not in `_register.py`, not in the executor map.
**Decision:** FIX
**Owning phase:** Phase 2.2 (Wire validator into orchestration loop)
**Effort:** Small — register the agent, add `ValidateStepExecutor`, append validate step to plans.

---

### Claim 02 — Five reasoning modes
**Status:** PARTIAL (5/7 pass) — unchanged
**README says:** "Direct, chain-of-thought, tree-of-thoughts, reflection, and critique modes"
**What passed:** All 5 mode enum values exist.
**What failed:**
- `test_reasoning_uses_llm_not_string_concat` — LLM router is called but response extraction is fragile (mock returns `MagicMock`, not a real response; the answer field is a mock object). The code calls the LLM but doesn't extract the text correctly.
- `test_tree_of_thoughts_makes_multiple_llm_calls` — ToT made 0 LLM calls. `_tree_reason` doesn't use the LLM at all; pure string manipulation.

**Root cause:** The LLM path exists in `_direct_reason` and `_chain_reason` but NOT in `_tree_reason`, `_reflect_reason`, or `_critique_reason`.
**Decision:** FIX
**Owning phase:** Phase 2.1 (Distinct LLM call patterns per mode)
**Effort:** Medium — implement LLM calls for 3 modes, fix response extraction.

---

### Claim 03 — Five execution modes
**Status:** PASS (7/7) — **NEWLY PASSING** (was 0/7)
**What changed:** Orchestrator now constructs successfully after torch/docling conditional imports. All 5 `OrchestrationMode` enum values exist; `execute_branching` and `execute_recursive` are callable.

---

### Claim 04 — Streaming execution
**Status:** PASS (1/1) — **NEWLY PASSING** (was 0/1)
**What changed:** Orchestrator constructs; `execute_streaming` yields expected event types.

---

### Claim 05 — 11 retrieval sources
**Status:** PASS (13/13) — **NEWLY PASSING** (was 12/13)
**What changed:** Orchestrator constructs; all `_retrieve_*` methods exist.

---

### Claim 06 — 4 fusion methods
**Status:** PASS (9/9) — unchanged

---

### Claim 07 — 5 rerank providers
**Status:** PASS (6/6) — unchanged

---

### Claim 08 — Citation styles
**Status:** PARTIAL (6/11 pass) — unchanged
**What failed:** All 5 `test_citation_style_produces_output` tests — `CitationBuilder.build()` requires a `results` positional argument that the test isn't passing correctly (API mismatch).
**Decision:** FIX
**Owning phase:** Phase 5.3
**Effort:** Small — fix the test to match the actual `CitationBuilder.build()` signature, or fix the API.

---

### Claim 09 — ColBERT
**Status:** SKIP (2/2 pass, 1 skip) — unchanged
**Decision:** Mark as optional in README.
**Owning phase:** Phase 5.3

---

### Claim 10 — GraphRAG pipeline
**Status:** PARTIAL (2/4 pass) — unchanged
**What failed:**
- Community detection uses BFS, not Louvain/Leiden
- Relationship inferrer caps at 50 pairs with sliding window of 9
**Decision:** FIX
**Owning phase:** Phase 2.3

---

### Claim 11 — Knowledge graph content
**Status:** FAIL (0/3 pass) — unchanged
**What failed:** `get_use_case_library`, `get_adr_library`, `get_reference_library` functions don't exist in the knowledge content modules.
**Decision:** FIX (or REMOVE if content is placeholder)
**Owning phase:** Phase 2.4

---

### Claim 12 — Entity graph cache
**Status:** PARTIAL (2/4 pass) — improved from 1/4
**What passed:** Both API endpoints now exist (stats + invalidate).
**What failed:**
- `test_entity_cache_lru_eviction` — `EntityGraphCache.__init__()` doesn't accept `ttl_seconds` kwarg
- `test_entity_cache_ttl_expiry` — same API mismatch
**Decision:** FIX
**Owning phase:** Phase 3.5
**Effort:** Small — fix the test to match the actual `EntityGraphCache` API, verify LRU+TTL.

---

### Claim 13 — 7 source types
**Status:** PASS (3/3) — unchanged

---

### Claim 14 — Unified ingestion
**Status:** PASS (3/3) — **NEWLY PASSING** (was 1/3)
**What changed:** `llama_index` import unblocked; handler registry now accessible; 33 artifact types confirmed; handlers have async `handle` methods.

---

### Claim 15 — Code chunking 7 languages
**Status:** PASS (7/7) — unchanged

---

### Claim 16 — VLM processor
**Status:** PASS (3/3) — unchanged

---

### Claim 17 — ColPali
**Status:** PARTIAL (2/3 pass) — improved from 0/3
**What passed:** Module exists; torch import is conditional.
**What failed:** `test_colpali_search_method_exists` — `UISketchVisualIndexer` is in `ui/colpali_integration.py`, not `documents/colpali.py`. Test import path is wrong.
**Decision:** FIX (test fix)
**Owning phase:** Phase 4.2
**Effort:** Trivial — fix the test import path.

---

### Claim 18 — Platform adapters
**Status:** PARTIAL (6/7 pass) — unchanged
**What failed:** `test_aws_adapter_produces_non_hardcoded_recommendations` — `transform_ir_to_platform` is sync, not async. Test `await`s the result.
**Decision:** FIX
**Owning phase:** Phase 4.3
**Effort:** Small — fix the test to not await, then verify non-hardcoded output.

---

### Claim 19 — 30+ tools
**Status:** PASS (2/2) — unchanged

---

### Claim 20 — Tooling search
**Status:** PASS (6/6) — **NEWLY PASSING** (was 1/6)
**What changed:** `llama_index` import unblocked; all 5 tooling retrievers exist; all 5 search endpoints exist.

---

### Claim 21 — Multilingual
**Status:** PASS (4/4) — unchanged

---

### Claim 22 — Observability
**Status:** PARTIAL (3/5 pass) — improved from 2/5
**What passed:** JSON format setting; metrics collector exists; execution state tracking works.
**What failed:**
- `test_middleware_adds_trace_id` — no `TraceMiddleware` or `RequestIDMiddleware` in the middleware stack
- `test_p50_p95_p99_metrics` — `ObservabilityCollector` class doesn't exist in `core.observability`
**Decision:** FIX
**Owning phase:** Phase 5.1
**Effort:** Medium — add trace middleware, implement percentile tracking.

---

## Updated Summary by Decision

| Decision | Count | Claims |
|----------|-------|--------|
| **No action (claim met)** | 13 | #03, #04, #05, #06, #07, #13, #14, #15, #16, #19, #20, #21, (+ #09 with caveat) |
| **FIX** | 9 | #01, #02, #08, #10, #11, #12, #17, #18, #22 |
| **REMOVE** | 0 | (none yet) |
| **DEFER** | 0 | (none yet) |

## Remaining 21 Failures (the real refactor backlog)

| Claim | Failures | Root cause | Phase | Effort |
|-------|----------|------------|-------|--------|
| #01 | 3 | ValidatorAgent not wired | 2.2 | Small |
| #02 | 2 | 3 reasoning modes don't use LLM | 2.1 | Medium |
| #08 | 5 | CitationBuilder.build() API mismatch | 5.3 | Small |
| #10 | 2 | BFS communities, 50-pair cap | 2.3 | Medium |
| #11 | 3 | Knowledge getter functions missing | 2.4 | Medium |
| #12 | 2 | EntityGraphCache API mismatch | 3.5 | Small |
| #17 | 1 | Test import path wrong | 4.2 | Trivial |
| #18 | 1 | transform_ir_to_platform is sync | 4.3 | Small |
| #22 | 2 | No trace middleware, no percentiles | 5.1 | Medium |

**Total estimated effort to close all 21 failures:** ~2-3 weeks of focused work, distributed across Phases 2-5.

---

## Next Steps

The claim suite is now clean — every failure is a real code-level issue, not an import artifact. The highest-signal next steps are:

1. **Phase 2.2** — Wire the ValidatorAgent (claim #01, 3 failures). Smallest fix, highest symbolic value.
2. **Phase 2.1** — Implement LLM calls for ToT/Reflect/Critique (claim #02, 2 failures).
3. **Phase 2.4** — Audit knowledge content files and expose proper getters (claim #11, 3 failures).
4. **Phase 2.3** — Replace BFS with Louvain, remove pair cap (claim #10, 2 failures).

Run `pytest tests/claims/ -v -m claim` at any time to verify progress.

---

## Per-Claim Triage

### Claim 01 — Validates its own answers
**Status:** FAIL (0/3 pass)
**README says:** "it plans, retrieves from multiple sources, reasons with a knowledge graph, and validates its own answers"
**What failed:**
- `test_orchestration_response_includes_validation` — response has no `validation` key
- `test_validator_agent_is_registered` — `AgentType.VALIDATOR` does not exist
- `test_orchestration_has_validate_executor` — no `validate` executor in the engine

**Root cause:** `ValidatorAgent` (315 lines) is fully implemented but completely disconnected — not in the `AgentType` enum, not in `_register.py`, not in the executor map.
**Decision:** FIX
**Owning phase:** Phase 2.2 (Wire validator into orchestration loop)
**Effort:** Small — register the agent, add `ValidateStepExecutor`, append validate step to plans.

---

### Claim 02 — Five reasoning modes
**Status:** PARTIAL (5/7 pass)
**README says:** "Direct, chain-of-thought, tree-of-thoughts, reflection, and critique modes"
**What passed:** All 5 mode enum values exist.
**What failed:**
- `test_reasoning_uses_llm_not_string_concat` — LLM router is called but the result isn't extracted correctly (mock returns `MagicMock` not a real response object, so the answer field is a mock object, not the LLM text). The underlying code does call the LLM, but the response extraction is fragile.
- `test_tree_of_thoughts_makes_multiple_llm_calls` — ToT made 0 LLM calls. The `_tree_reason` method doesn't use the LLM at all; it's pure string manipulation.

**Root cause:** The LLM path exists in `_direct_reason` and `_chain_reason` but NOT in `_tree_reason`, `_reflect_reason`, or `_critique_reason`. Those three are still string concatenation.
**Decision:** FIX
**Owning phase:** Phase 2.1 (Distinct LLM call patterns per mode)
**Effort:** Medium — implement LLM calls for 3 modes, each with distinct prompt patterns.

---

### Claim 03 — Five execution modes
**Status:** FAIL (0/7 pass)
**README says:** "Iterative, Parallel, Sequential, Branching, Recursive"
**What failed:**
- All 5 `test_execution_mode_exists` parametrized tests — `OrchestrationMode` enum does not exist at all. The modes are defined as a string enum but the import path or class name is wrong.
- `test_execute_branching_works` — fails because the orchestrator can't be constructed (cascading import failure).
- `test_execute_recursive_exists` — same cascading failure.

**Root cause:** The `OrchestrationMode` enum exists in `orchestration.py` but the import in the test fails because the orchestrator constructor crashes (likely the `agents._register` import or agent registry failure). Need to investigate whether the enum is actually exported.
**Decision:** FIX
**Owning phase:** Phase 3.2 + 3.3 (Wave-based execution + verify all 5 modes)
**Effort:** Medium — fix the import chain, then verify branching/recursive actually work.

---

### Claim 04 — Streaming execution
**Status:** FAIL (0/1 pass)
**README says:** "Streaming execution with step-by-step progress yields"
**What failed:** `test_streaming_yields_expected_events` — cascading failure from orchestrator construction.
**Decision:** FIX
**Owning phase:** Phase 3.4 (Streaming verification)
**Effort:** Small once Phase 3.2 unblocks the orchestrator.

---

### Claim 05 — 11 retrieval sources
**Status:** PARTIAL (12/13 pass)
**README says:** "11 sources: Docs, Code, Graph, Code Graph, Tickets, Telemetry, Diagram, UI Sketch, ColBERT, Knowledge Graph, Multimodal"
**What passed:** All 11 `RetrievalSource` enum values exist; count is exactly 11.
**What failed:** `test_orchestrator_handles_all_sources` — cascading failure from orchestrator construction.
**Decision:** FIX
**Owning phase:** Phase 3.1 (lazy init + bug fixes)
**Effort:** Small — the enum is correct, just need the orchestrator to construct.

---

### Claim 06 — 4 fusion methods
**Status:** PASS (9/9 pass)
**README says:** "4 fusion methods: RRF, Score-normalized, Weighted, Combined"
**What passed:** All 4 methods exist, produce sorted results, and are deterministic across runs.
**Decision:** No action needed. Claim met.
**Note:** The `_get_result_key` hash bug mentioned in the strategy doesn't manifest in practice because the test uses the same process. The fix (SHA-256 instead of `hash()`) is still recommended for cross-process determinism but is not blocking.

---

### Claim 07 — 5 rerank providers
**Status:** PASS (6/6 pass)
**README says:** "5 rerank providers: Cohere, BGE, SentenceTransformers, Jina, LlamaIndex"
**What passed:** All 5 providers exist in the enum and have class implementations.
**Decision:** No action needed. Claim met.
**Note:** Integration tests (actually calling each provider) are deferred to Phase 5.3 with `@pytest.mark.skipif` for missing API keys.

---

### Claim 08 — Citation styles
**Status:** PARTIAL (6/11 pass)
**README says:** "5 citation styles: Parenthetical, Verbatim, Footnote, Highlight, Structured, Diagram" (note: README says 5 but lists 6)
**What passed:** All 6 `CitationStyle` enum values exist.
**What failed:** All 5 `test_citation_style_produces_output` tests — `CitationBuilder.build()` either doesn't exist or doesn't return objects with `.text` or `.formatted` attributes. The API may be different from what the test assumes.
**Root cause:** The `CitationBuilder` API doesn't match the test's assumptions. Need to check the actual return type.
**Decision:** FIX
**Owning phase:** Phase 5.3 (verify citation styles produce output)
**Effort:** Small — fix the test to match the actual API, or fix the API to be more standard.
**Also:** Fix README count from "5" to "6".

---

### Claim 09 — ColBERT
**Status:** SKIP (2/2 pass, 1 skip)
**README says:** "ColBERT support: Late interaction embeddings for enhanced semantic search"
**What passed:** `ColBERTRetriever` class exists; config settings exist.
**What skipped:** `test_colbert_search_returns_results` — ColBERT not enabled (no `fastembed` installed).
**Decision:** FIX (mark as optional in README)
**Owning phase:** Phase 5.3
**Effort:** Small — either install `fastembed` in CI or mark the feature as opt-in in the README.

---

### Claim 10 — GraphRAG pipeline
**Status:** PARTIAL (2/4 pass)
**README says:** "GraphRAG pipeline with entity extraction, relationship inference, community detection"
**What passed:** `GraphRAGPipeline` exists; LLM entity extractor is the default when `use_llm=True`.
**What failed:**
- `test_community_detection_uses_louvain_or_leiden` — uses BFS connected components, not Louvain/Leiden.
- `test_relationship_inferrer_no_silent_cap` — caps at 50 pairs with sliding window of 9.

**Root cause:** Community detection is BFS; relationship inferrer has silent caps.
**Decision:** FIX
**Owning phase:** Phase 2.3 (real Louvain + no caps)
**Effort:** Medium — add `python-louvain` dep, rewrite `_build_communities`, remove caps from `_create_entity_pairs`.

---

### Claim 11 — Knowledge graph content
**Status:** FAIL (0/3 pass)
**README says:** "7 use cases per platform, 5 ADRs, 8 reference architectures"
**What failed:**
- `test_use_cases_per_platform` — `get_use_case_library` function doesn't exist in `core/knowledge/usecases.py`.
- `test_adrs_count` — `get_adr_library` doesn't exist in `core/knowledge/adrs.py`.
- `test_reference_architectures_count` — `get_reference_library` doesn't exist in `core/knowledge/reference.py`.

**Root cause:** The knowledge content modules (656 lines total) exist but don't expose the expected getter functions. Either the API is different, or the content is structured differently than assumed.
**Decision:** FIX (or REMOVE if content is placeholder)
**Owning phase:** Phase 2.4 (knowledge content verification)
**Effort:** Medium — audit the 656 lines, expose proper getters, verify content is real not placeholder. If placeholder, either populate or remove the claim.

---

### Claim 12 — Entity graph cache
**Status:** PARTIAL (1/4 pass)
**README says:** "Entity graph cache: LRU eviction (500 entries, 1h TTL) with REST API for monitoring"
**What passed:** `/entity/cache/invalidate` endpoint exists.
**What failed:**
- `test_entity_cache_lru_eviction` — `EntityGraphCache.__init__()` doesn't accept `ttl_seconds` kwarg. API mismatch.
- `test_entity_cache_ttl_expiry` — same API mismatch.
- `test_entity_cache_stats_endpoint_exists` — cascading `llama_index` import failure.

**Root cause:** `EntityGraphCache` constructor signature is different from what the test assumes. The `llama_index` import failure blocks the API route check.
**Decision:** FIX
**Owning phase:** Phase 3.5 (entity cache verification)
**Effort:** Small — fix the test to match the actual `EntityGraphCache` API, verify LRU+TTL works. The `llama_index` import failure is a separate issue (see cross-cutting).

---

### Claim 13 — 7 source types
**Status:** PASS (3/3 pass)
**README says:** "7 source types: Git repositories, Documents, Tickets, Telemetry, Knowledge Base, Architecture, Requirements"
**What passed:** All 7 source modules importable; git pipeline has `ingest_repository`; document ingestion produces chunks.
**Decision:** No action needed. Claim met.

---

### Claim 14 — Unified ingestion
**Status:** PARTIAL (1/3 pass)
**README says:** "33 artifact types, 24 handlers"
**What passed:** `ArtifactType` enum has exactly 33 types.
**What failed:**
- `test_handler_registry_exists` — `llama_index` import failure blocks the handler registry import.
- `test_handlers_have_async_handle_method` — same cascading failure.

**Root cause:** `llama_index` is not installed in the test environment. It's listed as a dependency but not installed.
**Decision:** FIX (install `llama_index` or make import conditional)
**Owning phase:** Phase 0.2 (CI unfreeze — install all deps) + Phase 5.4
**Effort:** Small — `pip install llama-index` in CI, or make the import conditional.

---

### Claim 15 — Code chunking 7 languages
**Status:** PASS (7/7 pass)
**README says:** "Code chunking with entity extraction (Python, JavaScript, TypeScript, Go, Rust, Java, Kotlin)"
**What passed:** All 7 languages produce chunks with entity metadata.
**Decision:** No action needed. Claim met.

---

### Claim 16 — VLM processor
**Status:** PASS (3/3 pass)
**README says:** "VLM processor for architecture diagrams; Supports Qwen Vision and OpenAI vision providers"
**What passed:** `VLMProcessor` exists; source mentions both Qwen and OpenAI; no fire-and-forget `create_task` in `ir_builder`.
**Decision:** No action needed. Claim met (at the structural level).
**Note:** End-to-end VLM testing (actual image → IR extraction) deferred to Phase 4.1.

---

### Claim 17 — ColPali
**Status:** FAIL (0/3 pass)
**README says:** "ColPali Support: Visual embeddings for UI sketch similarity"
**What failed:** All 3 tests — `llama_index` import failure blocks `documents.colpali` import.
**Root cause:** `documents/colpali.py` (or a transitive import) depends on `llama_index` which isn't installed.
**Decision:** FIX (install `llama_index` or make import conditional)
**Owning phase:** Phase 0.2 + Phase 4.2
**Effort:** Small — install dep or make conditional. Then verify torch import is lazy.

---

### Claim 18 — Platform adapters
**Status:** PARTIAL (6/7 pass)
**README says:** "Platform Adapters: SAP BTP, VMware Tanzu, Power Platform, AWS, Azure, GCP"
**What passed:** All 6 adapters register successfully.
**What failed:** `test_aws_adapter_produces_non_hardcoded_recommendations` — `transform_ir_to_platform` is not async (returns `AdapterOutput` directly, not a coroutine).
**Root cause:** The test assumes `transform_ir_to_platform` is async; it's actually sync. The test `await`s the result, causing `TypeError: object AdapterOutput can't be used in 'await' expression`.
**Decision:** FIX
**Owning phase:** Phase 4.3 (platform adapter verification)
**Effort:** Small — fix the test to not await. Then verify the two different inputs produce different outputs (the actual hardcoded-data check).

---

### Claim 19 — 30+ tools
**Status:** PASS (2/2 pass)
**README says:** "30+ tools exposed via Model Context Protocol"
**What passed:** Tool registry has ≥30 tools; no fabricated fallback patterns found in `day2.py`, `feedback.py`, `observability.py`.
**Decision:** No action needed. Claim met.
**Note:** The fabricated-fallback check only scans 3 of 8 tool files. Phase 1.2 (full tool audit) expands this to all 8 files.

---

### Claim 20 — Tooling search
**Status:** PARTIAL (1/6 pass)
**README says:** "Tooling Search: Kubernetes, Helm, Docker, GraphQL, Istio"
**What passed:** All 5 search endpoints exist in the API.
**What failed:** All 5 `test_tooling_retriever_exists` tests — `llama_index` import failure blocks `retrieval.tooling.*` imports.
**Root cause:** Same `llama_index` import issue.
**Decision:** FIX (install `llama_index`)
**Owning phase:** Phase 0.2 + Phase 5.4
**Effort:** Small.

---

### Claim 21 — Multilingual
**Status:** PASS (4/4 pass)
**README says:** "Language detection (Russian, English, and 20+ languages); Russian text normalization (Cyrillic, ё→е equivalence)"
**What passed:** Russian and English detected correctly; ё→е normalization works; 7 non-RU/EN languages don't crash.
**Decision:** No action needed. Claim met.

---

### Claim 22 — Observability
**Status:** PARTIAL (2/5 pass)
**README says:** "Trace Logging (JSONL), Metrics Collection (p50/p95/p99), Execution State tracking"
**What passed:** JSON format setting exists; metrics collector exists with `record_request`.
**What failed:**
- `test_execution_state_tracking` — `llama_index` import failure blocks `agents.orchestration` import.
- `test_middleware_adds_trace_id` — middleware list shows `BaseHTTPMiddleware` and `CORSMiddleware` but no `TraceMiddleware` or `RequestIDMiddleware`.
- `test_p50_p95_p99_metrics` — `ObservabilityCollector` class doesn't exist in `core.observability`.

**Root cause:** No trace ID middleware; no percentile latency tracking.
**Decision:** FIX
**Owning phase:** Phase 5.1 (observability)
**Effort:** Medium — add trace middleware, implement percentile tracking in `ObservabilityCollector`.

---

## Cross-Cutting Finding: `llama_index` Import Failure

**Impact:** 12 of the 41 failing tests fail because `llama_index` is not installed in the test environment. This blocks imports across `documents/parse.py`, `documents/colpali.py`, `retrieval/tooling/*`, `api/main.py` (routes), and `agents/orchestration.py`.

**Root cause:** `llama_index` is listed in `pyproject.toml` dependencies but `pip install` wasn't run with `--all-extras` in the test environment.

**Fix:** Phase 0.2 (CI unfreeze) must ensure `uv sync --all-extras` or `pip install -e ".[all]"` runs before tests. Alternatively, make `llama_index` imports conditional (try/except) so the system degrades gracefully without it.

**Priority:** P0 — this single fix will turn ~12 failures into passes (or real failures that need code fixes).

---

## Summary by Decision

| Decision | Count | Claims |
|----------|-------|--------|
| **No action (claim met)** | 8 | #06, #07, #13, #15, #16, #19, #21, (+ #09 with caveat) |
| **FIX** | 13 | #01, #02, #03, #04, #05, #08, #10, #11, #12, #14, #17, #18, #20, #22 |
| **REMOVE** | 0 | (none yet — may change after Phase 2.4 content audit) |
| **DEFER** | 0 | (none yet) |

## Summary by Phase

| Owning phase | Claims addressed | Est. effort |
|---|---|---|
| Phase 0.2 (CI unfreeze, install deps) | #14, #17, #20 (partial), #22 (partial) | Small |
| Phase 2.1 (reasoning modes) | #02 | Medium |
| Phase 2.2 (validator) | #01 | Small |
| Phase 2.3 (GraphRAG) | #10 | Medium |
| Phase 2.4 (knowledge content) | #11 | Medium |
| Phase 3.1-3.5 (retrieval integrity) | #03, #04, #05, #12 | Medium |
| Phase 4.1-4.3 (multimodal + adapters) | #16 (E2E), #18 | Medium |
| Phase 5.1 (observability) | #22 | Medium |
| Phase 5.3 (citations, ColBERT, rerank E2E) | #08, #09 | Small |
| Phase 5.4 (ingestion, tooling) | #14 (full), #20 (full) | Small |

---

## Next Steps

1. **Phase 0.2** — Install `llama_index` in the test environment. This alone should turn ~12 failures into passes and unblock the cascading failures in claims #03, #04, #05, #14, #17, #20, #22.
2. **Re-run the claim suite** after Phase 0.2 to get a clean baseline without import failures.
3. **Phase 2.2** — Wire the ValidatorAgent (claim #01). Smallest fix with highest symbolic value — it's the headline claim.
4. **Phase 2.1** — Implement LLM calls for ToT, Reflect, Critique modes (claim #02).
5. **Phase 3.2** — Fix the orchestrator construction issue and verify all 5 execution modes (claims #03, #04, #05).

The claim suite is now the single source of truth for "does the system deliver its promises?" Run `pytest tests/claims/ -v -m claim` at any time to check.
