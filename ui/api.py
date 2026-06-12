"""FastAPI router for UI sketch endpoints."""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ui", tags=["ui"])


class UIAnalyzeRequest(BaseModel):
    image_url: str
    title: Optional[str] = None


class UIElementResult(BaseModel):
    element_id: str
    element_type: str
    label: Optional[str] = None
    confidence: float


class UIAnalyzeResponse(BaseModel):
    sketch_id: str
    title: str
    format_type: str
    page_type: Optional[str] = None
    elements: list[UIElementResult]
    element_count: int
    source_type_confidence: float
    warnings: list[str] = []


class UISuggestRequest(BaseModel):
    ui_sketch_id: Optional[str] = None
    image_url: Optional[str] = None
    detail_level: int = 1


class UISuggestResponse(BaseModel):
    sketch_id: Optional[str] = None
    suggestions: list[dict]
    detail_level: int


@router.post("/analyze", response_model=UIAnalyzeResponse)
async def analyze_ui(request: UIAnalyzeRequest):
    from ui.evidence_aggregator import EvidenceAggregator
    from ui.graph_builder import UIGraphBuilder
    from ui.vlm_extractor import VLMUIExtractor

    extractor = VLMUIExtractor()
    vlm_schema = await extractor.extract(request.image_url)

    if vlm_schema is None:
        raise HTTPException(status_code=400, detail="Failed to extract UI from image")

    aggregator = EvidenceAggregator()
    result = aggregator.aggregate(image_url=request.image_url, vlm_schema=vlm_schema)

    # Get ColPali visual embedding
    try:
        from ui.colpali_integration import get_ui_visual_indexer

        visual_indexer = get_ui_visual_indexer()
        embedding = await visual_indexer.get_embedding(request.image_url)
        if embedding is not None:
            emb_attr = getattr(embedding, "embeddings", None)
            if emb_attr is not None:
                emb_tensor = getattr(emb_attr, "numel", lambda: 0)()
                if emb_tensor and emb_tensor > 0:
                    visual_embedding_list = (
                        emb_attr[0].cpu().tolist() if hasattr(emb_attr[0], "cpu") else None
                    )
                    if visual_embedding_list:
                        result = aggregator.aggregate(
                            image_url=request.image_url,
                            vlm_schema=vlm_schema,
                            visual_embedding=visual_embedding_list,
                        )
    except Exception as e:
        logger.debug("ColPali embedding failed in /ui/analyze: %s", e)

    graph_builder = UIGraphBuilder()
    graph_result = await graph_builder.build(result)
    if not graph_result.get("success"):
        logger.warning("UI graph build failed: %s", graph_result.get("error"))

    warnings = []
    if result.extraction_metadata.get("low_confidence_warning"):
        warnings.append("Low extraction confidence")

    return UIAnalyzeResponse(
        sketch_id=result.sketch.sketch_id,
        title=result.sketch.title,
        format_type=result.sketch.format_type,
        page_type=result.sketch.page_type,
        elements=[
            UIElementResult(
                element_id=e.element_id,
                element_type=e.element_type,
                label=e.label,
                confidence=e.confidence,
            )
            for e in result.elements
        ],
        element_count=len(result.elements),
        source_type_confidence=result.source_type_confidence,
        warnings=warnings,
    )


@router.post("/suggest", response_model=UISuggestResponse)
async def suggest_implementation(request: UISuggestRequest):
    from tools.base import ToolInput
    from ui.suggestion_tool import UISuggestionTool

    if not request.ui_sketch_id and not request.image_url:
        raise HTTPException(status_code=400, detail="Provide ui_sketch_id or image_url")

    tool = UISuggestionTool()
    args = {
        "ui_sketch_id": request.ui_sketch_id,
        "image_url": request.image_url,
        "detail_level": min(max(request.detail_level, 1), 3),
    }
    result = await tool.execute(ToolInput(args=args))
    if result.error:
        raise HTTPException(status_code=500, detail=result.error)

    return UISuggestResponse(
        sketch_id=request.ui_sketch_id,
        suggestions=result.result.get("suggestions", []),
        detail_level=args["detail_level"],
    )


class UIIngestRequest(BaseModel):
    image_url: str
    title: Optional[str] = None
    enable_vector_index: bool = True
    enable_graph_index: bool = True


class UIIngestResponse(BaseModel):
    job_id: str
    image_url: str
    status: str
    progress: float
    sketch_id: Optional[str] = None
    element_count: int = 0
    extraction_confidence: float = 0.0
    error: Optional[str] = None


class UIBatchRequest(BaseModel):
    items: List[Dict[str, str]]
    parallel: bool = True


class UIBatchResponse(BaseModel):
    job_ids: List[str]
    total: int


@router.post("/ingest", response_model=UIIngestResponse)
async def ingest_ui(request: UIIngestRequest):
    from ui.pipeline import get_ui_ingestion_pipeline

    pipeline = get_ui_ingestion_pipeline()
    result = await pipeline.ingest(
        image_url=request.image_url,
        title=request.title,
    )

    return UIIngestResponse(
        job_id=result.job.job_id,
        image_url=result.job.image_url,
        status=result.job.status.value,
        progress=result.job.progress,
        sketch_id=result.job.sketch_id,
        element_count=result.job.element_count,
        extraction_confidence=result.job.extraction_confidence,
        error=result.job.error,
    )


@router.post("/batch", response_model=UIBatchResponse)
async def batch_ingest_ui(request: UIBatchRequest):
    from ui.pipeline import get_ui_ingestion_pipeline

    pipeline = get_ui_ingestion_pipeline()
    results = await pipeline.batch_ingest(request.items)

    job_ids = [r.job.job_id for r in results if r is not None]

    return UIBatchResponse(
        job_ids=job_ids,
        total=len(job_ids),
    )


@router.get("/jobs")
async def list_ui_jobs(limit: int = 50):
    from ui.ingestion_job import get_ui_job_registry

    registry = get_ui_job_registry()
    jobs = await registry.list_recent(limit)

    return {
        "jobs": [
            {
                "job_id": j.job_id,
                "image_url": j.image_url,
                "status": j.status.value,
                "progress": j.progress,
                "created_at": j.created_at,
            }
            for j in jobs
        ],
        "total": len(jobs),
    }


@router.get("/jobs/{job_id}")
async def get_ui_job(job_id: str):
    from ui.ingestion_job import get_ui_job_registry

    registry = get_ui_job_registry()
    job = await registry.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return {
        "job_id": job.job_id,
        "image_url": job.image_url,
        "title": job.title,
        "status": job.status.value,
        "progress": job.progress,
        "sketch_id": job.sketch_id,
        "element_count": job.element_count,
        "extraction_confidence": job.extraction_confidence,
        "indexing_success": job.indexing_success,
        "error": job.error,
        "metadata": job.metadata,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }
