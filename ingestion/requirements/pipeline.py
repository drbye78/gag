import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ingestion.requirements.client import (
    RequirementsClient,
    JiraRequirementsClient,
    ConfluenceRequirementsClient,
    LocalRequirementsClient,
    Requirement,
    get_requirements_client,
)


class RequirementsJobStatus(str, Enum):
    PENDING = "pending"
    FETCHING = "fetching"
    PROCESSING = "processing"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RequirementsJob:
    job_id: str
    source: str
    status: RequirementsJobStatus = RequirementsJobStatus.PENDING
    req_count: int = 0
    indexed_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def progress(self) -> float:
        if self.status == RequirementsJobStatus.COMPLETED:
            return 1.0
        elif self.status == RequirementsJobStatus.FAILED:
            return 0.0
        elif self.status == RequirementsJobStatus.PENDING:
            return 0.0
        elif self.status == RequirementsJobStatus.FETCHING:
            return 0.3
        elif self.status == RequirementsJobStatus.PROCESSING:
            return 0.6
        elif self.status == RequirementsJobStatus.INDEXING:
            return 0.8
        return 0.0


class RequirementsIngestionPipeline:
    def __init__(
        self,
        jira_client: Optional[JiraRequirementsClient] = None,
        confluence_client: Optional[ConfluenceRequirementsClient] = None,
        local_client: Optional[LocalRequirementsClient] = None,
    ):
        self.jira_client = jira_client or JiraRequirementsClient()
        self.confluence_client = confluence_client or ConfluenceRequirementsClient()
        self.local_client = local_client or LocalRequirementsClient()
        self._jobs: Dict[str, RequirementsJob] = {}

    async def ingest_jira(
        self,
        issue_type: str = "Story",
        max_results: int = 100,
        index: bool = True,
    ) -> RequirementsJob:
        job = RequirementsJob(
            job_id=str(uuid.uuid4()),
            source="jira",
            status=RequirementsJobStatus.PENDING,
        )
        self._jobs[job.job_id] = job

        try:
            job.status = RequirementsJobStatus.FETCHING
            requirements = await self.jira_client.fetch_requirements(
                issue_type, max_results
            )
            job.req_count = len(requirements)

            job.status = RequirementsJobStatus.PROCESSING
            processed = self._process_requirements(requirements)

            job.status = RequirementsJobStatus.INDEXING
            if index:
                job.indexed_count = len(processed)

            job.status = RequirementsJobStatus.COMPLETED
            job.updated_at = time.time()

        except Exception as e:
            job.status = RequirementsJobStatus.FAILED
            job.error = str(e)
            job.updated_at = time.time()

        return job

    async def ingest_confluence(
        self,
        space_key: str = "REQ",
        label: Optional[str] = "requirements",
        index: bool = True,
    ) -> RequirementsJob:
        job = RequirementsJob(
            job_id=str(uuid.uuid4()),
            source="confluence",
            status=RequirementsJobStatus.PENDING,
        )
        self._jobs[job.job_id] = job

        try:
            job.status = RequirementsJobStatus.FETCHING
            requirements = await self.confluence_client.fetch_requirements(
                space_key, label
            )
            job.req_count = len(requirements)

            job.status = RequirementsJobStatus.PROCESSING
            processed = self._process_requirements(requirements)

            job.status = RequirementsJobStatus.INDEXING
            if index:
                job.indexed_count = len(processed)

            job.status = RequirementsJobStatus.COMPLETED
            job.updated_at = time.time()

        except Exception as e:
            job.status = RequirementsJobStatus.FAILED
            job.error = str(e)
            job.updated_at = time.time()

        return job

    async def ingest_local(
        self,
        file_pattern: str = "*.md",
        index: bool = True,
    ) -> RequirementsJob:
        job = RequirementsJob(
            job_id=str(uuid.uuid4()),
            source="local",
            status=RequirementsJobStatus.PENDING,
        )
        self._jobs[job.job_id] = job

        try:
            job.status = RequirementsJobStatus.FETCHING
            requirements = await self.local_client.fetch_requirements(file_pattern)
            job.req_count = len(requirements)

            job.status = RequirementsJobStatus.PROCESSING
            processed = self._process_requirements(requirements)

            job.status = RequirementsJobStatus.INDEXING
            if index:
                job.indexed_count = len(processed)

            job.status = RequirementsJobStatus.COMPLETED
            job.updated_at = time.time()

        except Exception as e:
            job.status = RequirementsJobStatus.FAILED
            job.error = str(e)
            job.updated_at = time.time()

        return job

    def _process_requirements(
        self, requirements: List[Requirement]
    ) -> List[Dict[str, Any]]:
        processed = []
        for req in requirements:
            processed.append(
                {
                    "id": req.req_id,
                    "source": req.source,
                    "title": req.title,
                    "description": req.description[:500],
                    "status": req.status,
                    "priority": req.priority,
                    "type": req.type,
                    "acceptance_criteria": req.acceptance_criteria,
                    "traceability": req.traceability,
                    "created_at": req.created_at,
                }
            )
        return processed

    def get_job(self, job_id: str) -> Optional[RequirementsJob]:
        return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        jobs = list(self._jobs.values())[-limit:]
        return [
            {
                "job_id": j.job_id,
                "source": j.source,
                "status": j.status.value,
                "progress": j.progress,
                "req_count": j.req_count,
                "indexed_count": j.indexed_count,
                "error": j.error,
                "created_at": j.created_at,
            }
            for j in jobs
        ]


_pipeline: Optional[RequirementsIngestionPipeline] = None


def get_requirements_pipeline() -> RequirementsIngestionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RequirementsIngestionPipeline()
    return _pipeline
