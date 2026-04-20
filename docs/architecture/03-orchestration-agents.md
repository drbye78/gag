# Orchestration & Agents Architecture

The orchestration engine coordinates a multi-agent system for complex query resolution. This document covers the agent types, execution flows, and integration points.

## Overview

```
Query → Plan → Retrieve → Reason → Execute → Validate → Response
                     ↑              ↓
                   Retry (if failed)
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
| `CHAIN_OF_THOUGHT` | Step-by-step reasoning |
| `TREE_OF_THOUGHTS` | Multiple perspectives |
| `REFLECT` | Self-evaluation |
| `CRITIQUE` | Risk assessment |
| `DIRECT` | Direct answer |

### 4. ToolExecutor (`agents/executor.py`)

**Responsibility**: Tool execution pipeline

| Function | Description |
|----------|-------------|
| `execute()` | Run selected tools |
| `execute_parallel()` | Concurrent tool execution |
| `execute_sequential()` | Sequential tool execution |

### 5. ValidatorAgent (`agents/validator.py`)

**Responsibility**: Response validation

| Validation | Description |
|------------|-------------|
| `ACCURACY` | Response matches retrieved context |
| `COHERENCE` | Reasoning chain is consistent |
| `COMPLETENESS` | All query aspects addressed |
| `CONFIDENCE` | Score based on coverage |
| `SAFETY` | No dangerous patterns |

## Main Orchestration Engine (`agents/orchestration.py`)

### OrchestrationEngine

```python
class OrchestrationEngine:
    def __init__(
        self,
        max_iterations: int = 3,
        max_retries: int = 2,
        parallel_execution: bool = True
    ):
        self.planner = PlannerAgent()
        self.retriever = RetrievalAgent()
        self.reasoner = ReasoningAgent()
        self.executor = ToolExecutor()
```

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

The agent system has access to 30+ MCP tools:

| Category | Tools |
|----------|-------|
| Code Analysis | find_callers, find_callees, dead_code, complexity |
| Infrastructure | search_kubernetes, search_helm, search_dockerfile |
| Reasoning | chain_of_thoughts, tree_of_thoughts |
| Validation | architecture_evaluate, security_validate, cost_estimate |