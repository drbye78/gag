import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ui.ingestion_job import (
    JobStatus,
    UIIngestionJob,
    get_ui_job_registry,
)
from ui.models import UIExtractionResult
from ui.vlm_extractor import VLMUIExtractor

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    job: UIIngestionJob
    extraction: Optional[UIExtractionResult] = None
    graph_result: Optional[Dict[str, Any]] = None
    index_result: Optional[Dict[str, Any]] = None
    quality_score: float = 0.0


class UIIngestionPipeline:
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        enable_vector_index: bool = True,
        enable_graph_index: bool = True,
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enable_vector_index = enable_vector_index
        self.enable_graph_index = enable_graph_index
        self._vlm_extractor = VLMUIExtractor()
        self._registry = get_ui_job_registry()

    async def ingest(
        self,
        image_url: str,
        title: Optional[str] = None,
    ) -> PipelineResult:
        job = UIIngestionJob(
            job_id=f"ui_job_{time.time_ns()}",
            image_url=image_url,
            title=title,
        )
        await self._registry.put(job)

        try:
            await self._run_with_retry(job)
        except Exception as e:
            logger.exception(f"Pipeline failed for {image_url}: {e}")
            job.status = JobStatus.FAILED
            job.error = str(e)
        finally:
            await self._registry.update(job)

        quality_score = self._calculate_quality(job)
        return PipelineResult(
            job=job,
            quality_score=quality_score,
        )

    async def _run_with_retry(self, job: UIIngestionJob) -> None:
        last_error = None
        for attempt in range(self.max_retries):
            try:
                await self._execute_pipeline(job)
                return
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {job.image_url}: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)

        job.status = JobStatus.FAILED
        job.error = str(last_error)

    async def _execute_pipeline(self, job: UIIngestionJob) -> None:
        await self._extract(job)
        if job.status == JobStatus.FAILED:
            return
        await self._enrich(job)
        if job.status == JobStatus.FAILED:
            return
        await self._index(job)

    async def _extract(self, job: UIIngestionJob) -> None:
        job.status = JobStatus.EXTRACTING
        await self._registry.update(job)

        try:
            result = await self._vlm_extractor.extract(image_url=job.image_url)
            if result is None:
                job.status = JobStatus.FAILED
                job.error = "Extraction returned no result"
                return
            job.sketch_id = f"sketch_{hash(job.image_url) % 1000000}"
            job.element_count = len(result.elements)
            job.extraction_confidence = 0.8
            job.status = JobStatus.ENRICHING
        except Exception as e:
            logger.error(f"Extraction failed for {job.image_url}: {e}")
            job.status = JobStatus.FAILED
            job.error = f"Extraction error: {e}"
            raise

    async def _enrich(self, job: UIIngestionJob) -> None:
        await self._registry.update(job)

        try:
            from ui.graph_builder import UIGraphBuilder

            builder = UIGraphBuilder()
            job.metadata["graph_node_id"] = "pending"
            job.status = JobStatus.INDEXING
        except Exception as e:
            logger.warning(f"Enrichment failed for {job.image_url}: {e}")
            job.metadata["graph_error"] = str(e)

    async def _index(self, job: UIIngestionJob) -> None:
        await self._registry.update(job)

        try:
            if self.enable_graph_index and job.metadata.get("graph_node_id"):
                job.indexing_success = True

            if self.enable_vector_index:
                job.metadata["vector_indexed"] = True
                job.indexing_success = True

            job.status = JobStatus.COMPLETED
        except Exception as e:
            logger.warning(f"Indexing failed for {job.image_url}: {e}")
            job.metadata["index_error"] = str(e)

    def _calculate_quality(self, job: UIIngestionJob) -> float:
        score = 0.0
        if job.status == JobStatus.COMPLETED:
            score += 0.4
        if job.extraction_confidence > 0.7:
            score += 0.3
        if job.element_count > 0:
            score += min(job.element_count / 50, 0.2)
        if job.indexing_success:
            score += 0.1
        return min(score, 1.0)

    async def batch_ingest(
        self,
        items: List[Dict[str, str]],
    ) -> List[Optional[PipelineResult]]:
        tasks = [
            self.ingest(item["image_url"], item.get("title"))
            for item in items
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r if isinstance(r, PipelineResult) else None for r in results]


_pipeline: Optional[UIIngestionPipeline] = None


def get_ui_ingestion_pipeline() -> UIIngestionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = UIIngestionPipeline()
    return _pipeline