import asyncio
import logging
import time
from collections import OrderedDict
from typing import List, Optional

from unified_ingestion.core.job import ArtifactJob

logger = logging.getLogger(__name__)


class JobRegistry:
    def __init__(self, max_size: int = 1000, ttl_seconds: float = 3600.0):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._jobs: OrderedDict[str, ArtifactJob] = OrderedDict()
        self._lock = asyncio.Lock()

    async def put(self, job: ArtifactJob) -> None:
        async with self._lock:
            await self._evict_expired()
            while len(self._jobs) >= self.max_size:
                self._jobs.popitem(last=False)
            self._jobs[job.job_id] = job

    async def get(self, job_id: str) -> Optional[ArtifactJob]:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job and self._is_expired(job):
                del self._jobs[job_id]
                return None
            if job:
                self._jobs.move_to_end(job_id)
            return job

    async def list_recent(self, limit: int = 50) -> List[ArtifactJob]:
        async with self._lock:
            jobs = list(self._jobs.values())
            return jobs[-limit:][::-1]

    async def _evict_expired(self) -> None:
        now = time.time()
        expired = [
            jid for jid, job in self._jobs.items() if now - job.updated_at > self.ttl_seconds
        ]
        for jid in expired:
            del self._jobs[jid]

    def _is_expired(self, job: ArtifactJob) -> bool:
        return time.time() - job.updated_at > self.ttl_seconds


_registry: Optional[JobRegistry] = None


def get_job_registry() -> JobRegistry:
    global _registry
    if _registry is None:
        _registry = JobRegistry()
    return _registry
