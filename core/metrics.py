"""Metrics collection for observability."""

import time
from typing import Any, Dict, Optional

from collections import defaultdict
from dataclasses import dataclass


@dataclass
class Metric:
    name: str
    value: float
    labels: Dict[str, str]
    timestamp: float


class MetricsCollector:
    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, list] = defaultdict(list)
        self._start_time = time.time()

    def increment(
        self, name: str, value: float = 1, labels: Optional[Dict[str, str]] = None
    ) -> None:
        key = self._make_key(name, labels)
        self._counters[key] += value

    def gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        key = self._make_key(name, labels)
        self._gauges[key] = value

    def histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        key = self._make_key(name, labels)
        self._histograms[key].append(value)
        if len(self._histograms[key]) > 1000:
            self._histograms[key] = self._histograms[key][-1000:]

    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_counter(self, name: str) -> float:
        return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> Optional[float]:
        return self._gauges.get(name)

    def get_histogram(self, name: str) -> Dict[str, float]:
        values = self._histograms.get(name, [])
        if not values:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}
        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }

    def get_all(self) -> Dict[str, Any]:
        return {
            "uptime": time.time() - self._start_time,
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {k: self.get_histogram(k) for k in self._histograms},
        }

    def reset(self) -> None:
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()


_metrics: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


def observe_request(method: str, path: str, status: int, duration: float) -> None:
    m = get_metrics()
    m.increment(
        "http_requests_total",
        1,
        {"method": method, "path": path, "status": str(status)},
    )
    m.histogram(
        "http_request_duration_seconds", duration, {"method": method, "path": path}
    )


def observe_retrieval(source: str, duration: float, count: int) -> None:
    m = get_metrics()
    m.increment(f"retrieval_{source}_total", count)
    m.histogram(f"retrieval_{source}_duration_seconds", duration)


def observe_llm(duration: float, model: str, tokens: int) -> None:
    m = get_metrics()
    m.increment("llm_requests_total", 1, {"model": model})
    m.histogram("llm_request_duration_seconds", duration, {"model": model})
    m.increment("llm_tokens_total", tokens, {"model": model})
