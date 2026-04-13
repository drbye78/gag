import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ingestion.architecture.client import (
    ArchitectureClient,
    ArchitectureDiagram,
    get_architecture_client,
)


class ArchitectureJobStatus(str, Enum):
    PENDING = "pending"
    FETCHING = "fetching"
    PARSING = "parsing"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ArchitectureJob:
    job_id: str
    source: str
    status: ArchitectureJobStatus = ArchitectureJobStatus.PENDING
    diagram_count: int = 0
    component_count: int = 0
    indexed_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def progress(self) -> float:
        if self.status == ArchitectureJobStatus.COMPLETED:
            return 1.0
        elif self.status == ArchitectureJobStatus.FAILED:
            return 0.0
        elif self.status == ArchitectureJobStatus.PENDING:
            return 0.0
        elif self.status == ArchitectureJobStatus.FETCHING:
            return 0.25
        elif self.status == ArchitectureJobStatus.PARSING:
            return 0.5
        elif self.status == ArchitectureJobStatus.INDEXING:
            return 0.75
        return 0.0


class ArchitectureIngestionPipeline:
    def __init__(self, client: Optional[ArchitectureClient] = None):
        self.client = client or get_architecture_client()
        self._jobs: Dict[str, ArchitectureJob] = {}

    async def ingest_confluence(
        self,
        space_key: str,
        label: Optional[str] = None,
        index: bool = True,
    ) -> ArchitectureJob:
        job = ArchitectureJob(
            job_id=str(uuid.uuid4()),
            source="confluence",
            status=ArchitectureJobStatus.PENDING,
        )
        self._jobs[job.job_id] = job

        try:
            job.status = ArchitectureJobStatus.FETCHING
            diagrams = await self.client.fetch_from_confluence(space_key, label)
            job.diagram_count = len(diagrams)

            job.status = ArchitectureJobStatus.PARSING
            components, relationships = self._parse_all_diagrams(diagrams)
            job.component_count = len(components)

            job.status = ArchitectureJobStatus.INDEXING
            if index:
                job.indexed_count = len(components) + len(relationships)

            job.status = ArchitectureJobStatus.COMPLETED
            job.updated_at = time.time()

        except Exception as e:
            job.status = ArchitectureJobStatus.FAILED
            job.error = str(e)
            job.updated_at = time.time()

        return job

    async def ingest_github(
        self,
        repo: str,
        path: str = "docs/architecture",
        index: bool = True,
    ) -> ArchitectureJob:
        job = ArchitectureJob(
            job_id=str(uuid.uuid4()),
            source="github",
            status=ArchitectureJobStatus.PENDING,
        )
        self._jobs[job.job_id] = job

        try:
            job.status = ArchitectureJobStatus.FETCHING
            diagrams = await self.client.fetch_from_github(repo, path)
            job.diagram_count = len(diagrams)

            job.status = ArchitectureJobStatus.PARSING
            components, relationships = self._parse_all_diagrams(diagrams)
            job.component_count = len(components)

            job.status = ArchitectureJobStatus.INDEXING
            if index:
                job.indexed_count = len(components) + len(relationships)

            job.status = ArchitectureJobStatus.COMPLETED
            job.updated_at = time.time()

        except Exception as e:
            job.status = ArchitectureJobStatus.FAILED
            job.error = str(e)
            job.updated_at = time.time()

        return job

    async def ingest_local(
        self,
        directory: str,
        index: bool = True,
    ) -> ArchitectureJob:
        job = ArchitectureJob(
            job_id=str(uuid.uuid4()),
            source="local",
            status=ArchitectureJobStatus.PENDING,
        )
        self._jobs[job.job_id] = job

        try:
            job.status = ArchitectureJobStatus.FETCHING
            diagrams = await self.client.fetch_from_local(directory)
            job.diagram_count = len(diagrams)

            job.status = ArchitectureJobStatus.PARSING
            components, relationships = self._parse_all_diagrams(diagrams)
            job.component_count = len(components)

            job.status = ArchitectureJobStatus.INDEXING
            if index:
                job.indexed_count = len(components) + len(relationships)

            job.status = ArchitectureJobStatus.COMPLETED
            job.updated_at = time.time()

        except Exception as e:
            job.status = ArchitectureJobStatus.FAILED
            job.error = str(e)
            job.updated_at = time.time()

        return job

    def _parse_all_diagrams(
        self,
        diagrams: List[ArchitectureDiagram],
    ) -> tuple:
        all_components = []
        all_relationships = []

        for diagram in diagrams:
            parsed = self.client.parse_architecture(diagram)
            all_components.extend(parsed.get("components", []))
            all_relationships.extend(parsed.get("relationships", []))

        return all_components, all_relationships

    def get_job(self, job_id: str) -> Optional[ArchitectureJob]:
        return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        jobs = list(self._jobs.values())[-limit:]
        return [
            {
                "job_id": j.job_id,
                "source": j.source,
                "status": j.status.value,
                "progress": j.progress,
                "diagram_count": j.diagram_count,
                "component_count": j.component_count,
                "indexed_count": j.indexed_count,
                "error": j.error,
                "created_at": j.created_at,
            }
            for j in jobs
        ]


_pipeline: Optional[ArchitectureIngestionPipeline] = None


def get_architecture_pipeline() -> ArchitectureIngestionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = ArchitectureIngestionPipeline()
    return _pipeline
