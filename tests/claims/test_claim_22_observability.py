"""
README claim: "Trace Logging: JSONL format with trace_id per request;
Metrics Collection: Latency (p50/p95/p99), errors, counters;
Execution State: Step-by-step tracking with reasoning traces"
Source: README.md lines 134-136
"""
import pytest


@pytest.mark.claim
def test_trace_logging_jsonl_format():
    from core.config import get_settings
    settings = get_settings()
    assert hasattr(settings, "json_format"), "json_format setting missing"
    assert settings.json_format is True, "JSON format should be enabled by default"


@pytest.mark.claim
def test_metrics_collection_exists():
    from core.metrics import get_metrics
    metrics = get_metrics()
    assert metrics is not None, "Metrics collector not found"
    assert hasattr(metrics, "record_request"), "Metrics must have record_request method"


@pytest.mark.claim
def test_execution_state_tracking():
    from agents.orchestration import ExecutionState, StepStatus
    from agents.planner import ExecutionStep

    step = ExecutionStep(step_type="retrieve", action="search", source="docs")
    state = ExecutionState(step=step)
    assert state.status == StepStatus.PENDING
    assert state.started_at is None
    assert state.completed_at is None
    assert state.retry_count == 0
    assert state.reasoning_trace == []


@pytest.mark.claim
def test_middleware_adds_trace_id():
    from api.main import app
    middleware_types = [m.cls.__name__ for m in app.user_middleware]
    has_trace = any("Trace" in name or "RequestID" in name for name in middleware_types)
    assert has_trace, f"Trace/RequestID middleware not found: {middleware_types}"


@pytest.mark.claim
def test_p50_p95_p99_metrics():
    from core.observability import ObservabilityCollector
    collector = ObservabilityCollector()
    for ms in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        collector.record_latency("test_op", ms)
    metrics = collector.get_metrics()
    metrics_str = str(metrics)
    has_percentiles = "p50" in metrics_str or "p95" in metrics_str or "p99" in metrics_str
    assert has_percentiles, "Metrics do not include p50/p95/p99 latency"
