"""Prometheus metrics collection for observability.

This module provides Prometheus-compatible metrics using prometheus_client.
It exposes counters, histograms, and gauges for request latency, retrieval latency,
LLM calls, and token usage.
"""

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

# Request metrics
REQUEST_LATENCY = Histogram(
    "request_latency_seconds",
    "Request latency in seconds",
    ["method", "path", "status"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
)

REQUESTS_TOTAL = Counter(
    "requests_total",
    "Total number of requests",
    ["method", "path", "status"],
)

ERRORS_TOTAL = Counter(
    "errors_total",
    "Total number of errors",
    ["method", "path", "error_type"],
)

# Retrieval metrics
RETRIEVAL_LATENCY = Histogram(
    "retrieval_latency_seconds",
    "Retrieval latency in seconds",
    ["source"],
)

RETRIEVAL_COUNT = Counter(
    "retrieval_count_total",
    "Total number of retrieval operations",
    ["source"],
)

# LLM metrics
LLM_CALLS_TOTAL = Counter(
    "llm_calls_total",
    "Total number of LLM calls",
    ["model", "status"],
)

LLM_LATENCY = Histogram(
    "llm_latency_seconds",
    "LLM call latency in seconds",
    ["model"],
    buckets=(0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, 15.0, 30.0, 60.0),
)

TOKENS_USED = Counter(
    "tokens_used_total",
    "Total number of tokens used",
    ["model", "token_type"],
)

# Active connections gauge
ACTIVE_REQUESTS = Gauge(
    "active_requests",
    "Number of active requests",
)


def record_request(method: str, path: str, status: int, latency_seconds: float) -> None:
    """Record request metrics."""
    REQUEST_LATENCY.labels(method=method, path=path, status=status).observe(latency_seconds)
    REQUESTS_TOTAL.labels(method=method, path=path, status=status).inc()


def record_error(method: str, path: str, error_type: str) -> None:
    """Record error metrics."""
    ERRORS_TOTAL.labels(method=method, path=path, error_type=error_type).inc()


def record_retrieval(source: str, latency_seconds: float, count: int = 1) -> None:
    """Record retrieval metrics."""
    RETRIEVAL_LATENCY.labels(source=source).observe(latency_seconds)
    RETRIEVAL_COUNT.labels(source=source).inc(count)


def record_llm(model: str, latency_seconds: float, tokens: int, status: str = "success") -> None:
    """Record LLM call metrics."""
    LLM_CALLS_TOTAL.labels(model=model, status=status).inc()
    LLM_LATENCY.labels(model=model).observe(latency_seconds)
    TOKENS_USED.labels(model=model, token_type="prompt").inc(tokens // 2)  # Approximate
    TOKENS_USED.labels(model=model, token_type="completion").inc(tokens // 2)  # Approximate


def increment_active_requests(delta: int = 1) -> None:
    """Increment or decrement active requests gauge."""
    ACTIVE_REQUESTS.inc(delta) if delta > 0 else ACTIVE_REQUESTS.dec(abs(delta))


def get_metrics() -> bytes:
    """Generate Prometheus metrics in text format."""
    return generate_latest()


def get_content_type() -> str:
    """Get the content type for Prometheus metrics."""
    return CONTENT_TYPE_LATEST


__all__ = [
    "record_request",
    "record_error",
    "record_retrieval",
    "record_llm",
    "increment_active_requests",
    "get_metrics",
    "get_content_type",
]
