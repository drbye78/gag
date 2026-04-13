"""
Telemetry Retriever - Logs and metrics retrieval.

Supports Prometheus and Elasticsearch backends
with in-memory fallback.
"""

import os
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx


class TelemetryBackend(ABC):
    @abstractmethod
    async def search_events(
        self,
        query: str,
        service: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def search_metrics(
        self,
        metric_name: Optional[str] = None,
        service: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        pass


class PrometheusBackend(TelemetryBackend):
    def __init__(self, url: Optional[str] = None):
        self.url = url or os.getenv("PROMETHEUS_URL", "http://localhost:9090")
        self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def _query(self, query: str) -> List[Dict[str, Any]]:
        try:
            client = self._get_client()
            resp = await client.get(f"{self.url}/api/v1/query", params={"query": query})
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != "success":
                return []
            return [
                {"metric": r.get("metric", {}), "value": r.get("value", [None, 0])[1]}
                for r in data.get("data", {}).get("result", [])
            ]
        except Exception:
            return []

    async def search_events(
        self,
        query: str,
        service: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        results = await self._query(
            f'alerts{{service="{service}"}}' if service else "alerts"
        )
        return [
            {
                "id": r.get("metric", {}).get("alertname", ""),
                "event_type": "alert",
                "service": r.get("metric", {}).get("service", ""),
                "severity": r.get("metric", {}).get("severity", "info"),
                "message": r.get("metric", {}).get("alertname", ""),
                "timestamp": datetime.utcnow().isoformat(),
            }
            for r in results[:limit]
        ]

    async def search_metrics(
        self,
        metric_name: Optional[str] = None,
        service: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        promql = metric_name or (f"{service}_" if service else "up")
        results = await self._query(promql)
        return [
            {
                "id": r.get("metric", {}).get("__name__", metric_name or "unknown"),
                "metric_name": r.get("metric", {}).get(
                    "__name__", metric_name or "unknown"
                ),
                "service": r.get("metric", {}).get("job", ""),
                "value": r.get("value", 0),
                "unit": "",
                "timestamp": datetime.utcnow().isoformat(),
            }
            for r in results[:limit]
        ]


class ElasticSearchBackend(TelemetryBackend):
    def __init__(self, url: Optional[str] = None, index: str = "logs-*"):
        self.url = url or os.getenv("ELASTIC_URL", "http://localhost:9200")
        self.index = index
        self.username = os.getenv("ELASTIC_USER", "")
        self.password = os.getenv("ELASTIC_PASS", "")
        self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            auth = (self.username, self.password) if self.username else None
            self._client = httpx.AsyncClient(auth=auth, timeout=30.0)
        return self._client

    async def search_events(
        self,
        query: str,
        service: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        must = []
        if query:
            must.append({"match": {"message": query}})
        if service:
            must.append({"match": {"service": service}})
        if severity:
            must.append({"match": {"severity": severity}})
        body = {
            "query": {"bool": {"must": must}} if must else {"match_all": {}},
            "size": limit,
            "sort": [{"@timestamp": "desc"}],
        }
        try:
            client = self._get_client()
            resp = await client.post(f"{self.url}/{self.index}/_search", json=body)
            resp.raise_for_status()
            data = resp.json()
            return [
                {
                    "id": hit["_id"],
                    "event_type": "log",
                    "service": hit["_source"].get("service", ""),
                    "severity": hit["_source"].get("level", "info"),
                    "message": hit["_source"].get("message", ""),
                    "timestamp": hit["_source"].get(
                        "@timestamp", datetime.utcnow().isoformat()
                    ),
                }
                for hit in data.get("hits", {}).get("hits", [])
            ]
        except Exception:
            return []

    async def search_metrics(
        self,
        metric_name: Optional[str] = None,
        service: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        return []


class InMemoryTelemetryBackend(TelemetryBackend):
    def __init__(self):
        self._events = []
        self._metrics = []
        self._add_defaults()

    def _add_defaults(self):
        self._events = [
            {
                "id": "e001",
                "event_type": "request",
                "service": "api",
                "severity": "info",
                "message": "GET /api/users - 200",
                "timestamp": datetime.utcnow().isoformat(),
            },
            {
                "id": "e002",
                "event_type": "error",
                "service": "api",
                "severity": "error",
                "message": "Connection timeout",
                "timestamp": datetime.utcnow().isoformat(),
            },
        ]
        self._metrics = [
            {
                "id": "m001",
                "metric_name": "cpu_usage",
                "service": "api",
                "value": 45.2,
                "unit": "percent",
                "timestamp": datetime.utcnow().isoformat(),
            },
            {
                "id": "m002",
                "metric_name": "memory_usage",
                "service": "api",
                "value": 512.0,
                "unit": "MB",
                "timestamp": datetime.utcnow().isoformat(),
            },
        ]

    def add_event(self, event: Dict[str, Any]) -> None:
        self._events.append(event)

    def add_metric(self, metric: Dict[str, Any]) -> None:
        self._metrics.append(metric)

    async def search_events(
        self,
        query: str,
        service: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        results = []
        query_lower = query.lower() if query else ""
        for event in self._events:
            if query_lower and query_lower not in event.get("message", "").lower():
                continue
            if service and event.get("service") != service:
                continue
            if severity and event.get("severity") != severity:
                continue
            results.append(event)
        return results[:limit]

    async def search_metrics(
        self,
        metric_name: Optional[str] = None,
        service: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        results = []
        for metric in self._metrics:
            if metric_name and metric.get("metric_name") != metric_name:
                continue
            if service and metric.get("service") != service:
                continue
            results.append(metric)
        return results[:limit]


class TelemetryRetriever:
    def __init__(self, backend: Optional[TelemetryBackend] = None):
        self.backend = backend or self._create_backend()

    @staticmethod
    def _create_backend() -> TelemetryBackend:
        backend_type = os.getenv("TELEMETRY_BACKEND", "").lower()
        if backend_type == "prometheus":
            return PrometheusBackend()
        elif backend_type == "elasticsearch":
            return ElasticSearchBackend()
        else:
            return InMemoryTelemetryBackend()

    async def search_events(
        self,
        query: str,
        service: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)
        results = await self.backend.search_events(query, service, severity, limit)
        return {
            "source": "telemetry",
            "query": query,
            "results": results,
            "total": len(results),
            "took_ms": int(time.time() * 1000) - start,
        }

    async def search_metrics(
        self,
        metric_name: Optional[str] = None,
        service: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)
        results = await self.backend.search_metrics(metric_name, service, limit)
        return {
            "source": "telemetry_metrics",
            "results": results,
            "total": len(results),
            "took_ms": int(time.time() * 1000) - start,
        }


def get_telemetry_retriever() -> TelemetryRetriever:
    return TelemetryRetriever()
