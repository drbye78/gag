import asyncio
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    ENRICHING = "enriching"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class UIIngestionJob:
    job_id: str
    image_url: str
    title: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    sketch_id: Optional[str] = None
    element_count: int = 0
    extraction_confidence: float = 0.0
    indexing_success: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def progress(self) -> float:
        if self.status == JobStatus.COMPLETED:
            return 1.0
        elif self.status == JobStatus.FAILED:
            return 0.0
        elif self.status == JobStatus.PENDING:
            return 0.0
        elif self.status == JobStatus.EXTRACTING:
            return 0.33
        elif self.status == JobStatus.ENRICHING:
            return 0.66
        elif self.status == JobStatus.INDEXING:
            return 0.8
        return 0.0


class JobRegistry:
    def __init__(self, max_size: int = 1000, ttl_seconds: float = 3600.0):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._jobs: OrderedDict[str, UIIngestionJob] = OrderedDict()
        self._lock = asyncio.Lock()

    async def put(self, job: UIIngestionJob) -> None:
        async with self._lock:
            await self._evict_expired()
            while len(self._jobs) >= self.max_size:
                self._jobs.popitem(last=False)
            self._jobs[job.job_id] = job

    async def get(self, job_id: str) -> Optional[UIIngestionJob]:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job and self._is_expired(job):
                del self._jobs[job_id]
                return None
            if job:
                self._jobs.move_to_end(job_id)
            return job

    async def list_recent(self, limit: int = 50) -> List[UIIngestionJob]:
        async with self._lock:
            await self._evict_expired()
            jobs = list(self._jobs.values())[-limit:]
            return [j for j in jobs if not self._is_expired(j)]

    async def update(self, job: UIIngestionJob) -> None:
        async with self._lock:
            job.updated_at = time.time()
            self._jobs[job.job_id] = job

    def _is_expired(self, job: UIIngestionJob) -> bool:
        return time.time() - job.updated_at > self.ttl_seconds

    async def _evict_expired(self) -> None:
        expired = [jid for jid, job in self._jobs.items() if self._is_expired(job)]
        for jid in expired:
            del self._jobs[jid]


_registry: Optional[JobRegistry] = None


def get_ui_job_registry() -> JobRegistry:
    global _registry
    if _registry is None:
        _registry = JobRegistry()
    return _registry
