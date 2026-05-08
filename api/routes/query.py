import asyncio

from fastapi import APIRouter, Depends

from api.models.request import QueryRequest
from api.models.response import QueryResponse
from core.auth import require_authenticated

router = APIRouter(prefix="/query", tags=["query"])

_semaphore = asyncio.Semaphore(50)


@router.post("", response_model=QueryResponse, dependencies=[Depends(require_authenticated)])
async def query(request: QueryRequest):
    from agents.orchestration import get_orchestration_engine

    async with _semaphore:
        engine = get_orchestration_engine()
        result = await engine.execute(request.query)

    return QueryResponse(
        query=result["query"],
        answer=result["answer"],
        sources=result.get("retrieval_results", {}).get("results", []),
        metadata=result.get("metadata", {}),
    )
