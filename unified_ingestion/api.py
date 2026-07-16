import asyncio
import hashlib
import logging
import os
import zipfile
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pydantic import field_validator

from core.auth import require_authenticated
from unified_ingestion.core.registry import get_job_registry
from unified_ingestion.core.types import ArtifactType
from unified_ingestion.core.job import ArtifactJob, JobStatus
from unified_ingestion.handlers import register_handlers, get_handler

logger = logging.getLogger(__name__)

register_handlers()


class IngestRequest(BaseModel):
    content: bytes
    artifact_type: str
    source_id: str
    metadata: Optional[Dict[str, Any]] = None
    index_vectors: bool = True
    index_graph: bool = False

    @field_validator("source_id", "artifact_type")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("field must not be empty")
        return v.strip()


class IngestResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    total_chunks: int
    indexed_count: int
    error: Optional[str] = None


class BatchIngestRequest(BaseModel):
    items: List[Dict[str, Any]]
    parallel: bool = True


class BatchIngestResponse(BaseModel):
    jobs: List[Dict[str, Any]]


class ZipIngestRequest(BaseModel):
    zip_content: bytes
    artifact_type: str
    metadata: Optional[Dict[str, Any]] = None


class GitIngestRequest(BaseModel):
    repo_url: str
    branch: str = "main"
    artifact_type: str = "source_code"
    depth: int = 1


class FilesystemIngestRequest(BaseModel):
    paths: List[str]
    artifact_type: str = "source_code"
    recursive: bool = True


class JobStatusResponse(BaseModel):
    job_id: str
    artifact_type: str
    source_id: str
    status: str
    progress: float
    total_chunks: int
    indexed_count: int
    error: Optional[str]
    created_at: float
    updated_at: float


class FormatInfo(BaseModel):
    type: str
    description: str
    extensions: List[str]


router = APIRouter(prefix="/artifacts", tags=["artifacts"], dependencies=[Depends(require_authenticated)])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_artifact(request: IngestRequest):
    job_id = f"job_{request.source_id}"
    registry = get_job_registry()

    job = ArtifactJob(
        job_id=job_id,
        artifact_type=request.artifact_type,
        source_id=request.source_id,
        source_path="",
        content=request.content,
        status=JobStatus.PROCESSING,
    )
    await registry.put(job)

    try:
        handler = get_handler(request.artifact_type)
        metadata = request.metadata or {}
        metadata["source_id"] = request.source_id

        result = await handler.handle(request.content, request.source_id, metadata)

        job.status = JobStatus.COMPLETED if result.success else JobStatus.FAILED
        job.chunks = result.chunks
        job.embedded_chunks = []
        job.total_chunks = len(result.chunks)
        job.indexed_count = job.total_chunks if request.index_vectors else 0
        job.error = result.error
        job.metadata = result.metadata
        job.updated_at = asyncio.get_event_loop().time()

    except Exception as e:
        logger.error(f"Ingest failed: {e}")
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.updated_at = asyncio.get_event_loop().time()

    await registry.put(job)
    return IngestResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        total_chunks=job.total_chunks,
        indexed_count=job.indexed_count,
        error=job.error,
    )


@router.post("/ingest/batch", response_model=BatchIngestResponse)
async def ingest_batch(request: BatchIngestRequest):
    registry = get_job_registry()
    jobs = []

    if request.parallel:
        tasks = []
        for item in request.items:
            job_id = f"job_{item.get('source_id', uuid.uuid4().hex[:8])}"
            job = ArtifactJob(
                job_id=job_id,
                artifact_type=item.get("artifact_type", "document"),
                source_id=item.get("source_id", ""),
                source_path=item.get("source_path", ""),
                content=item.get("content"),
                status=JobStatus.PROCESSING,
            )
            tasks.append(_process_job(job, registry))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                jobs.append({"error": str(result)})
            else:
                jobs.append(result)
    else:
        for item in request.items:
            job_id = f"job_{item.get('source_id', uuid.uuid4().hex[:8])}"
            job = ArtifactJob(
                job_id=job_id,
                artifact_type=item.get("artifact_type", "document"),
                source_id=item.get("source_id", ""),
                source_path=item.get("source_path", ""),
                content=item.get("content"),
                status=JobStatus.PROCESSING,
            )
            result_job = await _process_job(job, registry)
            jobs.append(result_job)

    return BatchIngestResponse(jobs=jobs)


async def _process_job(job: ArtifactJob, registry) -> Dict[str, Any]:
    try:
        handler = get_handler(job.artifact_type)
        metadata = {"source_id": job.source_id}

        result = await handler.handle(job.content, job.source_id, metadata)

        job.status = JobStatus.COMPLETED if result.success else JobStatus.FAILED
        job.chunks = result.chunks
        job.total_chunks = len(result.chunks)
        job.indexed_count = job.total_chunks
        job.error = result.error
        job.metadata = result.metadata

    except Exception as e:
        logger.error(f"Job {job.job_id} failed: {e}")
        job.status = JobStatus.FAILED
        job.error = str(e)

    job.updated_at = asyncio.get_event_loop().time()
    await registry.put(job)

    return {"job_id": job.job_id, "status": job.status, "progress": job.progress}


@router.post("/ingest/zip", response_model=BatchIngestResponse)
async def ingest_zip(request: ZipIngestRequest):
    import io

    registry = get_job_registry()
    jobs = []

    try:
        with zipfile.ZipFile(io.BytesIO(request.zip_content)) as zf:
            for name in zf.namelist():
                if name.endswith("/"):
                    continue

                content = zf.read(name)
                artifact_type = request.artifact_type

                ext = os.path.splitext(name)[1].lower()
                type_map = {
                    ".py": "source_code",
                    ".js": "source_code",
                    ".ts": "source_code",
                    ".yaml": "k8s",
                    ".yml": "k8s",
                    ".md": "markdown",
                    ".json": "json",
                    ".yaml": "yaml",
                    ".graphql": "graphql",
                    ".proto": "grpc_proto",
                }
                artifact_type = type_map.get(ext, artifact_type)

                job_id = f"job_{name}"
                job = ArtifactJob(
                    job_id=job_id,
                    artifact_type=artifact_type,
                    source_id=name,
                    source_path=name,
                    content=content,
                    status=JobStatus.PROCESSING,
                )

                result_job = await _process_job(job, registry)
                jobs.append(result_job)

    except Exception as e:
        logger.error(f"ZIP ingest failed: {e}")
        return BatchIngestResponse(jobs=[{"error": str(e)}])

    return BatchIngestResponse(jobs=jobs)


@router.post("/ingest/git", response_model=IngestResponse)
async def ingest_git(request: GitIngestRequest):
    registry = get_job_registry()

    repo_hash = hashlib.sha256(request.repo_url.encode()).hexdigest()[:8]
    job_id = f"git_{repo_hash}"
    job = ArtifactJob(
        job_id=job_id,
        artifact_type=request.artifact_type,
        source_id=request.repo_url,
        source_path=request.repo_url,
        status=JobStatus.PROCESSING,
    )

    try:
        import tempfile
        import shutil

        with tempfile.TemporaryDirectory() as tmpdir:
            import subprocess

            result = subprocess.run(
                ["git", "clone", "--depth", str(request.depth), "--branch", request.branch, "--single-branch", request.repo_url, tmpdir],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise Exception(f"Git clone failed: {result.stderr}")

            files_content = []
            for root, _, files in os.walk(tmpdir):
                for f in files:
                    if f.startswith("."):
                        continue
                    path = os.path.join(root, f)
                    try:
                        with open(path, "rb") as fp:
                            files_content.append((path, fp.read()))
                    except Exception:
                        pass

            all_content = b"\n".join(fc for _, fc in files_content)
            handler = get_handler(request.artifact_type)
            result = await handler.handle(all_content, request.repo_url, {})

            job.status = JobStatus.COMPLETED if result.success else JobStatus.FAILED
            job.chunks = result.chunks
            job.total_chunks = len(result.chunks)
            job.indexed_count = job.total_chunks
            job.error = result.error

    except Exception as e:
        logger.error(f"Git ingest failed: {e}")
        job.status = JobStatus.FAILED
        job.error = str(e)

    job.updated_at = asyncio.get_event_loop().time()
    await registry.put(job)

    return IngestResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        total_chunks=job.total_chunks,
        indexed_count=job.indexed_count,
        error=job.error,
    )


@router.post("/ingest/filesystem", response_model=BatchIngestResponse)
async def ingest_filesystem(request: FilesystemIngestRequest):
    registry = get_job_registry()
    jobs = []

    for path in request.paths:
        if not os.path.exists(path):
            jobs.append({"job_id": path, "error": "Path not found"})
            continue

        if os.path.isfile(path):
            files = [path]
        elif request.recursive:
            files = [os.path.join(root, f) for root, _, files in os.walk(path) for f in files]
        else:
            files = os.listdir(path)

        for f in files:
            file_path = os.path.join(path, f) if os.path.isdir(path) else f
            if not os.path.isfile(file_path):
                continue

            try:
                with open(file_path, "rb") as fp:
                    content = fp.read()

                ext = os.path.splitext(file_path)[1].lower()
                type_map = {
                    ".py": "source_code",
                    ".js": "source_code",
                    ".ts": "source_code",
                    ".yaml": "k8s",
                    ".yml": "k8s",
                    ".md": "markdown",
                }
                artifact_type = type_map.get(ext, request.artifact_type)

                job_id = f"fs_{os.path.basename(file_path)}"
                job = ArtifactJob(
                    job_id=job_id,
                    artifact_type=artifact_type,
                    source_id=file_path,
                    source_path=file_path,
                    content=content,
                    status=JobStatus.PROCESSING,
                )

                result_job = await _process_job(job, registry)
                jobs.append(result_job)

            except Exception as e:
                jobs.append({"job_id": file_path, "error": str(e)})

    return BatchIngestResponse(jobs=jobs)


@router.get("/jobs")
async def list_jobs(limit: int = 50):
    registry = get_job_registry()
    jobs = await registry.list_recent(limit)
    return {
        "jobs": [
            {
                "job_id": j.job_id,
                "artifact_type": j.artifact_type,
                "source_id": j.source_id,
                "status": j.status,
                "progress": j.progress,
                "total_chunks": j.total_chunks,
                "created_at": j.created_at,
            }
            for j in jobs
        ]
    }


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str):
    registry = get_job_registry()
    job = await registry.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        job_id=job.job_id,
        artifact_type=job.artifact_type,
        source_id=job.source_id,
        status=job.status,
        progress=job.progress,
        total_chunks=job.total_chunks,
        indexed_count=job.indexed_count,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    registry = get_job_registry()
    job = await registry.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = JobStatus.FAILED
    job.error = "Cancelled by user"
    job.updated_at = asyncio.get_event_loop().time()
    await registry.put(job)

    return {"job_id": job_id, "status": "cancelled"}


@router.get("/formats")
async def list_formats():
    formats = [
        {"type": "document", "description": "PDF, DOCX, PPTX, XLSX", "extensions": [".pdf", ".docx", ".pptx", ".xlsx"]},
        {"type": "markdown", "description": "Markdown with frontmatter", "extensions": [".md", ".markdown"]},
        {"type": "source_code", "description": "Source code (Python, JS, Go, etc)", "extensions": [".py", ".js", ".ts", ".go", ".rs", ".java"]},
        {"type": "config", "description": "Configuration files", "extensions": [".json", ".yaml", ".yml", ".toml", ".env"]},
        {"type": "text", "description": "Plain text, CSV, TSV", "extensions": [".txt", ".csv", ".tsv"]},
        {"type": "k8s", "description": "Kubernetes manifests", "extensions": [".yaml", ".yml"]},
        {"type": "helm", "description": "Helm charts", "extensions": ["Chart.yaml", "values.yaml"]},
        {"type": "dockerfile", "description": "Dockerfiles", "extensions": ["Dockerfile"]},
        {"type": "istio", "description": "Istio resources", "extensions": [".yaml"]},
        {"type": "diagram", "description": "Architecture diagrams", "extensions": [".svg", ".png"]},
        {"type": "plantuml", "description": "PlantUML diagrams", "extensions": [".puml", ".plantuml"]},
        {"type": "mermaid", "description": "Mermaid diagrams", "extensions": [".mmd", ".mermaid"]},
        {"type": "bpmn", "description": "BPMN 2.0", "extensions": [".bpmn", ".xml"]},
        {"type": "api_spec", "description": "OpenAPI/Swagger specs", "extensions": [".json", ".yaml", ".yml"]},
        {"type": "graphql", "description": "GraphQL schemas", "extensions": [".graphql", ".gql"]},
    ]
    return {"formats": formats}


@router.get("/types")
async def list_artifact_types():
    return {"types": [t.value for t in ArtifactType]}


try:
    from unified_ingestion.optimize import (
        get_metrics_collector,
        get_health_checker,
        format_error,
        IngestionError,
    )
    OPTIMIZE_AVAILABLE = True
except ImportError:
    OPTIMIZE_AVAILABLE = False
    def format_error(error: Exception) -> dict:
        return {"error": str(type(error).__name__), "message": str(error)}


if OPTIMIZE_AVAILABLE:

    @router.get("/health")
    async def health_check():
        return get_health_checker().get_status()

    @router.get("/metrics")
    async def metrics():
        metrics = get_metrics_collector()
        return metrics.get_stats()

    @router.get("/metrics/counters")
    async def list_counters():
        metrics = get_metrics_collector()
        return metrics.get_stats()["counters"]