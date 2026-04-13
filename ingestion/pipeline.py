"""
Pipeline - Ingestion orchestration.

Coordinates chunking → embedding → indexing pipeline
with job tracking and status updates.
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ingestion.chunker import ChunkResult, DocumentChunker, CodeChunker
from ingestion.embedder import EmbeddingPipeline, get_embedding_pipeline
from ingestion.indexer import VectorIndexer, GraphIndexer, IndexerResult


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class IngestionJob:
    job_id: str
    source_type: str
    source_id: str
    content: str
    status: JobStatus = JobStatus.PENDING
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    embedded_chunks: List[Dict[str, Any]] = field(default_factory=list)
    total_chunks: int = 0
    indexed_count: int = 0
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
        elif self.status == JobStatus.CHUNKING:
            return 0.2
        elif self.status == JobStatus.EMBEDDING:
            return 0.5
        elif self.status == JobStatus.INDEXING:
            return 0.8
        return 0.0


class IngestionPipeline:
    def __init__(
        self,
        chunker: Optional[DocumentChunker] = None,
        code_chunker: Optional[CodeChunker] = None,
        embedder: Optional[EmbeddingPipeline] = None,
        vector_indexer: Optional[VectorIndexer] = None,
        graph_indexer: Optional[GraphIndexer] = None,
    ):
        self.chunker = chunker or DocumentChunker()
        self.code_chunker = code_chunker or CodeChunker()
        self.embedder = embedder or get_embedding_pipeline()
        self.vector_indexer = vector_indexer or VectorIndexer()
        self.graph_indexer = graph_indexer or GraphIndexer()
        self._jobs: Dict[str, IngestionJob] = {}

    async def ingest_document(
        self,
        content: str,
        source_id: str,
        source_type: str = "document",
        metadata: Optional[Dict[str, Any]] = None,
        index: bool = True,
    ) -> IngestionJob:
        job = IngestionJob(
            job_id=str(uuid.uuid4()),
            source_type=source_type,
            source_id=source_id,
            content=content,
            metadata=metadata or {},
        )
        self._jobs[job.job_id] = job

        try:
            job.status = JobStatus.CHUNKING

            if source_type == "code":
                chunk_result = self.code_chunker.chunk(content, source_id)
            else:
                chunk_result = self.chunker.chunk(content, source_id)

            chunks = [
                {
                    "id": c.id,
                    "content": c.content,
                    "source_id": source_id,
                    "source_type": source_type,
                    "chunk_index": c.chunk_index,
                    "metadata": {**c.metadata, **job.metadata},
                }
                for c in chunk_result.chunks
            ]

            job.chunks = chunks
            job.total_chunks = len(chunks)
            job.status = JobStatus.EMBEDDING

            embedded = await self.embedder.embed_chunks(chunks)
            job.embedded_chunks = embedded
            job.status = JobStatus.INDEXING

            if index and embedded:
                index_result = await self.vector_indexer.index_chunks(embedded)
                job.indexed_count = index_result.indexed_count

            job.status = JobStatus.COMPLETED
            job.updated_at = time.time()

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.updated_at = time.time()

        return job

    async def ingest_batch(
        self,
        documents: List[Dict[str, str]],
        parallel: bool = True,
    ) -> List[IngestionJob]:
        if parallel:
            import asyncio

            tasks = [
                self.ingest_document(
                    doc["content"], doc["id"], doc.get("type", "document")
                )
                for doc in documents
            ]
            jobs = await asyncio.gather(*tasks, return_exceptions=True)
            return [j for j in jobs if isinstance(j, IngestionJob)]
        else:
            jobs = []
            for doc in documents:
                job = await self.ingest_document(
                    doc["content"], doc["id"], doc.get("type", "document")
                )
                jobs.append(job)
            return jobs

    async def ingest_codebase(
        self,
        files: Dict[str, str],
        index_graph: bool = False,
    ) -> IngestionJob:
        import time

        job = IngestionJob(
            job_id=str(uuid.uuid4()),
            source_type="codebase",
            source_id="batch",
            content="",
            metadata={"file_count": len(files)},
        )
        self._jobs[job.job_id] = job

        try:
            job.status = JobStatus.CHUNKING
            all_chunks = []
            all_entities = []

            for file_path, content in files.items():
                chunk_result = self.code_chunker.chunk_file(file_path, content)
                for c in chunk_result.chunks:
                    all_chunks.append(
                        {
                            "id": c.id,
                            "content": c.content,
                            "source_id": chunk_result.source_id,
                            "source_type": "code",
                            "chunk_index": c.chunk_index,
                            "metadata": {
                                **c.metadata,
                                "file_path": file_path,
                            },
                        }
                    )
                    if c.metadata.get("entity_type") and c.metadata.get("entity_name"):
                        all_entities.append(
                            {
                                "id": c.id,
                                "node_type": c.metadata["entity_type"],
                                "properties": {
                                    "name": c.metadata["entity_name"],
                                    "file_path": file_path,
                                },
                            }
                        )

            job.chunks = all_chunks
            job.total_chunks = len(all_chunks)
            job.status = JobStatus.EMBEDDING

            all_embedded = await self.embedder.embed_chunks(all_chunks)
            job.embedded_chunks = all_embedded
            job.status = JobStatus.INDEXING

            index_result = await self.vector_indexer.index_chunks(all_embedded)
            job.indexed_count = index_result.indexed_count

            if index_graph and all_entities:
                await self.graph_indexer.index_nodes(all_entities)

            if index_result.indexed_count == 0:
                job.status = JobStatus.FAILED
                job.error = "No chunks were indexed"
            else:
                job.status = JobStatus.COMPLETED

            job.updated_at = time.time()

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.updated_at = time.time()

        return job

    def get_job(self, job_id: str) -> Optional[IngestionJob]:
        return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        jobs = list(self._jobs.values())[-limit:]
        return [
            {
                "job_id": j.job_id,
                "source_id": j.source_id,
                "source_type": j.source_type,
                "status": j.status.value,
                "progress": j.progress,
                "total_chunks": j.total_chunks,
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
            JobStatus.PENDING,
            JobStatus.CHUNKING,
            JobStatus.EMBEDDING,
            JobStatus.INDEXING,
        ):
            job.status = JobStatus.FAILED
            job.error = "Cancelled by user"
            return True
        return False


_pipeline: Optional[IngestionPipeline] = None


def get_ingestion_pipeline() -> IngestionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = IngestionPipeline()
    return _pipeline
