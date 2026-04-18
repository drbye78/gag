"""Ingestion orchestration with job lifecycle management and cleanup."""

import asyncio
import logging
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ingestion.chunker import ChunkResult, DocumentChunker, CodeChunker
from ingestion.embedder import EmbeddingPipeline, get_embedding_pipeline
from ingestion.indexer import VectorIndexer, GraphIndexer, IndexerResult
from core.config import get_settings
from core.errors import IngestionError

logger = logging.getLogger(__name__)


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


class JobRegistry:
    """Thread-safe LRU job registry with eviction."""

    def __init__(self, max_size: int = 1000, ttl_seconds: float = 3600.0):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._jobs: OrderedDict[str, IngestionJob] = OrderedDict()
        self._lock = asyncio.Lock()

    async def put(self, job: IngestionJob) -> None:
        async with self._lock:
            # Evict expired jobs first
            await self._evict_expired()
            # Evict oldest if at capacity
            while len(self._jobs) >= self.max_size:
                self._jobs.popitem(last=False)
            self._jobs[job.job_id] = job

    async def get(self, job_id: str) -> Optional[IngestionJob]:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job and self._is_expired(job):
                del self._jobs[job_id]
                return None
            if job:
                # Move to end (most recently used)
                self._jobs.move_to_end(job_id)
            return job

    async def list_recent(self, limit: int = 50) -> List[IngestionJob]:
        async with self._lock:
            await self._evict_expired()
            jobs = list(self._jobs.values())[-limit:]
            return [j for j in jobs if not self._is_expired(j)]

    async def remove(self, job_id: str) -> bool:
        async with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                return True
            return False

    async def clear_completed(self, older_than_seconds: float = 300) -> int:
        """Remove completed jobs older than specified seconds."""
        async with self._lock:
            cutoff = time.time() - older_than_seconds
            to_remove = [
                jid for jid, job in self._jobs.items()
                if job.status in (JobStatus.COMPLETED, JobStatus.FAILED)
                and job.updated_at < cutoff
            ]
            for jid in to_remove:
                del self._jobs[jid]
            return len(to_remove)

    def size(self) -> int:
        return len(self._jobs)

    def _is_expired(self, job: IngestionJob) -> bool:
        return time.time() - job.updated_at > self.ttl_seconds

    async def _evict_expired(self) -> None:
        expired = [jid for jid, job in self._jobs.items() if self._is_expired(job)]
        for jid in expired:
            del self._jobs[jid]


class IngestionPipeline:
    """Production-grade ingestion pipeline with job management and structured errors."""

    def __init__(
        self,
        chunker: Optional[DocumentChunker] = None,
        code_chunker: Optional[CodeChunker] = None,
        embedder: Optional[EmbeddingPipeline] = None,
        vector_indexer: Optional[VectorIndexer] = None,
        graph_indexer: Optional[GraphIndexer] = None,
        use_graphrag: bool = False,
        max_jobs: int = 1000,
    ):
        settings = get_settings()
        self.chunker = chunker or DocumentChunker()
        self.code_chunker = code_chunker or CodeChunker()
        self.embedder = embedder or get_embedding_pipeline()
        self.vector_indexer = vector_indexer or VectorIndexer()
        self.graph_indexer = graph_indexer or GraphIndexer()
        self.use_graphrag = use_graphrag
        self._graphrag_pipeline = None
        self._registry = JobRegistry(max_size=max_jobs)

    @property
    def graphrag_pipeline(self) -> Optional[Any]:
        if self._graphrag_pipeline is None and self.use_graphrag:
            from ingestion.graphrag import get_graphrag_pipeline
            settings = get_settings()
            self._graphrag_pipeline = get_graphrag_pipeline(
                use_llm_extraction=settings.graphrag_use_llm_extraction,
                use_structural_chunking=settings.graphrag_structural_chunking,
                incremental=settings.graphrag_incremental,
            )
        return self._graphrag_pipeline

    async def ingest_document(
        self,
        content: str,
        source_id: str,
        source_type: str = "document",
        metadata: Optional[Dict[str, Any]] = None,
        index: bool = True,
        use_graphrag: Optional[bool] = None,
    ) -> IngestionJob:
        use_gr = use_graphrag if use_graphrag is not None else self.use_graphrag

        if use_gr and self.graphrag_pipeline:
            return await self._ingest_with_graphrag(content, source_id, source_type, metadata, index)

        return await self._ingest_standard(content, source_id, source_type, metadata, index)

    async def _ingest_standard(
        self,
        content: str,
        source_id: str,
        source_type: str,
        metadata: Optional[Dict[str, Any]],
        index: bool,
    ) -> IngestionJob:
        job = IngestionJob(
            job_id=str(uuid.uuid4()),
            source_type=source_type,
            source_id=source_id,
            content=content,
            metadata=metadata or {},
        )
        await self._registry.put(job)

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
            logger.info("Ingestion job %s completed: %d chunks, %d indexed",
                       job.job_id, job.total_chunks, job.indexed_count)

        except Exception as e:
            logger.exception("Ingestion job %s failed: %s", job.job_id, e)
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.updated_at = time.time()

        return job

    async def _ingest_with_graphrag(
        self,
        content: str,
        source_id: str,
        source_type: str,
        metadata: Optional[Dict[str, Any]],
        index: bool,
    ) -> IngestionJob:
        gr_pipeline = self.graphrag_pipeline
        if gr_pipeline is None:
            raise IngestionError("GraphRAG pipeline not initialized", details={"use_graphrag": self.use_graphrag})

        job = IngestionJob(
            job_id=str(uuid.uuid4()),
            source_type=source_type,
            source_id=source_id,
            content=content,
            metadata=metadata or {},
        )
        await self._registry.put(job)

        try:
            job.status = JobStatus.CHUNKING

            graphrag_result = await gr_pipeline.process_document(
                content, source_id, source_type
            )

            chunks = [
                {
                    "id": c.id,
                    "content": c.content,
                    "source_id": source_id,
                    "source_type": source_type,
                    "chunk_index": c.chunk_index,
                    "metadata": {
                        **c.metadata,
                        **job.metadata,
                        "entities": [e.id for e in graphrag_result.entities if e.name.lower() in c.content.lower()][:10],
                        "entity_names": [e.name for e in graphrag_result.entities if e.name.lower() in c.content.lower()][:10],
                        "community_ids": [c.id for c in graphrag_result.communities],
                    },
                }
                for c in graphrag_result.chunks
            ]

            job.chunks = chunks
            job.total_chunks = len(chunks)
            job.metadata["graphrag_entities"] = len(graphrag_result.entities)
            job.metadata["graphrag_relationships"] = len(graphrag_result.relationships)
            job.metadata["graphrag_communities"] = len(graphrag_result.communities)
            job.status = JobStatus.EMBEDDING

            embedded = await self.embedder.embed_chunks(chunks)
            job.embedded_chunks = embedded
            job.status = JobStatus.INDEXING

            if index and embedded:
                index_result = await self.vector_indexer.index_chunks(embedded)
                job.indexed_count = index_result.indexed_count

            job.status = JobStatus.COMPLETED
            job.updated_at = time.time()
            logger.info("GraphRAG ingestion job %s completed: %d chunks, %d entities",
                       job.job_id, job.total_chunks, len(graphrag_result.entities))

        except Exception as e:
            logger.exception("GraphRAG ingestion job %s failed: %s", job.job_id, e)
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
        job = IngestionJob(
            job_id=str(uuid.uuid4()),
            source_type="codebase",
            source_id="batch",
            content="",
            metadata={"file_count": len(files)},
        )
        await self._registry.put(job)

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
            logger.info("Codebase ingestion job %s completed: %d files, %d chunks",
                       job.job_id, len(files), job.total_chunks)

        except Exception as e:
            logger.exception("Codebase ingestion job %s failed: %s", job.job_id, e)
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.updated_at = time.time()

        return job

    async def get_job(self, job_id: str) -> Optional[IngestionJob]:
        return await self._registry.get(job_id)

    async def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        jobs = await self._registry.list_recent(limit)
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

    async def cancel_job(self, job_id: str) -> bool:
        job = await self._registry.get(job_id)
        if job and job.status in (
            JobStatus.PENDING,
            JobStatus.CHUNKING,
            JobStatus.EMBEDDING,
            JobStatus.INDEXING,
        ):
            job.status = JobStatus.FAILED
            job.error = "Cancelled by user"
            job.updated_at = time.time()
            return True
        return False

    async def cleanup_completed(self, older_than_seconds: float = 300) -> int:
        """Remove completed/failed jobs older than specified seconds."""
        return await self._registry.clear_completed(older_than_seconds)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "registry_size": self._registry.size(),
            "max_size": self._registry.max_size,
            "ttl_seconds": self._registry.ttl_seconds,
        }


_pipeline: Optional[IngestionPipeline] = None


def get_ingestion_pipeline(use_graphrag: bool = False) -> IngestionPipeline:
    global _pipeline
    settings = get_settings()
    effective_use_graphrag = use_graphrag or settings.graphrag_enabled
    if _pipeline is None or _pipeline.use_graphrag != effective_use_graphrag:
        _pipeline = IngestionPipeline(use_graphrag=effective_use_graphrag)
    return _pipeline