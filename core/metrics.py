"""Metrics collection for observability.

This module is deprecated. Use core.observability.MetricsCollector instead.
This file exists for backward compatibility and re-exports from observability.
"""

from core.observability import MetricsCollector as _MetricsCollector

_metrics_collector: _MetricsCollector | None = None


def get_metrics() -> _MetricsCollector:
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = _MetricsCollector()
    return _metrics_collector


def observe_request(method: str, path: str, status: int, duration: float) -> None:
    """Deprecated: Use observability tracing instead."""
    pass


def observe_retrieval(source: str, duration: float, count: int) -> None:
    """Deprecated: Use observability tracing instead."""
    pass


def observe_llm(duration: float, model: str, tokens: int) -> None:
    """Deprecated: Use observability tracing instead."""
    pass