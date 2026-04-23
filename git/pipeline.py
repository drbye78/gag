"""
Git Pipeline - Git repository ingestion pipeline.

Coordinates clone → parse → index pipeline
with job tracking and per-repo credentials.
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from git.credentials import GitCredentialManager, get_credential_manager
from git.repo import GitRepoManager, GitRepo, RepoSource, RepoStatus, get_repo_manager
from git.parser import CodeParser, CodeEntity, get_code_parser


class GitJobStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    PARSING = "parsing"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class GitIngestionJob:
    job_id: str
    repo_url: str
    branch: str
    status: GitJobStatus = GitJobStatus.PENDING
    repo_id: Optional[str] = None
    entities: List[CodeEntity] = field(default_factory=list)
    total_files: int = 0
    total_entities: int = 0
    indexed_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def progress(self) -> float:
        if self.status == GitJobStatus.COMPLETED:
            return 1.0
        elif self.status == GitJobStatus.FAILED:
            return 0.0
        elif self.status == GitJobStatus.PENDING:
            return 0.0
        elif self.status == GitJobStatus.CLONING:
            return 0.2
        elif self.status == GitJobStatus.PARSING:
            return 0.5
        elif self.status == GitJobStatus.INDEXING:
            return 0.8
        return 0.0


class GitIngestionPipeline:
    def __init__(
        self,
        repo_manager: Optional[GitRepoManager] = None,
        credential_manager: Optional[GitCredentialManager] = None,
        parser: Optional[CodeParser] = None,
        graph_indexer: Optional[Any] = None,
    ):
        self.repo_manager = repo_manager or get_repo_manager()
        self.credential_manager = credential_manager or get_credential_manager()
        self.parser = parser or get_code_parser()
        self.graph_indexer = graph_indexer
        self._jobs: Dict[str, GitIngestionJob] = {}

    async def ingest_repository(
        self,
        repo_url: str,
        branch: str = "main",
        parse_code: bool = True,
        index_graph: bool = True,
        extensions: Optional[List[str]] = None,
    ) -> GitIngestionJob:
        job = GitIngestionJob(
            job_id=str(uuid.uuid4())[:8],
            repo_url=repo_url,
            branch=branch,
        )
        self._jobs[job.job_id] = job

        try:
            job.status = GitJobStatus.CLONING

            repo = await self.repo_manager.clone(repo_url, branch, deep_clone=True)
            job.repo_id = repo.repo_id

            if repo.status == RepoStatus.FAILED:
                job.status = GitJobStatus.FAILED
                job.error = repo.error
                return job

            job.status = GitJobStatus.PARSING

            files = await self.repo_manager.list_files(
                repo.repo_id, extensions=extensions
            )
            job.total_files = len(files)

            files = files[:500]

            all_entities = []

            for file_path in files:
                file = await self.repo_manager.read_file(repo.repo_id, file_path)
                if not file:
                    continue

                if parse_code:
                    parsed = self.parser.parse(file.content, file_path)
                    all_entities.extend(parsed.entities)

                    entities_to_index = [
                        {
                            "id": e.entity_id,
                            "node_type": e.entity_type.value,
                            "properties": {
                                "name": e.name,
                                "file_path": e.file_path,
                                "start_line": e.start_line,
                                "end_line": e.end_line,
                                "language": e.language,
                                "repo_url": repo_url,
                                "branch": branch,
                            },
                        }
                        for e in parsed.entities
                    ]

                    if index_graph and self.graph_indexer and entities_to_index:
                        await self.graph_indexer.index_nodes(entities_to_index)
                        job.indexed_count += len(entities_to_index)

            job.entities = all_entities
            job.total_entities = len(all_entities)

            job.status = GitJobStatus.COMPLETED
            job.updated_at = time.time()

        except Exception as e:
            job.status = GitJobStatus.FAILED
            job.error = str(e)
            job.updated_at = time.time()

        return job

    async def ingest_multiple(
        self,
        repos: List[Dict[str, str]],
        parallel: bool = True,
    ) -> List[GitIngestionJob]:
        if parallel:
            import asyncio

            tasks = [
                self.ingest_repository(
                    repo_url=repo["url"],
                    branch=repo.get("branch", "main"),
                )
                for repo in repos
            ]
            jobs = await asyncio.gather(*tasks, return_exceptions=True)
            return [j for j in jobs if isinstance(j, GitIngestionJob)]
        else:
            jobs = []
            for repo in repos:
                job = await self.ingest_repository(
                    repo_url=repo["url"],
                    branch=repo.get("branch", "main"),
                )
                jobs.append(job)
            return jobs

    async def ingest_organization(
        self,
        org_name: str,
        access_token: str,
        repos: Optional[List[str]] = None,
        branch: str = "main",
    ) -> List[GitIngestionJob]:
        import httpx

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        async with httpx.AsyncClient() as client:
            if repos is None:
                resp = await client.get(
                    f"https://api.github.com/orgs/{org_name}/repos",
                    headers=headers,
                    params={"per_page": 100},
                    timeout=30.0,
                )
                resp.raise_for_status()
                data = resp.json()
                repos = [r["full_name"] for r in data]

            tasks = [
                self.ingest_repository(
                    repo_url=f"https://github.com/{repo}.git",
                    branch=branch,
                )
                for repo in repos
            ]

            jobs = await asyncio.gather(*tasks, return_exceptions=True)
            return [j for j in jobs if isinstance(j, GitIngestionJob)]

    async def sync_repository(
        self,
        repo_id: str,
    ) -> GitIngestionJob:
        import asyncio

        repo = self.repo_manager.get_repo(repo_id)
        if not repo:
            raise ValueError(f"Repo {repo_id} not found")

        job = GitIngestionJob(
            job_id=str(uuid.uuid4())[:8],
            repo_url=repo.url,
            branch=repo.branch,
            repo_id=repo_id,
        )
        self._jobs[job.job_id] = job

        try:
            await self.repo_manager.pull(repo_id)

            repo = self.repo_manager.get_repo(repo_id)

            files = (await self.repo_manager.list_files(repo_id))[:100]

            entities = []
            for file_path in files:
                file = await self.repo_manager.read_file(repo_id, file_path)
                if file:
                    parsed = self.parser.parse(file.content, file_path)
                    entities.extend(parsed.entities)

            job.entities = entities
            job.total_entities = len(entities)
            job.total_files = len(files)
            job.status = GitJobStatus.COMPLETED

        except Exception as e:
            job.status = GitJobStatus.FAILED
            job.error = str(e)

        job.updated_at = time.time()
        return job

    def get_job(self, job_id: str) -> Optional[GitIngestionJob]:
        return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        jobs = list(self._jobs.values())[-limit:]
        return [
            {
                "job_id": j.job_id,
                "repo_url": j.repo_url,
                "branch": j.branch,
                "status": j.status.value,
                "progress": j.progress,
                "total_files": j.total_files,
                "total_entities": j.total_entities,
                "indexed_count": j.indexed_count,
                "error": j.error,
                "created_at": j.created_at,
                "updated_at": j.updated_at,
            }
            for j in jobs
        ]

    def cancel_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job and job.status in (
            GitJobStatus.PENDING,
            GitJobStatus.CLONING,
            GitJobStatus.PARSING,
            GitJobStatus.INDEXING,
        ):
            job.status = GitJobStatus.FAILED
            job.error = "Cancelled by user"
            return True
        return False


_pipeline: Optional[GitIngestionPipeline] = None


def get_git_pipeline() -> GitIngestionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = GitIngestionPipeline()
    return _pipeline
