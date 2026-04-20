from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from core.pipeline import get_knowledge_pipeline, get_explanation_engine
from core.adapters import get_adapter_registry
from core.patterns import get_pattern_library
from core.constraints import get_constraint_engine
from models.ir import IRFeature, PlatformContext

router = APIRouter(prefix="/adapter", tags=["Platform Adapter"])


class AdapterQueryRequest(BaseModel):
    query: str
    platform: str = "sap"
    auto_detect: bool = False


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


@router.post("/query", response_model=AdapterQueryResponse)
async def process_with_adapter(req: AdapterQueryRequest):
    pipeline = get_knowledge_pipeline()
    registry = get_adapter_registry()

    if req.auto_detect:
        features = IRFeature()
        features_dict = {"query": req.query}
        feature_str = req.query.lower()

        detect_rules = {
            "sap": ["xsuaa", "hana", "btp", "cap", "cloudfoundry", "kyma"],
            "tanzu": ["tanzu", "pivotal", "spring", "kubernetes"],
            "powerplatform": ["powerapps", "powerautomate", "dataverse"],
        }
        for platform_id, keywords in detect_rules.items():
            if any(kw in feature_str for kw in keywords):
                req.platform = platform_id
                break

    adapter = registry.get(req.platform)
    if not adapter:
        raise HTTPException(
            status_code=404,
            detail=f"Platform '{req.platform}' not found. Available: {registry.list_platforms()}"
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