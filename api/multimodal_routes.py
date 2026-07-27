"""Entity cache, multimodal, and diagram endpoints — extracted from api/main.py."""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.auth import require_authenticated

logger = logging.getLogger(__name__)
router = APIRouter(tags=["multimodal"])


# --- Entity Cache ---

class EntityCacheStatsResponse(BaseModel):
    size: int
    capacity: int
    hit_rate: float
    hits: int
    misses: int
    utilization_pct: float
    oldest_entry: Optional[Dict[str, Any]] = None

class EntityCacheInvalidateRequest(BaseModel):
    entity_name: Optional[str] = None

class EntityCacheInvalidateResponse(BaseModel):
    invalidated: bool
    entity_name: Optional[str] = None
    message: str


@router.get("/entity/cache/stats", response_model=EntityCacheStatsResponse, dependencies=[Depends(require_authenticated)])
async def entity_cache_stats():
    from retrieval.hybrid import get_enhanced_hybrid_retriever
    retriever = get_enhanced_hybrid_retriever()
    stats = await retriever.get_entity_cache_stats()
    return EntityCacheStatsResponse(
        size=stats["size"], capacity=stats["capacity"], hit_rate=stats["hit_rate"],
        hits=stats["hits"], misses=stats["misses"], utilization_pct=stats["utilization_pct"],
        oldest_entry=stats.get("oldest_entry"),
    )


@router.post("/entity/cache/invalidate", response_model=EntityCacheInvalidateResponse, dependencies=[Depends(require_authenticated)])
async def entity_cache_invalidate(request: EntityCacheInvalidateRequest):
    from retrieval.hybrid import get_enhanced_hybrid_retriever
    retriever = get_enhanced_hybrid_retriever()
    success = await retriever.invalidate_entity_cache(request.entity_name)
    return EntityCacheInvalidateResponse(
        invalidated=success, entity_name=request.entity_name,
        message="Cache cleared" if not request.entity_name else f"Invalidated '{request.entity_name}'",
    )


# --- Multimodal ---

class ImageExtractionRequest(BaseModel):
    image_url: str
    prompt: Optional[str] = "Extract all text from this image"

    from pydantic import field_validator
    @field_validator("image_url")
    @classmethod
    def image_url_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("image_url must not be empty")
        return v.strip()

class ImageExtractionResponse(BaseModel):
    text: str
    metadata: Dict[str, Any]

class ColPALSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10

class ColPALSearchResponse(BaseModel):
    query: str
    results: Any
    method: str = "colpal"
    count: int

class UISketchSearchRequest(BaseModel):
    sketch_data: str
    limit: Optional[int] = 10

class UISketchSearchResponse(BaseModel):
    results: Any
    method: str = "ui_sketch"
    count: int

class DiagramExtractRequest(BaseModel):
    content: Optional[str] = None
    image_url: Optional[str] = None
    source: Optional[str] = None
    enrich: bool = False

class DiagramExtractResponse(BaseModel):
    diagram_id: str
    diagram_type: str
    title: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    extraction_confidence: float

class DiagramSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10
    diagram_types: Optional[List[str]] = None

class DiagramSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    count: int


@router.post("/multimodal/extract", response_model=ImageExtractionResponse, dependencies=[Depends(require_authenticated)])
async def extract_from_image(request: ImageExtractionRequest):
    from multimodal.vlm import get_vlm_processor
    processor = get_vlm_processor()
    result = await processor.extract_for_ir(request.image_url, title=None)
    return ImageExtractionResponse(text=result.get("content", ""), metadata={})


@router.post("/search/colpal", response_model=ColPALSearchResponse, dependencies=[Depends(require_authenticated)])
async def search_colpal(request: ColPALSearchRequest):
    from ui.retriever import get_ui_retriever
    retriever = get_ui_retriever()
    results = await retriever.search_combined(element_types=[], limit=request.limit or 10)
    return ColPALSearchResponse(query=request.query, results=results, method="colpal", count=len(results))


@router.post("/search/ui-sketch", response_model=UISketchSearchResponse, dependencies=[Depends(require_authenticated)])
async def search_ui_sketch(request: UISketchSearchRequest):
    from ui.retriever import get_ui_retriever
    retriever = get_ui_retriever()
    results = await retriever.search_combined(element_types=[], limit=request.limit or 10)
    return UISketchSearchResponse(results=results, method="ui_sketch", count=len(results))


@router.post("/multimodal/diagram/extract", dependencies=[Depends(require_authenticated)])
async def extract_diagram(request: DiagramExtractRequest):
    from multimodal.diagram_ir import get_diagram_ir_builder
    builder = get_diagram_ir_builder()
    if request.image_url:
        ir = await builder.from_image(request.image_url, source=request.source)
    elif request.content:
        ir = await builder.from_text(request.content, source=request.source)
    else:
        from multimodal.diagram_ir import DiagramIR
        ir = DiagramIR(id="empty", diagram_type="unknown")
    if request.enrich and ir.nodes:
        ir = await builder.enrich(ir)
    return DiagramExtractResponse(
        diagram_id=ir.id, diagram_type=ir.diagram_type, title=ir.title,
        nodes=[n.to_dict() for n in ir.nodes], edges=[e.to_dict() for e in ir.edges],
        extraction_confidence=ir.extraction_confidence,
    )


@router.post("/multimodal/diagram/search", dependencies=[Depends(require_authenticated)])
async def search_diagram(request: DiagramSearchRequest):
    from multimodal.diagram_registry import DiagramRegistry
    registry = DiagramRegistry(use_qdrant=False, use_falkor=False)
    results = await registry.search(request.query, limit=request.limit or 10, diagram_types=request.diagram_types)
    return DiagramSearchResponse(results=[r.ir.to_dict() for r in results], count=len(results))


@router.get("/multimodal/diagram/{diagram_id}", dependencies=[Depends(require_authenticated)])
async def get_diagram(diagram_id: str):
    from multimodal.diagram_registry import DiagramRegistry
    registry = DiagramRegistry(use_qdrant=False, use_falkor=False)
    ir = await registry.get_by_id(diagram_id)
    if not ir:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return ir.to_dict()


@router.get("/multimodal/diagram/visualize/{diagram_id}", dependencies=[Depends(require_authenticated)])
async def visualize_diagram(diagram_id: str):
    from multimodal.diagram_registry import DiagramRegistry
    registry = DiagramRegistry(use_qdrant=False, use_falkor=False)
    graph = await registry.get_graph(diagram_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return {"graph": graph}
