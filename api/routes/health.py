import asyncio

from fastapi import APIRouter

from api.models.response import HealthResponse

router = APIRouter(prefix="", tags=["health"])

_semaphore = asyncio.Semaphore(50)


@router.get("/health", response_model=HealthResponse, tags=["public"])
async def health():
    from core.health import get_health_checker

    checker = get_health_checker()
    status_info = await checker.get_status()

    return HealthResponse(
        status=status_info["status"],
        version="4.2.0",
    )


@router.get("/metrics", tags=["observability"])
async def metrics():
    from fastapi.responses import Response

    from core.prometheus_metrics import CONTENT_TYPE_LATEST, generate_latest

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
