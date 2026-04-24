"""
Ingestion API - FastAPI endpoints for data ingestion.

Provides /ingest, /ingest/batch, /ingest/codebase,
/jobs, /jobs/{id} endpoints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, field_validator

from fastapi import APIRouter, HTTPException, Depends

from core.auth import require_authenticated

from ingestion.pipeline import IngestionPipeline, get_ingestion_pipeline, JobStatus


class IngestRequest(BaseModel):
    content: str
    source_id: str
    source_type: str = "document"
    metadata: Optional[Dict[str, Any]] = None
    index: bool = True
    use_graphrag: bool = False

    @field_validator("content", "source_id")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("field must not be empty")
        return v.strip() if isinstance(v, str) else v


class IngestResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    total_chunks: int
    indexed_count: int


class BatchIngestRequest(BaseModel):
    documents: List[Dict[str, str]]
    parallel: bool = True


class BatchIngestResponse(BaseModel):
    jobs: List[Dict[str, Any]]


class CodebaseIngestRequest(BaseModel):
    files: Dict[str, str]
    index_graph: bool = False


class JobStatusResponse(BaseModel):
    job_id: str
    source_id: str
    source_type: str
    status: str
    progress: float
    total_chunks: int
    indexed_count: int
    error: Optional[str]


router = APIRouter(prefix="/ingestion", tags=["ingestion"], dependencies=[Depends(require_authenticated)])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(request: IngestRequest):
    pipeline = get_ingestion_pipeline(use_graphrag=request.use_graphrag)
    job = await pipeline.ingest_document(
        content=request.content,
        source_id=request.source_id,
        source_type=request.source_type,
        metadata=request.metadata,
        index=request.index,
        use_graphrag=request.use_graphrag,
    )

    return IngestResponse(
        job_id=job.job_id,
        status=job.status.value,
        progress=job.progress,
        total_chunks=job.total_chunks,
        indexed_count=job.indexed_count,
    )


@router.post("/batch", response_model=BatchIngestResponse)
async def ingest_batch(request: BatchIngestRequest):
    pipeline = get_ingestion_pipeline()
    jobs = await pipeline.ingest_batch(request.documents, request.parallel)

    return BatchIngestResponse(
        jobs=[
            {
                "job_id": j.job_id,
                "source_id": j.source_id,
                "status": j.status.value,
            }
            for j in jobs
        ]
    )


@router.post("/codebase")
async def ingest_codebase(request: CodebaseIngestRequest):
    pipeline = get_ingestion_pipeline()
    job = await pipeline.ingest_codebase(
        files=request.files,
        index_graph=request.index_graph,
    )

    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "total_chunks": job.total_chunks,
        "indexed_count": job.indexed_count,
        "file_count": job.metadata.get("file_count", 0),
    }


@router.get("/jobs", response_model=List[Dict[str, Any]])
async def list_jobs(limit: int = 50):
    if limit < 1:
        limit = 1
    elif limit > 1000:
        limit = 1000
    pipeline = get_ingestion_pipeline()
    return pipeline.list_jobs(limit)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str):
    pipeline = get_ingestion_pipeline()
    job = pipeline.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.job_id,
        source_id=job.source_id,
        source_type=job.source_type,
        status=job.status.value,
        progress=job.progress,
        total_chunks=job.total_chunks,
        indexed_count=job.indexed_count,
        error=job.error,
    )


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    pipeline = get_ingestion_pipeline()
    success = pipeline.cancel_job(job_id)

    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel job")

    return {"status": "cancelled", "job_id": job_id}


app = router


__all__ = ["app"]
