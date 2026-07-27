# Orchestration & Agents Architecture

The orchestration engine coordinates a multi-agent system for complex query resolution. This document covers the agent types, execution flows, and integration points.

## Overview

```
Query → Plan → [Retrieve‖Tool] → Analyze → Reason → Validate
                 ↑                                  ↓
           Re-Plan (if score < threshold) ← Issues fed back to planner
                                    ↓ (if score >= threshold)
                                Response
```

## Agent Types

### 1. PlannerAgent (`agents/planner.py`)

**Responsibility**: Intent detection and execution planning

| Function | Description |
|----------|-------------|
| `detect_intent()` | Classifies query into: DESIGN, EXPLAIN, TROUBLESHOOT, OPTIMIZE |
| `identify_sources()` | Auto-detects required retrieval sources |
| `select_tools()` | Identifies required MCP tools |
| `create_plan()` | Builds ExecutionPlan with ExecutionStep objects |

**Intent Detection**:
```python
INTENT_PATTERNS = {
    "design": ["design", "create", "build", "implement", "architecture"],
    "explain": ["what is", "how does", "explain", "describe"],
    "troubleshoot": ["error", "issue", "problem", "bug", "broken"],
    "optimize": ["optimize", "improve", "performance", "faster", "efficient"],
}
```

### 2. RetrievalAgent (`agents/retrieval.py`)

**Responsibility**: Multi-source data retrieval

| Function | Description |
|----------|-------------|
| `retrieve()` | Execute parallel/sequential retrieval |
| `get_sources()` | Get sources from plan |
| `aggregate_results()` | Merge results from all sources |

**Retrieval Strategies**:
- `PARALLEL` - All sources simultaneously
- `SEQUENTIAL` - Sources one-by-one
- `CASCADE` - Stop when enough results
- `ADAPTIVE` - Auto-select based on intent

### 3. ReasoningAgent (`agents/reasoning.py`)

**Responsibility**: LLM-based reasoning over retrieved data

| Mode | Description |
|------|-------------|
| `DIRECT` | Single-call concise answer |
| `CHAIN_OF_THOUGHT` | Step-by-step reasoning with structured prompt |
| `TREE_OF_THOUGHTS` | 3 parallel persona calls (architect, developer, support) → synthesis call (real multi-call) |
| `REFLECT` | 2-pass: initial answer → self-critique of assumptions/omissions → final revised answer |
| `CRITIQUE` | Answer → separate structured evaluation call (correctness, relevance, risks) |

**Streaming**: `generate_answer_streaming()` yields tokens as they arrive via `router.chat(stream=True)`.
**Citations**: When `require_citations=True`, context items are numbered [N] and the LLM cites sources inline. Extracted citations skip the validator's separate LLM faithfulness check.

### 4. ToolExecutor (`agents/executor.py`)

**Responsibility**: Tool execution pipeline

| Function | Description |
|----------|-------------|
| `execute()` | Run selected tools |
| `execute_parallel()` | Concurrent tool execution |
| `execute_sequential()` | Sequential tool execution |

### 5. ValidatorAgent (`agents/validator.py`)

**Responsibility**: Response validation with feedback loop integration

| Validation | Description |
|------------|-------------|
| `ACCURACY` | Response matches retrieved context (coverage guard prevents inflated scores) |
| `COHERENCE` | Reasoning chain is consistent |
| `COMPLETENESS` | All query aspects addressed |
| `CONFIDENCE` | Score based on coverage |
| `SAFETY` | No dangerous patterns |

**Optimizations**: When `citations_present=True` and citations are extracted from the reasoner's output, the validator skips the separate LLM faithfulness check, reducing LLM calls.
**Feedback loop**: Validation scores below the `validation_threshold` (default 0.7) trigger automatic re-planning through the orchestrator.

## Main Orchestration Engine (`agents/orchestration.py`)

### OrchestrationEngine

```python
class OrchestrationEngine:
    def __init__(
        self,
        max_iterations: int = 3,
        max_retries: int = 2,
        parallel_execution: bool = True,
        validation_threshold: float = 0.7,
        require_citations: bool = True,
        redis_url: Optional[str] = None,
    ):
        self.planner = PlannerAgent()
        self.retriever = RetrievalAgent()
        self.reasoner = ReasoningAgent()
        self.executor = ToolExecutor()
        self.validator = ValidatorAgent()
```

**Self-correcting execute() loop**: `Plan → [Retrieve‖Tool] → Analyze → Reason → Validate → Re-Plan if score < validation_threshold`

**Topological sort** (`_compute_tiers()`): Steps declare dependencies via `depends_on` field. `_compute_tiers()` uses Kahn's algorithm to auto-compute execution tiers, replacing the hardcoded tier_map.

**Wave execution** (`_execute_tier()`): Each tier executes in parallel; tiers run sequentially. Results from completed tiers feed into downstream steps.

**State persistence**: `_save_execution_snapshot()` serializes `ExecutionState` to Redis for crash recovery. `resume_execution(trace_id)` restores and continues from the last completed tier.

**Configuration**:
- `validation_threshold` (default 0.7): Minimum score for convergence
- `require_citations` (default True): Inline source citations in reasoning output
- `max_iterations` (default 3): Maximum re-planning iterations

### Execution Modes

| Mode | Behavior |
|------|----------|
| `ITERATIVE` | Default, loop with revision |
| `PARALLEL` | All steps execute simultaneously |
| `SEQUENTIAL` | Steps execute one-by-one |
| `BRANCHING` | Decompose query, execute branches, merge |
| `RECURSIVE` | Execute with sub-query extraction |

## Execution Flow

### Plan → Retrieve → Reason → Execute Loop

```
1. PLAN (PlannerAgent)
   ├─ Detect intent from query
   ├─ Identify sources (docs, code, graph, etc.)
   ├─ Select tools (architecture_evaluate, security_validate)
   └─ Create ExecutionPlan with ExecutionSteps

2. RETRIEVE (RetrievalAgent)
   ├─ Execute parallel/sequential retrieval
   ├─ Aggregate results from all sources
   └─ Cache for reuse

3. EXECUTE (ToolExecutor)
   ├─ Run selected tools
   └─ Refine query based on tool results

4. REASON (ReasoningAgent)
   ├─ Generate final answer using retrieved data
   ├─ Apply reasoning mode (CoT, ToT, etc.)
   └─ Return annotated response

5. VALIDATE (ValidatorAgent)
   ├─ Check accuracy, coherence, completeness
   ├─ Calculate confidence score
   └─ Return ValidationResult

6. REVISION LOOP (if needed)
   ├─ Check if revision needed
   └─ Re-plan if necessary (max iterations = 3)
```

## Retry Logic

```python
for attempt in range(self.max_retries + 1):
    try:
        result = await executor.execute(state, context)
        state.status = StepStatus.COMPLETED
        break
    except Exception as e:
        if attempt < self.max_retries:
            state.retry_count += 1
            await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
        else:
            state.status = StepStatus.FAILED
```

- **Max Retries**: Configurable (default: 2)
- **Backoff**: 0.5s × (attempt + 1)
- **Metrics**: Total retries tracked

## Execution State

```python
@dataclass
class ExecutionState:
    step: ExecutionStep
    status: StepStatus  # PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
    result: Any
    error: Optional[str]
    started_at: Optional[float]
    completed_at: Optional[float]
    retry_count: int
    reasoning_trace: List[ReasoningTraceEntry]
```

## Memory System (`core/memory.py`)

### Three-Tier Architecture

| Tier | Class | Scope | TTL |
|------|-------|-------|-----|
| SHORT_TERM | ShortTermMemory | Session | 1 hour |
| PROJECT | ProjectMemory | Project | Persistent |
| LONG_TERM | LongTermMemory | Global | Persistent (Qdrant) |

### Integration

```python
# At execution start - load context
memory = get_memory_system()
session_context = memory.get_context(max_entries=5)
if session_context:
    context["session_history"] = session_context

# After execution - remember results
memory.remember(
    key=f"execution:{int(start_time)}",
    value={"query": query, "intent": plan.intent},
    tier=MemoryTier.PROJECT,
)
```

## Step Executors

| Executor | Class | Purpose |
|----------|-------|---------|
| retrieve | RetrieveStepExecutor | Multi-source retrieval |
| tool | ToolStepExecutor | Tool execution |
| reason | ReasonStepExecutor | LLM reasoning |
| analyze | AnalyzeStepExecutor | IR/log/architecture analysis |

## Streaming Execution

The engine supports step-by-step progress streaming:

```python
async for event in engine.execute_streaming(query):
    # Events: start → plan → iteration_start → step_complete → plan_revised → complete
```

## Knowledge Processing Pipeline (`core/pipeline.py`)

Integrates platform adapters into orchestration:

```python
class KnowledgeProcessingPipeline:
    async def process(query, platform_context, existing_ir):
        # 1. Extract features from IR and query
        features = self._extract_features(existing_ir, query)

        # 2. Pattern matching
        pattern_results = self.pattern_matcher.match(features)

        # 3. Constraint evaluation
        violations = self.constraint_engine.evaluate(features, platform)

        # 4. Platform adapter transformation
        adapter = self.adapter_registry.get(platform)
        return adapter.transform_ir_to_platform(adapter_input)
```

### UnifiedPipeline

Knowledge-first pipeline that resolves intent first, then transforms to platform-specific output.

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_iterations` | 3 | Max revision loops |
| `max_retries` | 2 | Per-step retry attempts |
| `parallel_execution` | True | Default parallel mode |
| `cache_ttl` | 300 | Retrieval cache TTL (seconds) |

## API Entry Point

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/query` | POST | Main orchestration endpoint |

## MCP Tools Available

The agent system has access to 30+ MCP tools via JSON-RPC 2.0 protocol:

| Category | Tools |
|----------|-------|
| Code Analysis | find_callers, find_callees, dead_code, complexity |
| Infrastructure | search_kubernetes, search_helm, search_dockerfile, search_istio |
| Reasoning | chain_of_thoughts, tree_of_thoughts, iterative_reasoning |
| Validation | architecture_evaluate, security_validate, cost_estimate |
| Search | search, hybrid_search, colpal_search, ui_sketch_search |
| Document | parse_document_advanced, analyze_visual |
| Session | session/get, session/set, notifications/listen |

**Session Management**: MCP supports stateful sessions with get/set methods.
**Rate Limiting**: 100 calls/minute per client with sliding window.