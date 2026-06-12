from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from core.adapters import get_adapter_registry
from core.auth import require_authenticated
from core.constraints import get_constraint_engine
from core.patterns import get_pattern_library
from core.pipeline import get_knowledge_pipeline
from models.ir import IRFeature, PlatformContext

router = APIRouter(
    prefix="/adapter", tags=["Platform Adapter"], dependencies=[Depends(require_authenticated)]
)


class _QueryFeatures:
    """Minimal feature view for auto-detection.

    Wraps the user's query so the registry's string-matching logic can
    inspect it without requiring a full IRFeature extraction pass.
    """

    def __init__(self, query: str) -> None:
        self._query = query

    def model_dump(self) -> Dict[str, str]:
        return {"query": self._query}


class AdapterQueryRequest(BaseModel):
    query: str
    platform: str = "sap"
    auto_detect: bool = False

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        registry = get_adapter_registry()
        available = registry.list_platforms()
        if v not in available:
            raise ValueError(f"Platform '{v}' not found. Available platforms: {available}")
        return v


class AdapterQueryResponse(BaseModel):
    query: str
    platform: str
    recommendations: List[Dict[str, Any]]
    patterns_matched: List[str]
    constraint_violations: List[Dict[str, Any]]
    config_templates: Dict[str, str]
    code_snippets: Dict[str, str]
    explanation: str
    confidence: float
    can_proceed: bool
    # -- Enhanced adapter output fields ---------------------------------------
    service_specs: List[Dict[str, Any]] = []
    compliance_matrix: List[Dict[str, Any]] = []
    cost_estimate: Optional[Dict[str, Any]] = None
    required_dependencies: List[str] = []
    portfolio_summary: Dict[str, int] = {}


@router.post("/query", response_model=AdapterQueryResponse)
async def process_with_adapter(req: AdapterQueryRequest):
    pipeline = get_knowledge_pipeline()
    registry = get_adapter_registry()

    if req.auto_detect:
        features = IRFeature()
        features_dict = {"query": req.query}
        feature_str = req.query.lower()

        # Delegate to the registry's canonical auto-detect (base.py)
        detected = registry.auto_detect(_QueryFeatures(req.query))
        req.platform = detected.platform_id

    adapter = registry.get(req.platform)
    if not adapter:
        raise HTTPException(
            status_code=404,
            detail=f"Platform '{req.platform}' not found. Available: {registry.list_platforms()}",
        )

    platform_ctx = PlatformContext(
        platform=req.platform,
        services=adapter.supported_services,
    )

    output = await pipeline.process(req.query, platform_ctx)

    return AdapterQueryResponse(
        query=req.query,
        platform=req.platform,
        recommendations=output.recommendations,
        patterns_matched=[p.get("name") for p in output.recommendations],
        constraint_violations=[],
        config_templates=output.config_templates,
        code_snippets=output.code_snippets,
        explanation=output.explanation,
        confidence=output.confidence,
        can_proceed=output.can_deploy,
        # -- New structured fields ------------------------------------------------
        service_specs=[s.model_dump() for s in output.service_specs],
        compliance_matrix=[cm.model_dump() for cm in output.compliance_matrix],
        cost_estimate=output.cost_estimate.model_dump() if output.cost_estimate is not None else None,
        required_dependencies=output.required_dependencies,
        portfolio_summary=output.portfolio_summary,
    )


@router.get("/platforms")
async def list_platforms():
    registry = get_adapter_registry()
    return {"platforms": registry.list_platforms()}


@router.get("/patterns")
async def list_patterns(domain: Optional[str] = None):
    library = get_pattern_library()
    if domain:
        patterns = library.list_by_domain(domain)
    else:
        patterns = library.all()

    return {
        "patterns": [
            {
                "id": p.id,
                "name": p.name,
                "domain": p.domain,
                "triggers": p.triggers,
                "components": p.components,
                "priority": p.priority,
            }
            for p in patterns
        ]
    }


@router.get("/constraints/{platform}")
async def get_platform_constraints(platform: str):
    engine = get_constraint_engine()
    violations = engine.evaluate({}, platform)

    return {
        "platform": platform,
        "constraints": [
            {
                "id": v.constraint.id,
                "name": v.constraint.name,
                "message": v.message,
                "fix_hint": v.fix_hint,
                "severity": v.severity,
            }
            for v in violations
        ],
    }
