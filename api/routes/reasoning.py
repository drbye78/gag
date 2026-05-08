from fastapi import APIRouter, Depends

from api.models.request import CitationRequest, ReasoningRequest, RerankRequest
from api.models.response import CitationResponse, ReasoningResponse, RerankResponse
from core.auth import require_authenticated

router = APIRouter(prefix="/reasoning", tags=["reasoning"])


@router.post("/chain", response_model=ReasoningResponse, dependencies=[Depends(require_authenticated)])
async def chain_reasoning(request: ReasoningRequest):
    from retrieval.reasoning import ReasoningMode, get_reasoning_engine

    engine = get_reasoning_engine(ReasoningMode.CHAIN_OF_THOUGHTS)
    result = await engine.reason(request.query, request.facts)

    return ReasoningResponse(
        query=result["query"],
        answer=result["answer"],
        reasoning_mode=result["reasoning_mode"],
        confidence=result["confidence"],
        steps=[
            {"thought": s.thought, "action": s.action, "observation": s.observation}
            for s in result.get("steps", [])
        ],
    )


@router.post("/entity", response_model=ReasoningResponse, dependencies=[Depends(require_authenticated)])
async def entity_reasoning(request: ReasoningRequest):
    from retrieval.reasoning.entity_aware import get_entity_aware_reasoning_engine

    engine = get_entity_aware_reasoning_engine()
    result = await engine.reason(request.query, request.facts)

    return ReasoningResponse(
        query=result["query"],
        answer=result["answer"],
        reasoning_mode=result["reasoning_mode"],
        confidence=result["confidence"],
        steps=[
            {"thought": s.thought, "action": s.action, "observation": s.observation}
            for s in result.get("steps", [])
        ],
    )


rerank_router = APIRouter(prefix="/rerank", tags=["rerank"])


@rerank_router.post("", response_model=RerankResponse, dependencies=[Depends(require_authenticated)])
async def rerank(request: RerankRequest):
    from retrieval.rerank import get_rerank_pipeline

    pipeline = get_rerank_pipeline()
    reranked = await pipeline.rerank(request.query, request.results)

    return RerankResponse(
        query=request.query,
        results=[
            {"content": r.content, "score": r.score, "id": r.node_id} for r in reranked
        ],
        reranked=True,
    )


citations_router = APIRouter(prefix="/citations", tags=["citations"])


@citations_router.post("", response_model=CitationResponse, dependencies=[Depends(require_authenticated)])
async def generate_citations(request: CitationRequest):
    from retrieval.citations import CitationBuilder, CitationStyle

    style = (
        CitationStyle(request.style) if request.style else CitationStyle.PARENTHETICAL
    )
    builder = CitationBuilder(style=style)

    annotated = builder.build(request.answer, request.sources)

    return CitationResponse(
        answer=annotated.answer,
        citations=[
            {"id": c.id, "confidence": c.confidence} for c in annotated.citations
        ],
        sources=[
            {"source_id": s.source_id, "content": s.content[:100]}
            for s in annotated.sources
        ],
    )
