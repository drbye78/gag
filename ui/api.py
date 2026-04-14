"""FastAPI router for UI sketch endpoints."""

import logging
from typing import Optional

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
    from ui.vlm_extractor import VLMUIExtractor
    from ui.evidence_aggregator import EvidenceAggregator
    from ui.graph_builder import UIGraphBuilder

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
        if embedding is not None and embedding.embeddings is not None:
            # Re-aggregate with embedding
            visual_embedding_list = embedding.embeddings[0].cpu().tolist() if embedding.embeddings.numel() > 0 else None
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
            UIElementResult(element_id=e.element_id, element_type=e.element_type,
                           label=e.label, confidence=e.confidence)
            for e in result.elements
        ],
        element_count=len(result.elements),
        source_type_confidence=result.source_type_confidence,
        warnings=warnings,
    )


@router.post("/suggest", response_model=UISuggestResponse)
async def suggest_implementation(request: UISuggestRequest):
    from ui.suggestion_tool import UISuggestionTool
    from tools.base import ToolInput

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
