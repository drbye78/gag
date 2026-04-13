# Agent System Documentation

The SAP BTP Engineering Intelligence System uses a multi-agent architecture with specialized agents working together to process queries, retrieve information, and generate responses.

## Agent Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│              OrchestrationEngine                           │
│                                                             │
│   ┌──────────────────────────────────────────────────────┐  │
│   │  Loop: Plan → Retrieve → Reason → Tool → Revise    │  │
│   │  (up to max_iterations)                             │  │
│   └──────────────────────────────────────────────────────┘  │
│                          │                               │
│         ┌────────────────┼────────────────┐               │
│         ▼              ▼              ▼               │
│   ┌───────────┐ ┌──────────────┐ ┌───────────────┐     │
│   │ Planner  │ │ Retrieval   │ │ Reasoning     │     │
│   │  Agent   │ │  Agent     │ │   Agent       │     │
│   └─────┬─────┘ └──────┬─────┘ └──────┬──────┘     │
│         │               │              │              │
│         ▼               ▼              ▼              │
│   ┌─────────────────────────────────────────────┐   │
│   │         ToolExecutor                        │   │
│   └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## Agent Responsibilities

| Agent | Responsibility | Key Methods |
|-------|-----------------|-------------|
| **Planner** | Intent detection, plan generation | `plan()`, `_detect_intent()`, `_identify_sources()` |
| **Retrieval** | Multi-source data retrieval | `execute_plan()`, `_execute_parallel()`, `_select_strategy()` |
| **Reasoning** | Answer synthesis via LLM | `generate_answer()`, `_build_prompt()` |
| **Executor** | Tool execution with retry logic | `execute()`, `execute_parallel()`, `execute_pipeline()` |
| **Orchestrator** | Overall flow control | `execute()`, `_execute_steps()` |

## 1. PlannerAgent

The PlannerAgent analyzes the user's query and creates an execution plan.

### Intent Detection

```python
INTENT_KEYWORDS = {
    Intent.DESIGN: ["design", "create", "build", "architect", "propose"],
    Intent.EXPLAIN: ["explain", "what", "how", "describe", "tell"],
    Intent.TROUBLESHOOT: ["error", "fail", "issue", "bug", "broken", "fix"],
    Intent.OPTIMIZE: ["improve", "optimize", "performance", "faster"],
}
```

### Plan Generation

| Intent | Generated Steps |
|--------|-----------------|
| DESIGN | analyze_ir → retrieve(docs, code) �� tool_calls → generate_architecture |
| EXPLAIN | retrieve(all sources) → tool_calls → generate_answer |
| TROUBLESHOOT | retrieve(tickets, telemetry) → analyze_logs → tool_calls → diagnose |
| OPTIMIZE | retrieve(code, telemetry) → analyze_logs → tool_calls → optimize |

### Source Identification

```python
SOURCE_KEYWORDS = {
    "docs": ["doc", "document", "readme", "guide", "sap", "btp"],
    "code": ["code", "function", "class", "implement", "api"],
    "graph": ["architecture", "component", "service", "deploy"],
    "tickets": ["issue", "bug", "ticket", "incident"],
    "telemetry": ["metric", "log", "performance", "monitor"],
}
```

### Usage

```python
planner = get_planner_agent()

# Build plan from query
plan = await planner.plan(
    "How do I implement OAuth2 in SAP CAP?",
    ir_context={"current_architecture": {...}}
)

# Get retrieval queries for each source
queries = planner.get_retrieval_queries("SAP BTP authentication")
# Returns: {"docs_queries": [...], "code_queries": [...], ...}
```

## 2. RetrievalAgent

The RetrievalAgent executes retrieval steps using various strategies.

### Retrieval Strategies

| Strategy | When to Use | Behavior |
|----------|-------------|----------|
| `PARALLEL` | Design tasks | All sources simultaneously |
| `SEQUENTIAL` | Troubleshooting | Logs first, then details |
| `CASCADE` | General | Stop when results found |
| `ADAPTIVE` | Default | Auto-select based on intent |

### Strategy Selection Logic

```python
def _select_strategy(self, intent):
    if intent == "troubleshoot":
        return RetrievalStrategy.SEQUENTIAL  # Logs first
    elif intent == "design":
        return RetrievalStrategy.PARALLEL   # All sources
    else:
        return RetrievalStrategy.CASCADE  # Efficient
```

### Caching

The RetrievalAgent includes a TTL-based cache:

```python
class RetrievalCache:
    def __init__(self, ttl_seconds=300):
        self._cache = {}
        self._ttl = ttl_seconds
    
    def get(self, query, source) -> Optional[RetrievalResult]
    def set(self, query, source, result)
    @property
    def hit_rate(self) -> float  # Cache efficiency
```

### Usage

```python
retrieval = get_retrieval_agent()

# Execute plan
results = await retrieval.execute_plan(plan, "SAP CAP authorization")

# Retrieve single source
result = await retrieval.retrieve_single(
    query="OAuth2 implementation",
    source="code",
    limit=10
)
```

### Metrics

```python
await retrieval.get_metrics()
# Returns:
# {
#     "total_queries": 100,
#     "cache_hit_rate": 0.35,
#     "cache_hits": 35,
#     "cache_misses": 65,
#     "avg_latency_ms": 230
# }
```

## 3. ReasoningAgent

The ReasoningAgent synthesizes answers using retrieved context.

### Reasoning Modes

| Mode | Description | Prompt Instruction |
|------|-------------|-------------------|
| `DIRECT` | Plain answer | None |
| `CHAIN_OF_THOUGHT` | Step-by-step | Think step by step: 1) What... 2) What context... |
| `TREE_OF_THOUGHTS` | Multiple perspectives | Explore architect/dev/support views |
| `CRITIQUE` | Draft + evaluate | Draft answer, then evaluate correctness |

### Prompt Building

```python
def _build_prompt(self, query, context, intent):
    base_prompt = f"Query: {query}\n\nContext:\n{self._format_context(context)}"
    
    if self.mode == ReasonMode.CHAIN_OF_THOUGHT:
        base_prompt += "Think step by step:\n1. What is being asked?"
    elif self.mode == ReasonMode.CRITIQUE:
        base_prompt += "After your answer, briefly evaluate correctness."
    
    return base_prompt
```

### Usage

```python
reasoner = get_reasoning_agent()

# Generate answer
answer = await reasoner.generate_answer(
    query="How to implement JWT in SAP CAP?",
    retrieved_data={
        "results": [
            {"source": "docs", "results": [...]},
            {"source": "code", "results": [...]}
        ]
    },
    tool_results=[{"tool": "security_validate", "output": {...}}],
    intent="explain"
)
```

## 4. ToolExecutor

The ToolExecutor runs validation and evaluation tools.

### Execution Modes

```python
# Parallel - all tools at once
results = await executor.execute_parallel(
    tools=["architecture_evaluate", "security_validate"],
    args={"architecture_id": "test"}
)

# Sequential - stop on failure
results = await executor.execute_sequential(
    tools=["architecture_evaluate", "security_validate"],
    args={"architecture_id": "test"},
    fail_fast=True
)

# Pipeline - with continue/stop on failure
pipeline = ToolPipeline(
    tools=["architecture_evaluate", "security_validate"],
    args={"architecture_id": "test"},
    on_failure="continue"  # or "stop"
)
results = await executor.execute_pipeline(pipeline)
```

### Tool Result Tracking

```python
@dataclass
class ToolResult:
    tool: str
    status: ToolStatus  # PENDING, RUNNING, COMPLETED, FAILED
    output: Any
    error: Optional[str]
    took_ms: int
    retries: int
```

### Metrics

```python
await executor.get_metrics()
# Returns:
# {
#     "total_executions": 50,
#     "successful": 45,
#     "failed": 5,
#     "retries": 3,
#     "success_rate": 0.9,
#     "avg_time_ms": 150
# }
```

## 5. OrchestrationEngine

The OrchestrationEngine coordinates all agents in an iterative loop.

### Execution Loop

```python
async def execute(self, query, ir_context):
    # 1. Plan
    plan = await self.planner.plan(query, ir_context)
    
    context = {"query": query, "ir_context": ir_context}
    
    # 2. Iterate (max_iterations times)
    for iteration range(self.max_iterations):
        # Execute steps
        states = await self._execute_steps(plan, context)
        
        # Aggregate results
        context["retrieval_results"] = aggregate(states)
        
        # Check if revision needed
        if not await self._revision_needed(states):
            break
        
        # Re-plan if needed
        plan = await self.planner.plan(query, context)
    
    # 3. Generate final answer
    answer = await self.reasoner.generate_answer(query, context)
    
    return {
        "query": query,
        "answer": answer,
        "plan": plan.to_dict(),
        "metrics": self.metrics
    }
```

### Step Execution

```python
async def _execute_steps(self, plan, context):
    if self.parallel_execution:
        # All steps at once
        tasks = [self._execute_step(s, context) for s in plan.steps]
        return await asyncio.gather(*tasks)
    else:
        # Sequential with state update
        states = []
        for step in plan.steps:
            state = await self._execute_step(step, context)
            states.append(state)
            context[f"{step.type}_result"] = state.result
        return states
```

### State Tracking

```python
@dataclass
class ExecutionState:
    step: ExecutionStep
    status: StepStatus  # PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
    result: Any
    error: Optional[str]
    started_at: float
    completed_at: float
    retry_count: int
    
    @property
    def duration_ms(self) -> int
```

### Metrics

```python
await engine.get_metrics()
# Returns:
# {
#     "total_runs": 100,
#     "successful_runs": 92,
#     "failed_runs": 8,
#     "total_steps_executed": 450,
#     "total_retries": 12,
#     "avg_execution_time_ms": 1200
# }
```

## Complete Example

```python
from agents.orchestration import get_orchestration_engine

# Get orchestrator
engine = get_orchestration_engine()

# Execute query
result = await engine.execute(
    query="How do I secure SAP CAP API with OAuth2?",
    ir_context={"current_project": {...}}
)

# Result structure
{
    "query": "How do I secure SAP CAP API with OAuth2?",
    "answer": "To secure your SAP CAP API with OAuth2...",
    "intent": "explain",
    "plan": {
        "query": "How do I secure SAP CAP API with OAuth2?",
        "intent": "explain",
        "steps": [
            {"step_type": "retrieve", "action": "search", "source": "docs", ...},
            {"step_type": "retrieve", "action": "search", "source": "code", ...},
            {"step_type": "reason", "action": "generate_answer"}
        ],
        "current_step": 3,
        "is_complete": True
    },
    "execution": {
        "iterations": 1,
        "steps": [
            {"step": {...}, "status": "completed", "took_ms": 150},
            {"step": {...}, "status": "completed", "took_ms": 200},
            {"step": {...}, "status": "completed", "took_ms": 800}
        ],
        "took_ms": 1150
    },
    "metrics": {
        "total_runs": 1,
        "successful_runs": 1,
        "avg_execution_time_ms": 1150
    }
}
```

## Adding Custom Agents

To add a custom agent:

1. **Create agent class**:
```python
class CustomAgent:
    async def execute(self, context) -> Dict[str, Any]:
        # Implementation
        return {"result": "..."}
```

2. **Register with orchestrator**:
```python
engine.custom_agents["custom"] = CustomAgent()
```

3. **Add step executor**:
```python
STEP_EXECUTORS["custom"] = CustomStepExecutor(custom_agent)
```