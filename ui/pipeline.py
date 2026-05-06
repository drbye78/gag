import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.pool import get_http_pool
from graph.client import get_falkordb_client
from ui.ingestion_job import (
    JobStatus,
    UIIngestionJob,
    get_ui_job_registry,
)
from ui.models import UISketch, UIExtractionResult, UIElement
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
            job.metadata["elements"] = [
                {"element_type": str(getattr(e, "element_type", "unknown")), "label": str(getattr(e, "label", "")), "confidence": float(getattr(e, "confidence", 0.8))}
                for e in result.elements
            ]
            job.metadata["source_type"] = str(getattr(result, 'source_type', 'sketch'))
            job.extraction_confidence = float(getattr(result, 'source_type_confidence', 0.85) or 0.85)
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
            from graph.client import get_falkordb_client

            builder = UIGraphBuilder()
            db = get_falkordb_client()

            elements = job.metadata.get("elements", [])
            elements_data = [
                UIElement(
                    element_id=f"elem_{i}",
                    element_type=e.get("element_type", "unknown"),
                    label=e.get("label", ""),
                    confidence=e.get("confidence", 0.8),
                )
                for i, e in enumerate(elements)
            ]
            sketch = UISketch(
                sketch_id=job.sketch_id or "",
                title=job.title or "",
                source_url=job.image_url,
                format_type=job.metadata.get("source_type", "sketch"),
                ingestion_timestamp=datetime.now(),
            )

            extraction_result = UIExtractionResult(
                sketch=sketch,
                layout=None,
                elements=elements_data,
                source_type_confidence=job.extraction_confidence,
            )

            cypher = builder.build_cypher(extraction_result)
            if cypher:
                result = await db.execute(cypher)
                job.metadata["graph_node_id"] = job.sketch_id
                job.metadata["graph_cypher"] = cypher[:500]
            else:
                job.metadata["graph_node_id"] = job.sketch_id

            job.status = JobStatus.INDEXING
        except Exception as e:
            logger.error(f"Enrichment failed for {job.image_url}: {e}")
            job.metadata["graph_error"] = str(e)
            raise

    async def _index(self, job: UIIngestionJob) -> None:
        await self._registry.update(job)

        try:
            indexing_results = {}

            if self.enable_graph_index and job.metadata.get("graph_node_id"):
                indexing_results["graph"] = {"indexed": True, "node_id": job.metadata.get("graph_node_id")}

            if self.enable_vector_index:
                from ingestion.embedder import EmbeddingPipeline
                embedder = EmbeddingPipeline()

                text_content = f"{job.title or ''} {job.image_url}"
                elements = job.metadata.get("elements", [])
                for element in elements:
                    text_content += f" {element.get('label', '')} {element.get('element_type', '')}"

                if text_content.strip():
                    vector = await embedder.embed(text_content)
                    from core.pool import get_http_pool
                    pool = get_http_pool()
                    from core.config import get_settings
                    settings = get_settings()

                    qdrant_url = f"http://{settings.qdrant_host}:6333"
                    payload = {
                        "points": [{
                            "id": job.sketch_id,
                            "vector": vector,
                            "payload": {
                                "image_url": job.image_url,
                                "title": job.title,
                                "element_count": job.element_count,
                                "graph_node_id": job.metadata.get("graph_node_id"),
                            },
                        }],
                    }
                    try:
                        resp = await pool.post(
                            f"{qdrant_url}/collections/ui_sketches/points",
                            json=payload,
                            timeout=10.0,
                        )
                        if resp.status_code in (200, 201):
                            indexing_results["vector"] = {"indexed": True, "points": 1}
                        else:
                            indexing_results["vector"] = {"indexed": False, "error": f"Qdrant: {resp.status_code}"}
                    except Exception as ve:
                        indexing_results["vector"] = {"indexed": False, "error": str(ve)}

            job.indexing_success = True
            job.status = JobStatus.COMPLETED
            job.metadata["index_results"] = indexing_results
        except Exception as e:
            logger.error(f"Indexing failed for {job.image_url}: {e}")
            job.metadata["index_error"] = str(e)
            raise
            logger.error(f"Indexing failed for {job.image_url}: {e}")
            job.metadata["index_error"] = str(e)
            raise

    def _calculate_quality(self, job: UIIngestionJob) -> float:
        score = 0.0
        weights = {
            "completion": 0.25,
            "extraction": 0.30,
            "elements": 0.20,
            "graph_indexing": 0.15,
            "vector_indexing": 0.10,
        }

        if job.status == JobStatus.COMPLETED:
            score += weights["completion"]

        if job.extraction_confidence > 0.7:
            score += weights["extraction"] * job.extraction_confidence
        elif job.extraction_confidence > 0.5:
            score += weights["extraction"] * 0.5

        if job.element_count > 0:
            score += min(job.element_count / 50, 1.0) * weights["elements"]

        if job.metadata.get("graph_node_id") and job.metadata.get("graph_node_id") != "pending":
            score += weights["graph_indexing"]

        if job.metadata.get("index_results"):
            index_results = job.metadata.get("index_results", {})
            if index_results.get("vector", {}).get("indexed"):
                score += weights["vector_indexing"]
            elif index_results.get("graph", {}).get("indexed"):
                score += weights["vector_indexing"] * 0.5

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