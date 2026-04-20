# Production Improvement Plan

## Overview
This document tracks improvements to address all identified production-readiness concerns.

## Phase 1: Core Infrastructure (Critical)

### 1.1 Pydantic Settings with Secrets Management
**Status**: Pending
**Priority**: Critical
**Files**: `core/config.py`

Current state: Uses plain `os.getenv()` throughout - no validation, no secrets handling, no type safety.

Target state:
```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Secrets - properly encrypted
    jwt_secret: SecretStr = Field(default="change-me-in-production")
    credential_encrypt_key: SecretStr = Field(default="")
    
    # Validated fields
    api_port: int = Field(default=8000, ge=1, le=65535)
    rate_limit_requests: int = Field(default=100, ge=1)
```

### 1.2 Dependency Injection Adoption
**Status**: Partial (exists but unused)
**Priority**: Critical
**Files**: `core/di.py`, `tools/base.py`, `agents/orchestration.py`

Current state: Global singletons (`get_tool_registry()`, `_catalog`, etc.) - hard to test, not multi-tenant ready.

Target state: All singletons accessible via DI container with override capability for testing:
```python
# Testing with override
container.override_for_testing("tool_registry", mock_registry)

# Multi-tenant
async with container.scoped("tenant-123"):
    registry = resolve("tool_registry")  # tenant-specific
```

### 1.3 Robust Error Handling
**Status**: Pending
**Priority**: High
**Files**: `agents/orchestration.py`, various

Current state: Broad `except Exception: pass` loses error context.

Target state: Specific exception hierarchy and proper logging:
```python
class OrchestrationError(Exception): ...
class RetrievalError(OrchestrationError): ...
class ReasoningError(OrchestrationError): ...
class ToolExecutionError(OrchestrationError): ...
```

---

## Phase 2: Orchestration Improvements

### 2.1 IR-First Execution Model
**Status**: Pending
**Priority**: Critical
**Files**: `agents/orchestration.py`, `models/ir.py`

Current state: IR passes through unmodified; agents reason on raw text.

Target state: IR becomes the primary execution context:
```python
# Step 1: Build IR from input
ir = ir_builder.build(query, sources)

# Step 2: All reasoning operates on IR structure
context["ir_context"] = ir  # structured, deterministic

# Step 3: Validation at each step
if not ir.is_complete:
    # Auto-complete via constraint engine
    ir = constraint_engine.enrich(ir)
```

### 2.2 Dynamic Tool Selection
**Status**: Partial
**Priority**: High
**Files**: `agents/planner.py`

Current state: Static planning with fixed sequence.

Target state: Context-aware tool selection:
```python
# Planner decides tools dynamically based on:
# - query complexity
# - available IR completeness
# - runtime constraints
plan = await planner.plan(query, ir_context, constraints)
```

---

## Phase 3: Observability

### 3.1 OpenTelemetry Integration
**Status**: Partial
**Priority**: Medium
**Files**: Multiple

Current state: Basic trace logging via `trace_id`.

Target state: Full OTel integration:
```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider

# Automatic instrumentation
# Span attributes from execution context
# Metrics via prometheus_endpoint
```

### 3.2 Rate Limiting Middleware
**Status**: Configured but incomplete
**Priority**: Medium
**Files**: `api/main.py`

Current state: Config exists but full limit Redis backend not visible.

Target state: Token bucket algorithm with Redis backend.

---

## Phase 4: Data & Schema

### 4.1 FalkorDB Schema Documentation
**Status**: Pending
**Priority**: Medium
**Files**: `graph/client.py`

Current state: Schema implicit in code.

Target state: Explicit schema with migration tracking:
```markdown
# FalkorDB Schema

## NodeTypes
- COMPONENT: "id, name, type, description, metadata"
- SERVICE: "id, name, platform, endpoints"
- PATTERN: "id, name, domain, confidence"

## EdgeTypes
- IMPLEMENTS: "COMPONENT → PATTERN"
- DEPENDS_ON: "SERVICE → SERVICE"
...
```

---

## Phase 5: Dependency Management

### 5.1 Replace Dynamic Imports
**Status**: Pending
**Priority**: High
**Files**: `retrieval/rerank/providers.py`, `api/main.py`

Current state: `try/except ImportError` fragile patterns.

Target state: Explicit optional dependency handling:
```python
# Option 1: Extra-based
optional_dependencies = {
    "cohere": ["cohere>=5.0.0"],
    "jina": ["jina>=3.0.0"],
}

# Option 2: Pluggy
class RerankerRegistry:
    def get(self, provider: str):
        if provider not in self.available:
            raise DependencyNotFoundError(f"{provider} not installed")
        return self._rerankers[provider]
```

---

## Implementation Priority

| Priority | Item | Estimated Effort |
|----------|------|------------------|
| 1 | Pydantic Settings | 2 days |
| 2 | DI Container Adoption | 1 day |
| 3 | Error Handling | 0.5 day |
| 4 | IR-First Orchestration | 2 days |
| 5 | Dynamic Tool Selection | 1 day |
| 6 | OTel Integration | 2 days |
| 7 | Rate Limiting | 1 day |
| 8 | FalkorDB Schema | 0.5 day |
| 9 | Dependency Patterns | 1 day |

**Total Estimated**: ~11 days of concentrated work

---

## Success Criteria

- [ ] All config fields have type validation and secrets properly handled
- [ ] All global singletons can be overridden for testing
- [ ] No broad `except Exception` without logging
- [ ] IR is primary execution context, not pass-through
- [ ] Tool selection is dynamic based on context
- [ ] Full OTel traces and metrics available
- [ ] Rate limiting works with Redis backend
- [ ] FalkorDB schema documented with migrations
- [ ] Dynamic imports use proper patterns
- [ ] All 356 tests still passing