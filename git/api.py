"""
Git API - FastAPI endpoints for git repository ingestion.

Provides /clone, /batch, /sync, /jobs, /jobs/{id}
endpoints with credential management.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Depends

from core.auth import require_authenticated

from git.pipeline import GitIngestionPipeline, get_git_pipeline, GitJobStatus
from git.repo import get_repo_manager
from git.credentials import get_credential_manager, CredentialType


class CloneRequest(BaseModel):
    url: str
    branch: str = "main"
    deep_clone: bool = True
    parse_code: bool = True
    index_graph: bool = True
    extensions: Optional[List[str]] = None


class CloneResponse(BaseModel):
    job_id: str
    repo_id: str
    status: str
    progress: float
    total_files: int
    total_entities: int


class BatchCloneRequest(BaseModel):
    repos: List[Dict[str, str]]
    parallel: bool = True


class BatchCloneResponse(BaseModel):
    jobs: List[Dict[str, Any]]


class OrgIngestRequest(BaseModel):
    org_name: str
    access_token: str
    repos: Optional[List[str]] = None
    branch: str = "main"


class CredentialRequest(BaseModel):
    repo_url: str
    credential_type: CredentialType
    username: Optional[str] = None
    token: Optional[str] = None
    password: Optional[str] = None
    ssh_key_path: Optional[str] = None
    ssh_key_password: Optional[str] = None


class JobStatusResponse(BaseModel):
    job_id: str
    repo_url: str
    branch: str
    status: str
    progress: float
    total_files: int
    total_entities: int
    indexed_count: int
    error: Optional[str]


router = APIRouter(prefix="/git", tags=["git"], dependencies=[Depends(require_authenticated)])


@router.post("/clone", response_model=CloneResponse)
async def clone_repository(request: CloneRequest):
    pipeline = get_git_pipeline()
    job = await pipeline.ingest_repository(
        repo_url=request.url,
        branch=request.branch,
        parse_code=request.parse_code,
        index_graph=request.index_graph,
        extensions=request.extensions,
    )

    return CloneResponse(
        job_id=job.job_id,
        repo_id=job.repo_id or "",
        status=job.status.value,
        progress=job.progress,
        total_files=job.total_files,
        total_entities=job.total_entities,
    )


@router.post("/batch", response_model=BatchCloneResponse)
async def clone_batch(request: BatchCloneRequest):
    pipeline = get_git_pipeline()
    jobs = await pipeline.ingest_multiple(request.repos, request.parallel)

    return BatchCloneResponse(
        jobs=[
            {
                "job_id": j.job_id,
                "repo_url": j.repo_url,
                "status": j.status.value,
            }
            for j in jobs
        ]
    )


@router.post("/organization")
async def ingest_organization(request: OrgIngestRequest):
    pipeline = get_git_pipeline()
    jobs = await pipeline.ingest_organization(
        org_name=request.org_name,
        access_token=request.access_token,
        repos=request.repos,
        branch=request.branch,
    )

    return {
        "org_name": request.org_name,
        "jobs": [
            {
                "job_id": j.job_id,
                "repo_url": j.repo_url,
                "status": j.status.value,
            }
            for j in jobs
        ],
    }


@router.post("/sync/{repo_id}")
async def sync_repository(repo_id: str):
    pipeline = get_git_pipeline()
    job = await pipeline.sync_repository(repo_id)

    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "total_entities": job.total_entities,
    }


@router.get("/repos", response_model=List[Dict[str, Any]])
async def list_repos():
    repo_manager = get_repo_manager()
    return repo_manager.list_repos()


@router.get("/repos/{repo_id}")
async def get_repo(repo_id: str):
    repo_manager = get_repo_manager()
    repo = repo_manager.get_repo(repo_id)

    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")

    branches = await repo_manager.list_branches(repo_id)

    return {
        "repo_id": repo.repo_id,
        "url": repo.url,
        "source": repo.source.value,
        "branch": repo.branch,
        "status": repo.status.value,
        "file_count": repo.file_count,
        "last_commit": repo.last_commit,
        "branches": branches,
    }


@router.get("/repos/{repo_id}/files")
async def list_repo_files(repo_id: str, extension: Optional[str] = None):
    repo_manager = get_repo_manager()
    extensions = [extension] if extension else None
    files = await repo_manager.list_files(repo_id, extensions=extensions)

    return {"repo_id": repo_id, "files": files[:100]}


@router.get("/repos/{repo_id}/files/{file_path:path}")
async def read_file(repo_id: str, file_path: str):
    repo_manager = get_repo_manager()
    file = await repo_manager.read_file(repo_id, file_path)

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    return {
        "path": file.path,
        "size": file.size,
        "language": file.language,
        "content": file.content,
    }


@router.post("/credentials")
async def add_credential(request: CredentialRequest):
    cred_manager = get_credential_manager()
    credential_id = cred_manager.add_credential(
        repo_url=request.repo_url,
        credential_type=request.credential_type,
        username=request.username,
        token=request.token,
        password=request.password,
        ssh_key_path=request.ssh_key_path,
        ssh_key_password=request.ssh_key_password,
    )

    return {"credential_id": credential_id, "repo_url": request.repo_url}


@router.get("/credentials", response_model=List[Dict[str, Any]])
async def list_credentials():
    cred_manager = get_credential_manager()
    return cred_manager.list_credentials()


@router.delete("/credentials/{credential_id}")
async def delete_credential(credential_id: str):
    cred_manager = get_credential_manager()
    success = cred_manager.delete_credential(credential_id)

    if not success:
        raise HTTPException(status_code=404, detail="Credential not found")

    return {"status": "deleted", "credential_id": credential_id}


@router.get("/jobs", response_model=List[Dict[str, Any]])
async def list_jobs(limit: int = 50):
    if limit < 1:
        limit = 1
    elif limit > 1000:
        limit = 1000
    pipeline = get_git_pipeline()
    return pipeline.list_jobs(limit)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str):
    pipeline = get_git_pipeline()
    job = pipeline.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.job_id,
        repo_url=job.repo_url,
        branch=job.branch,
        status=job.status.value,
        progress=job.progress,
        total_files=job.total_files,
        total_entities=job.total_entities,
        indexed_count=job.indexed_count,
        error=job.error,
    )


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    pipeline = get_git_pipeline()
    success = pipeline.cancel_job(job_id)

    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel job")

    return {"status": "cancelled", "job_id": job_id}


app = router


__all__ = ["app"]
