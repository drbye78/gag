import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ingestion.telemetry.client import (
    PrometheusClient,
    ElasticsearchClient,
    LokiClient,
    LogEntry,
    MetricPoint,
    get_prometheus_client,
    get_elasticsearch_client,
    get_loki_client,
)


class TelemetryJobStatus(str, Enum):
    PENDING = "pending"
    FETCHING = "fetching"
    PROCESSING = "processing"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TelemetryJob:
    job_id: str
    source: str
    status: TelemetryJobStatus = TelemetryJobStatus.PENDING
    log_count: int = 0
    metric_count: int = 0
    indexed_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def progress(self) -> float:
        if self.status == TelemetryJobStatus.COMPLETED:
            return 1.0
        elif self.status == TelemetryJobStatus.FAILED:
            return 0.0
        elif self.status == TelemetryJobStatus.PENDING:
            return 0.0
        elif self.status == TelemetryJobStatus.FETCHING:
            return 0.3
        elif self.status == TelemetryJobStatus.PROCESSING:
            return 0.6
        elif self.status == TelemetryJobStatus.INDEXING:
            return 0.8
        return 0.0


class TelemetryIngestionPipeline:
    def __init__(
        self,
        prometheus_client: Optional[PrometheusClient] = None,
        elasticsearch_client: Optional[ElasticsearchClient] = None,
        loki_client: Optional[LokiClient] = None,
    ):
        self.prometheus_client = prometheus_client or get_prometheus_client()
        self.elasticsearch_client = elasticsearch_client or get_elasticsearch_client()
        self.loki_client = loki_client or get_loki_client()
        self._jobs: Dict[str, TelemetryJob] = {}

    async def ingest_prometheus_metrics(
        self,
        query: str,
        start: Optional[float] = None,
        end: Optional[float] = None,
        step: str = "1m",
        index: bool = True,
    ) -> TelemetryJob:
        job = TelemetryJob(
            job_id=str(uuid.uuid4()),
            source="prometheus",
            status=TelemetryJobStatus.PENDING,
        )
        self._jobs[job.job_id] = job

        if start is None:
            start = time.time() - 3600
        if end is None:
            end = time.time()

        try:
            job.status = TelemetryJobStatus.FETCHING
            metrics = await self.prometheus_client.query_range(query, start, end, step)
            job.metric_count = len(metrics)

            job.status = TelemetryJobStatus.PROCESSING
            processed = self._process_metrics(metrics)

            job.status = TelemetryJobStatus.INDEXING
            if index:
                job.indexed_count = len(processed)

            job.status = TelemetryJobStatus.COMPLETED
            job.updated_at = time.time()

        except Exception as e:
            job.status = TelemetryJobStatus.FAILED
            job.error = str(e)
            job.updated_at = time.time()

        return job

    async def ingest_elasticsearch_logs(
        self,
        query: str,
        level: Optional[str] = None,
        service: Optional[str] = None,
        max_results: int = 100,
        index: bool = True,
    ) -> TelemetryJob:
        job = TelemetryJob(
            job_id=str(uuid.uuid4()),
            source="elasticsearch",
            status=TelemetryJobStatus.PENDING,
        )
        self._jobs[job.job_id] = job

        try:
            job.status = TelemetryJobStatus.FETCHING
            logs = await self.elasticsearch_client.search(
                query, level, service, max_results
            )
            job.log_count = len(logs)

            job.status = TelemetryJobStatus.PROCESSING
            processed = self._process_logs(logs)

            job.status = TelemetryJobStatus.INDEXING
            if index:
                job.indexed_count = len(processed)

            job.status = TelemetryJobStatus.COMPLETED
            job.updated_at = time.time()

        except Exception as e:
            job.status = TelemetryJobStatus.FAILED
            job.error = str(e)
            job.updated_at = time.time()

        return job

    async def ingest_loki_logs(
        self,
        query: str,
        start: Optional[int] = None,
        end: Optional[int] = None,
        limit: int = 100,
        index: bool = True,
    ) -> TelemetryJob:
        job = TelemetryJob(
            job_id=str(uuid.uuid4()),
            source="loki",
            status=TelemetryJobStatus.PENDING,
        )
        self._jobs[job.job_id] = job

        if start is None:
            start = int((time.time() - 3600) * 1e9)
        if end is None:
            end = int(time.time() * 1e9)

        try:
            job.status = TelemetryJobStatus.FETCHING
            logs = await self.loki_client.query_range(query, start, end, limit)
            job.log_count = len(logs)

            job.status = TelemetryJobStatus.PROCESSING
            processed = self._process_logs(logs)

            job.status = TelemetryJobStatus.INDEXING
            if index:
                job.indexed_count = len(processed)

            job.status = TelemetryJobStatus.COMPLETED
            job.updated_at = time.time()

        except Exception as e:
            job.status = TelemetryJobStatus.FAILED
            job.error = str(e)
            job.updated_at = time.time()

        return job

    async def ingest_all_sources(
        self,
        log_query: str,
        metric_query: str,
    ) -> Dict[str, TelemetryJob]:
        import asyncio

        log_job = asyncio.create_task(self.ingest_loki_logs(log_query))
        metric_job = asyncio.create_task(self.ingest_prometheus_metrics(metric_query))

        await asyncio.gather(log_job, metric_job)

        return {
            "loki": log_job.result(),
            "prometheus": metric_job.result(),
        }

    def _process_logs(self, logs: List[LogEntry]) -> List[Dict[str, Any]]:
        processed = []
        for log in logs:
            processed.append(
                {
                    "timestamp": log.timestamp,
                    "message": log.message,
                    "level": log.level,
                    "service": log.service,
                    "source": log.source,
                    "metadata": log.metadata,
                }
            )
        return processed

    def _process_metrics(self, metrics: List[MetricPoint]) -> List[Dict[str, Any]]:
        processed = []
        for metric in metrics:
            processed.append(
                {
                    "name": metric.name,
                    "value": metric.value,
                    "timestamp": metric.timestamp,
                    "labels": metric.labels,
                    "source": metric.source,
                }
            )
        return processed

    def get_job(self, job_id: str) -> Optional[TelemetryJob]:
        return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        jobs = list(self._jobs.values())[-limit:]
        return [
            {
                "job_id": j.job_id,
                "source": j.source,
                "status": j.status.value,
                "progress": j.progress,
                "log_count": j.log_count,
                "metric_count": j.metric_count,
                "indexed_count": j.indexed_count,
                "error": j.error,
                "created_at": j.created_at,
            }
            for j in jobs
        ]


_pipeline: Optional[TelemetryIngestionPipeline] = None


def get_telemetry_pipeline() -> TelemetryIngestionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = TelemetryIngestionPipeline()
    return _pipeline
