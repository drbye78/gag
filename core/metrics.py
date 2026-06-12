"""Metrics collection for observability.

.. deprecated::
    Use :mod:`core.observability` directly instead.  This module is
    kept solely as a thin re-export shim for existing import sites and
    will be removed in a future release.
"""

import warnings

warnings.warn(
    "core.metrics is deprecated — import from core.observability instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.observability import MetricsCollector as _MetricsCollector
from core.observability import get_metrics_collector as _get_metrics_collector


def get_metrics() -> _MetricsCollector:
    """Return the same MetricsCollector singleton used by observability."""
    return _get_metrics_collector()


def observe_request(method: str, path: str, status: int, duration: float) -> None:
    """Record request metrics via the metrics collector."""
    collector = get_metrics()
    collector.record_request(method, path, status, duration)


def observe_retrieval(source: str, duration: float, count: int) -> None:
    """Record retrieval metrics via the metrics collector."""
    collector = get_metrics()
    collector.record_retrieval(source, duration, count)


def observe_llm(duration: float, model: str, tokens: int) -> None:
    """Record LLM metrics via the metrics collector."""
    collector = get_metrics()
    collector.record_llm(duration, model, tokens)
