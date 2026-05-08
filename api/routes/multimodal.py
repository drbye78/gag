from fastapi import APIRouter, Depends

from api.models.request import DiagramExtractRequest, ImageExtractionRequest
from api.models.response import DiagramExtractResponse, ImageExtractionResponse
from core.auth import require_authenticated

router = APIRouter(prefix="/multimodal", tags=["multimodal"])


@router.post("/extract", response_model=ImageExtractionResponse, dependencies=[Depends(require_authenticated)])
async def extract_from_image(request: ImageExtractionRequest):
    from multimodal.vlm import get_vlm_processor

    processor = get_vlm_processor()
    result = await processor.extract_for_ir(request.image_url, title=None)

    return ImageExtractionResponse(
        text=result.get("content", ""),
        metadata={},
    )


@router.post("/diagram/extract", dependencies=[Depends(require_authenticated)])
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
        diagram_id=ir.id,
        diagram_type=ir.diagram_type,
        title=ir.title,
        nodes=[n.to_dict() for n in ir.nodes],
        edges=[e.to_dict() for e in ir.edges],
        extraction_confidence=ir.extraction_confidence,
    )


@router.get("/diagram/{diagram_id}", dependencies=[Depends(require_authenticated)])
async def get_diagram(diagram_id: str):
    from multimodal.diagram_registry import DiagramRegistry

    registry = DiagramRegistry(use_qdrant=False, use_falkor=False)
    ir = await registry.get_by_id(diagram_id)

    if not ir:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Diagram not found")

    return ir.to_dict()


@router.get("/diagram/visualize/{diagram_id}", dependencies=[Depends(require_authenticated)])
async def visualize_diagram(diagram_id: str):
    from multimodal.diagram_registry import DiagramRegistry

    registry = DiagramRegistry(use_qdrant=False, use_falkor=False)
    graph = await registry.get_graph(diagram_id)

    if not graph:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Diagram not found")

    return {"graph": graph}
