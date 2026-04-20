from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from core.knowledge.resolver import get_resolver
from core.knowledge.graph import get_knowledge_graph, NodeType
from core.knowledge.taxonomy import get_patterns
from core.knowledge.constraints import get_rule_engine

router = APIRouter(prefix="/knowledge", tags=["Knowledge"])


class KnowledgeQueryRequest(BaseModel):
    query: str


class KnowledgeQueryResponse(BaseModel):
    query: str
    platform: Optional[str]
    intent: str
    entities: List[Dict[str, Any]]
    patterns_matched: List[Dict[str, Any]]
    constraint_violations: List[Dict[str, Any]]
    reasoning: str
    can_proceed: bool


@router.post("/query", response_model=KnowledgeQueryResponse)
async def knowledge_query(req: KnowledgeQueryRequest):
    resolver = get_resolver()
    result = await resolver.resolve(req.query)
    
    return KnowledgeQueryResponse(
        query=result.query,
        platform=result.platform,
        intent=result.intent.primary.value if result.intent else "unknown",
        entities=[
            {"id": e.id, "name": e.name, "type": e.type, "confidence": e.confidence}
            for e in result.entities_found
        ],
        patterns_matched=[
            {"id": p.pattern_id, "name": p.pattern_name, "score": p.score}
            for p in result.patterns_matched
        ],
        constraint_violations=[
            {"message": v.message, "fix": v.fix, "severity": v.severity}
            for v in result.constraint_violations
        ],
        reasoning=result.reasoning,
        can_proceed=result.can_proceed,
    )


@router.get("/graph")
async def get_graph():
    graph = get_knowledge_graph()
    return {
        "nodes": [
            {"id": n.id, "name": n.name, "type": n.type.value}
            for n in graph.nodes.values()
        ],
        "edges": [
            {"source": e.source_id, "target": e.target_id, "type": e.type.value}
            for e in graph.edges
        ],
    }


@router.get("/patterns")
async def list_patterns():
    patterns = get_patterns()
    return {
        "patterns": [
            {
                "id": p.id,
                "name": p.name,
                "domain": p.domain.value,
                "quality_impact": p.quality_impact,
            }
            for p in patterns
        ]
    }


@router.get("/constraints/{platform}")
async def list_constraints(platform: str):
    engine = get_rule_engine()
    violations = engine.evaluate({"platform": platform}, [platform])
    return {
        "platform": platform,
        "violations": [
            {
                "id": v.rule.id,
                "name": v.rule.name,
                "message": v.message,
                "severity": v.severity,
            }
            for v in violations
        ],
    }