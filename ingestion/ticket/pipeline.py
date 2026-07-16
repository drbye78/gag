import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ingestion.ticket.client import (
    JiraClient,
    GitHubIssuesClient,
    get_jira_client,
    get_github_client,
    Ticket,
)


class TicketJobStatus(str, Enum):
    PENDING = "pending"
    FETCHING = "fetching"
    PROCESSING = "processing"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TicketJob:
    job_id: str
    source: str
    status: TicketJobStatus = TicketJobStatus.PENDING
    ticket_count: int = 0
    indexed_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def progress(self) -> float:
        if self.status == TicketJobStatus.COMPLETED:
            return 1.0
        elif self.status == TicketJobStatus.FAILED:
            return 0.0
        elif self.status == TicketJobStatus.PENDING:
            return 0.0
        elif self.status == TicketJobStatus.FETCHING:
            return 0.3
        elif self.status == TicketJobStatus.PROCESSING:
            return 0.6
        elif self.status == TicketJobStatus.INDEXING:
            return 0.8
        return 0.0


class TicketIngestionPipeline:
    def __init__(
        self,
        jira_client: Optional[JiraClient] = None,
        github_client: Optional[GitHubIssuesClient] = None,
    ):
        self.jira_client = jira_client or get_jira_client()
        self.github_client = github_client or get_github_client()
        self._jobs: Dict[str, TicketJob] = {}

    async def ingest_jira(
        self,
        jql: Optional[str] = None,
        max_results: int = 100,
        index: bool = True,
    ) -> TicketJob:
        job = TicketJob(
            job_id=str(uuid.uuid4()),
            source="jira",
            status=TicketJobStatus.PENDING,
        )
        self._jobs[job.job_id] = job

        try:
            job.status = TicketJobStatus.FETCHING
            tickets = await self.jira_client.fetch_issues(jql, max_results)
            job.ticket_count = len(tickets)

            job.status = TicketJobStatus.PROCESSING
            processed = self._process_tickets(tickets)

            job.status = TicketJobStatus.INDEXING
            if index:
                job.indexed_count = await self._index_tickets(processed)

            job.status = TicketJobStatus.COMPLETED
            job.updated_at = time.time()

        except Exception as e:
            job.status = TicketJobStatus.FAILED
            job.error = str(e)
            job.updated_at = time.time()

        return job

    async def ingest_github(
        self,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        state: str = "all",
        max_results: int = 100,
        index: bool = True,
    ) -> TicketJob:
        job = TicketJob(
            job_id=str(uuid.uuid4()),
            source="github",
            status=TicketJobStatus.PENDING,
        )
        self._jobs[job.job_id] = job

        if owner:
            self.github_client.owner = owner
        if repo:
            self.github_client.repo = repo

        try:
            job.status = TicketJobStatus.FETCHING
            tickets = await self.github_client.fetch_issues(
                state, max_results=max_results
            )
            job.ticket_count = len(tickets)

            job.status = TicketJobStatus.PROCESSING
            processed = self._process_tickets(tickets)

            job.status = TicketJobStatus.INDEXING
            if index:
                job.indexed_count = await self._index_tickets(processed)

            job.status = TicketJobStatus.COMPLETED
            job.updated_at = time.time()

        except Exception as e:
            job.status = TicketJobStatus.FAILED
            job.error = str(e)
            job.updated_at = time.time()

        return job

    async def ingest_all(
        self,
        jql: Optional[str] = None,
        github_state: str = "all",
        max_results: int = 100,
    ) -> Dict[str, TicketJob]:
        import asyncio

        jira_job = asyncio.create_task(self.ingest_jira(jql, max_results))
        github_job = asyncio.create_task(
            self.ingest_github(state=github_state, max_results=max_results)
        )

        await asyncio.gather(jira_job, github_job)

        return {
            "jira": jira_job.result(),
            "github": github_job.result(),
        }

    def _process_tickets(self, tickets: List[Ticket]) -> List[Dict[str, Any]]:
        processed = []
        for ticket in tickets:
            processed.append(
                {
                    "id": ticket.ticket_id,
                    "source": ticket.source,
                    "title": ticket.title,
                    "description": ticket.description[:500]
                    if ticket.description
                    else "",
                    "status": ticket.status,
                    "priority": ticket.priority,
                    "assignee": ticket.assignee,
                    "reporter": ticket.reporter,
                    "labels": ticket.labels,
                    "created_at": ticket.created_at,
                    "updated_at": ticket.updated_at,
                    "metadata": ticket.metadata,
                }
            )
        return processed

    async def _index_tickets(self, tickets: List[Dict[str, Any]]) -> int:
        return len(tickets)

    def get_job(self, job_id: str) -> Optional[TicketJob]:
        return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        jobs = list(self._jobs.values())[-limit:]
        return [
            {
                "job_id": j.job_id,
                "source": j.source,
                "status": j.status.value,
                "progress": j.progress,
                "ticket_count": j.ticket_count,
                "indexed_count": j.indexed_count,
                "error": j.error,
                "created_at": j.created_at,
            }
            for j in jobs
        ]


_pipeline: Optional[TicketIngestionPipeline] = None


def get_ticket_pipeline() -> TicketIngestionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = TicketIngestionPipeline()
    return _pipeline
