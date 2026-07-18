"""Query and reasoning endpoints — extracted from api/main.py."""
import base64
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from core.auth import require_authenticated

logger = logging.getLogger(__name__)
router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    query: str
    sources: Optional[List[str]] = None
    limit: Optional[int] = 10

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must not be empty")
        return v.strip()


class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    validation: Optional[Dict[str, Any]] = None
    intent: Optional[str] = None
    reliable: bool = True


class ReasoningRequest(BaseModel):
    query: str
    facts: List[Dict[str, Any]]
    mode: Optional[str] = "chain_of_thoughts"

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must not be empty")
        return v.strip()


class ReasoningResponse(BaseModel):
    query: str
    answer: str
    reasoning_mode: str
    confidence: float
    steps: List[Dict[str, Any]]


class RerankRequest(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    provider: Optional[str] = "cohere"
    strategy: Optional[str] = "single"

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must not be empty")
        return v.strip()


class RerankResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    reranked: bool


class CitationRequest(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    style: Optional[str] = "parenthetical"

    @field_validator("answer")
    @classmethod
    def answer_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("answer must not be empty")
        return v.strip()


class CitationResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]


@router.post("/query", response_model=QueryResponse, dependencies=[Depends(require_authenticated)])
async def query(request: QueryRequest):
    from agents.orchestration import get_orchestration_engine
    engine = get_orchestration_engine()
    result = await engine.execute(request.query, ir_context={}, max_iterations=None)
    validation = result.get("validation", {})
    reliable = validation.get("valid", True) if validation else True
    return QueryResponse(
        query=result["query"],
        answer=result["answer"],
        sources=result.get("retrieval_results", {}).get("results", []),
        metadata=result.get("metadata", {}),
        validation=validation,
        intent=result.get("intent"),
        reliable=reliable,
    )


@router.post("/hybrid/enhanced", dependencies=[Depends(require_authenticated)])
async def enhanced_search(request: QueryRequest):
    from retrieval.hybrid import get_enhanced_hybrid_retriever
    retriever = get_enhanced_hybrid_retriever()
    return await retriever.search_with_enhanced_reasoning(request.query, limit=request.limit or 10)


@router.post("/reasoning/chain", response_model=ReasoningResponse, dependencies=[Depends(require_authenticated)])
async def chain_reasoning(request: ReasoningRequest):
    from retrieval.reasoning import ReasoningMode, get_reasoning_engine
    engine = get_reasoning_engine(ReasoningMode.CHAIN_OF_THOUGHTS)
    result = await engine.reason(request.query, request.facts)
    return ReasoningResponse(
        query=result["query"], answer=result["answer"],
        reasoning_mode=result["reasoning_mode"], confidence=result["confidence"],
        steps=[{"thought": s.thought, "action": s.action, "observation": s.observation} for s in result.get("steps", [])],
    )


@router.post("/reasoning/entity", response_model=ReasoningResponse, dependencies=[Depends(require_authenticated)])
async def entity_reasoning(request: ReasoningRequest):
    from retrieval.reasoning.entity_aware import get_entity_aware_reasoning_engine
    engine = get_entity_aware_reasoning_engine()
    result = await engine.reason(request.query, request.facts)
    return ReasoningResponse(
        query=result["query"], answer=result["answer"],
        reasoning_mode=result["reasoning_mode"], confidence=result["confidence"],
        steps=[{"thought": s.thought, "action": s.action, "observation": s.observation} for s in result.get("steps", [])],
    )


@router.post("/rerank", response_model=RerankResponse, dependencies=[Depends(require_authenticated)])
async def rerank(request: RerankRequest):
    from retrieval.rerank import get_rerank_pipeline
    pipeline = get_rerank_pipeline()
    reranked = await pipeline.rerank(request.query, request.results)
    return RerankResponse(
        query=request.query,
        results=[{"content": r.content, "score": r.score, "id": r.node_id} for r in reranked],
        reranked=True,
    )


@router.post("/citations", response_model=CitationResponse, dependencies=[Depends(require_authenticated)])
async def generate_citations(request: CitationRequest):
    from retrieval.citations import CitationBuilder, CitationStyle
    style = CitationStyle(request.style) if request.style else CitationStyle.PARENTHETICAL
    builder = CitationBuilder(style=style)
    annotated = builder.build(request.answer, request.sources)
    return CitationResponse(
        answer=annotated.answer,
        citations=[{"id": c.id, "confidence": c.confidence} for c in annotated.citations],
        sources=[{"source_id": s.source_id, "content": s.content[:100]} for s in annotated.sources],
    )
