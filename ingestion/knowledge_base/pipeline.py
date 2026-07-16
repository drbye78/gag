import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ingestion.knowledge_base.client import (
    StackOverflowClient,
    RedditClient,
    ForumClient,
    KBEntry,
    get_stackoverflow_client,
    get_reddit_client,
    get_forum_client,
)


class KBJobStatus(str, Enum):
    PENDING = "pending"
    FETCHING = "fetching"
    PROCESSING = "processing"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class KBJob:
    job_id: str
    source: str
    status: KBJobStatus = KBJobStatus.PENDING
    entry_count: int = 0
    indexed_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def progress(self) -> float:
        if self.status == KBJobStatus.COMPLETED:
            return 1.0
        elif self.status == KBJobStatus.FAILED:
            return 0.0
        elif self.status == KBJobStatus.PENDING:
            return 0.0
        elif self.status == KBJobStatus.FETCHING:
            return 0.3
        elif self.status == KBJobStatus.PROCESSING:
            return 0.6
        elif self.status == KBJobStatus.INDEXING:
            return 0.8
        return 0.0


class KnowledgeBaseIngestionPipeline:
    def __init__(
        self,
        stackoverflow_client: Optional[StackOverflowClient] = None,
        reddit_client: Optional[RedditClient] = None,
        forum_client: Optional[ForumClient] = None,
    ):
        self.stackoverflow_client = stackoverflow_client or get_stackoverflow_client()
        self.reddit_client = reddit_client or get_reddit_client()
        self.forum_client = forum_client or get_forum_client()
        self._jobs: Dict[str, KBJob] = {}

    async def ingest_stackoverflow(
        self,
        query: str,
        max_results: int = 25,
        tags: Optional[List[str]] = None,
        index: bool = True,
    ) -> KBJob:
        job = KBJob(
            job_id=str(uuid.uuid4()),
            source="stackoverflow",
            status=KBJobStatus.PENDING,
        )
        self._jobs[job.job_id] = job

        try:
            job.status = KBJobStatus.FETCHING
            entries = await self.stackoverflow_client.search_questions(
                query=query,
                max_results=max_results,
                tagged=tags,
            )
            job.entry_count = len(entries)

            job.status = KBJobStatus.PROCESSING
            processed = self._process_entries(entries)

            job.status = KBJobStatus.INDEXING
            if index:
                job.indexed_count = len(processed)

            job.status = KBJobStatus.COMPLETED
            job.updated_at = time.time()

        except Exception as e:
            job.status = KBJobStatus.FAILED
            job.error = str(e)
            job.updated_at = time.time()

        return job

    async def ingest_reddit(
        self,
        subreddit: str,
        query: str,
        max_results: int = 25,
        index: bool = True,
    ) -> KBJob:
        job = KBJob(
            job_id=str(uuid.uuid4()),
            source="reddit",
            status=KBJobStatus.PENDING,
        )
        self._jobs[job.job_id] = job

        try:
            job.status = KBJobStatus.FETCHING
            entries = await self.reddit_client.search_submissions(
                subreddit=subreddit,
                query=query,
                max_results=max_results,
            )
            job.entry_count = len(entries)

            job.status = KBJobStatus.PROCESSING
            processed = self._process_entries(entries)

            job.status = KBJobStatus.INDEXING
            if index:
                job.indexed_count = len(processed)

            job.status = KBJobStatus.COMPLETED
            job.updated_at = time.time()

        except Exception as e:
            job.status = KBJobStatus.FAILED
            job.error = str(e)
            job.updated_at = time.time()

        return job

    async def ingest_forum(
        self,
        query: str,
        max_results: int = 25,
        index: bool = True,
    ) -> KBJob:
        job = KBJob(
            job_id=str(uuid.uuid4()),
            source="forum",
            status=KBJobStatus.PENDING,
        )
        self._jobs[job.job_id] = job

        try:
            job.status = KBJobStatus.FETCHING
            entries = await self.forum_client.search_posts(
                query=query,
                max_results=max_results,
            )
            job.entry_count = len(entries)

            job.status = KBJobStatus.PROCESSING
            processed = self._process_entries(entries)

            job.status = KBJobStatus.INDEXING
            if index:
                job.indexed_count = len(processed)

            job.status = KBJobStatus.COMPLETED
            job.updated_at = time.time()

        except Exception as e:
            job.status = KBJobStatus.FAILED
            job.error = str(e)
            job.updated_at = time.time()

        return job

    async def ingest_all_sources(
        self,
        query: str,
        subreddit: str = "programming",
    ) -> Dict[str, KBJob]:
        import asyncio

        so_job = asyncio.create_task(self.ingest_stackoverflow(query))
        reddit_job = asyncio.create_task(self.ingest_reddit(subreddit, query))
        forum_job = asyncio.create_task(self.ingest_forum(query))

        await asyncio.gather(so_job, reddit_job, forum_job)

        return {
            "stackoverflow": so_job.result(),
            "reddit": reddit_job.result(),
            "forum": forum_job.result(),
        }

    def _process_entries(self, entries: List[KBEntry]) -> List[Dict[str, Any]]:
        processed = []
        for entry in entries:
            processed.append(
                {
                    "id": entry.entry_id,
                    "source": entry.source,
                    "title": entry.title,
                    "content": entry.content[:500] if entry.content else "",
                    "author": entry.author,
                    "score": entry.score,
                    "tags": entry.tags,
                    "created_at": entry.created_at,
                    "metadata": entry.metadata,
                }
            )
        return processed

    def get_job(self, job_id: str) -> Optional[KBJob]:
        return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        jobs = list(self._jobs.values())[-limit:]
        return [
            {
                "job_id": j.job_id,
                "source": j.source,
                "status": j.status.value,
                "progress": j.progress,
                "entry_count": j.entry_count,
                "indexed_count": j.indexed_count,
                "error": j.error,
                "created_at": j.created_at,
            }
            for j in jobs
        ]


_pipeline: Optional[KnowledgeBaseIngestionPipeline] = None


def get_kb_pipeline() -> KnowledgeBaseIngestionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = KnowledgeBaseIngestionPipeline()
    return _pipeline
