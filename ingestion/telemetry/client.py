import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx


class TelemetrySource(str, Enum):
    PROMETHEUS = "prometheus"
    ELASTICSEARCH = "elasticsearch"
    LOKI = "loki"


@dataclass
class LogEntry:
    timestamp: float
    message: str
    level: str
    service: str
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricPoint:
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)
    source: str = ""


class PrometheusClient:
    def __init__(self, url: Optional[str] = None):
        self.url = url or os.getenv("PROMETHEUS_URL", "http://localhost:9090")
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            username = os.getenv("PROMETHEUS_USER", "")
            password = os.getenv("PROMETHEUS_PASSWORD", "")
            if username:
                self._client = httpx.AsyncClient(
                    auth=(username, password), timeout=30.0
                )
            else:
                self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def query_range(
        self,
        query: str,
        start: float,
        end: float,
        step: str = "1m",
    ) -> List[MetricPoint]:
        try:
            client = self._get_client()
            response = await client.get(
                f"{self.url}/api/v1/query_range",
                params={
                    "query": query,
                    "start": start,
                    "end": end,
                    "step": step,
                },
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        metrics = []
        for result in data.get("data", {}).get("result", []):
            metric_name = result.get("metric", {}).get("__name__", query)
            for value in result.get("values", []):
                metrics.append(
                    MetricPoint(
                        name=metric_name,
                        value=float(value[1]),
                        timestamp=value[0],
                        labels=result.get("metric", {}),
                        source=TelemetrySource.PROMETHEUS.value,
                    )
                )

        return metrics

    async def query(self, query: str) -> List[MetricPoint]:
        try:
            client = self._get_client()
            response = await client.get(
                f"{self.url}/api/v1/query",
                params={"query": query},
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        metrics = []
        for result in data.get("data", {}).get("result", []):
            metric_name = result.get("metric", {}).get("__name__", query)
            value = result.get("value", [])
            metrics.append(
                MetricPoint(
                    name=metric_name,
                    value=float(value[1]),
                    timestamp=value[0],
                    labels=result.get("metric", {}),
                    source=TelemetrySource.PROMETHEUS.value,
                )
            )

        return metrics

    async def label_values(self, label_name: str) -> List[str]:
        try:
            client = self._get_client()
            response = await client.get(
                f"{self.url}/api/v1/label/{label_name}/values",
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        return data.get("data", [])


class ElasticsearchClient:
    def __init__(
        self,
        url: Optional[str] = None,
        index: str = "logs-*",
    ):
        self.url = url or os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
        self.index = index
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            api_key = os.getenv("ELASTIC_API_KEY", "")
            if api_key:
                self._client = httpx.AsyncClient(
                    headers={"Authorization": f"ApiKey {api_key}"},
                    timeout=30.0,
                )
            else:
                self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def search(
        self,
        query: str,
        level: Optional[str] = None,
        service: Optional[str] = None,
        max_results: int = 100,
    ) -> List[LogEntry]:
        must = [{"match": {"message": query}}]
        if level:
            must.append({"term": {"level": level}})
        if service:
            must.append({"term": {"service": service}})

        try:
            client = self._get_client()
            response = await client.get(
                f"{self.url}/{self.index}/_search",
                json={
                    "query": {"bool": {"must": must}},
                    "size": max_results,
                    "sort": [{"@timestamp": "desc"}],
                },
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        logs = []
        for hit in data.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            logs.append(
                LogEntry(
                    timestamp=source.get("@timestamp", time.time()),
                    message=source.get("message", ""),
                    level=source.get("level", "info"),
                    service=source.get("service", ""),
                    source=TelemetrySource.ELASTICSEARCH.value,
                    metadata=source,
                )
            )

        return logs

    async def aggregations(
        self,
        field: str = "level",
        size: int = 10,
    ) -> Dict[str, int]:
        try:
            client = self._get_client()
            response = await client.get(
                f"{self.url}/{self.index}/_search",
                json={
                    "size": 0,
                    "aggs": {"levels": {"terms": {"field": field, "size": size}}},
                },
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return {}

        return {
            bucket.get("key", ""): bucket.get("doc_count", 0)
            for bucket in data.get("aggregations", {})
            .get("levels", {})
            .get("buckets", [])
        }


class LokiClient:
    def __init__(self, url: Optional[str] = None):
        self.url = url or os.getenv("LOKI_URL", "http://localhost:3100")
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            token = os.getenv("LOKI_TOKEN", "")
            if token:
                self._client = httpx.AsyncClient(
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=30.0,
                )
            else:
                self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def query_range(
        self,
        query: str,
        start: int,
        end: int,
        limit: int = 100,
    ) -> List[LogEntry]:
        try:
            client = self._get_client()
            response = await client.get(
                f"{self.url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": start,
                    "end": end,
                    "limit": limit,
                },
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        logs = []
        for stream, values in data.get("data", {}).get("result", []):
            labels = stream
            for timestamp, message in values:
                logs.append(
                    LogEntry(
                        timestamp=float(timestamp) / 1e9,
                        message=message,
                        level=labels.get("level", "info"),
                        service=labels.get("service", labels.get("app", "")),
                        source=TelemetrySource.LOKI.value,
                        metadata=labels,
                    )
                )

        return logs

    async def query(
        self,
        query: str,
        limit: int = 100,
    ) -> List[LogEntry]:
        try:
            client = self._get_client()
            response = await client.get(
                f"{self.url}/loki/api/v1/query",
                params={"query": query, "limit": limit},
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        logs = []
        for stream, values in data.get("data", {}).get("result", []):
            labels = stream
            for timestamp, message in values:
                logs.append(
                    LogEntry(
                        timestamp=float(timestamp) / 1e9,
                        message=message,
                        level=labels.get("level", "info"),
                        service=labels.get("service", labels.get("app", "")),
                        source=TelemetrySource.LOKI.value,
                        metadata=labels,
                    )
                )

        return logs


_prometheus_client: Optional[PrometheusClient] = None
_elasticsearch_client: Optional[ElasticsearchClient] = None
_loki_client: Optional[LokiClient] = None


def get_prometheus_client() -> PrometheusClient:
    global _prometheus_client
    if _prometheus_client is None:
        _prometheus_client = PrometheusClient()
    return _prometheus_client


def get_elasticsearch_client() -> ElasticsearchClient:
    global _elasticsearch_client
    if _elasticsearch_client is None:
        _elasticsearch_client = ElasticsearchClient()
    return _elasticsearch_client


def get_loki_client() -> LokiClient:
    global _loki_client
    if _loki_client is None:
        _loki_client = LokiClient()
    return _loki_client
