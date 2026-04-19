from typing import Any, Dict, List, Optional
from models.ir import IRNode, IRFeature, PlatformContext, EnrichedIR
from core.patterns import (
    PatternMatcher,
    PatternScorer,
    get_pattern_library,
    ConstraintViolation,
)
from core.constraints import get_constraint_engine
from core.adapters import AdapterInput, AdapterOutput, get_adapter_registry


class KnowledgeProcessingPipeline:
    def __init__(
        self,
        pattern_matcher: Optional[PatternMatcher] = None,
        constraint_engine=None,
        adapter_registry=None,
    ):
        self.pattern_matcher = pattern_matcher or PatternMatcher()
        self.constraint_engine = constraint_engine or get_constraint_engine()
        self.adapter_registry = adapter_registry or get_adapter_registry()
        self.pattern_scorer = PatternScorer()
    
    async def process(
        self,
        query: str,
        platform_context: PlatformContext,
        existing_ir: Optional[IRNode] = None,
    ) -> AdapterOutput:
        features = self._extract_features(existing_ir, query)
        
        pattern_results = self.pattern_matcher.match(features)
        
        violations = self.constraint_engine.evaluate(
            features.model_dump(),
            platform_context.platform
        )
        
        adapter = self.adapter_registry.get(platform_context.platform)
        if not adapter:
            adapter = self.adapter_registry.get_default()
        
        adapter_input = AdapterInput(
            ir_features=features,
            pattern_matches=pattern_results,
            constraint_violations=violations,
            platform_context=platform_context,
        )
        
        return adapter.transform_ir_to_platform(adapter_input)
    
    def _extract_features(
        self,
        ir_node: Optional[IRNode],
        query: str
    ) -> IRFeature:
        features = IRFeature()
        
        if ir_node:
            if hasattr(ir_node, "components") and ir_node.components:
                features.has_api = True
            
            if hasattr(ir_node, "technologies"):
                techs = [t.value if hasattr(t, "value") else str(t) for t in ir_node.technologies]
                features.has_database = any("hana" in t or "postgres" in t for t in techs)
        
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in ["event", "kafka", "async", "message"]):
            features.has_async = True
            features.has_event_driven = True
        
        if any(kw in query_lower for kw in ["auth", "login", "security"]):
            features.has_auth = True
        
        if any(kw in query_lower for kw in ["database", "storage", "hana", "sql"]):
            features.has_database = True
        
        if any(kw in query_lower for kw in ["api", "rest", "graphql", "endpoint"]):
            features.has_api = True
        
        if any(kw in query_lower for kw in ["ui", "web", "frontend", "screen"]):
            features.has_ui = True
        
        if any(kw in query_lower for kw in ["service", "microservice"]):
            features.has_microservices = True
        
        if any(kw in query_lower for kw in ["lambda", "function", "serverless"]):
            features.has_serverless = True
        
        if any(kw in query_lower for kw in ["container", "docker", "kubernetes", "k8s"]):
            features.has_container = True
        
        if any(kw in query_lower for kw in ["scale", "performance", "high availability"]):
            features.scalability_required = True
            features.high_availability_required = True
        
        if any(kw in query_lower for kw in ["multi", "tenant", "saas"]):
            features.multi_tenant = True
        
        return features


class ExplanationEngine:
    def explain(
        self,
        output: AdapterOutput,
        features: IRFeature,
        violations: List[ConstraintViolation],
    ) -> Dict[str, Any]:
        reasoning = []
        
        for rec in output.recommendations[:3]:
            reasoning.append({
                "type": "pattern",
                "recommendation": rec.get("name"),
                "reason": rec.get("reason", ""),
            })
        
        if violations:
            reasoning.append({
                "type": "constraint",
                "violations": [
                    {
                        "message": v.message,
                        "fix": v.fix_hint,
                        "severity": v.severity,
                    }
                    for v in violations
                ],
            })
        
        return {
            "decision": output.recommendations[0].get("name") if output.recommendations else None,
            "reasoning": reasoning,
            "confidence": output.confidence,
            "can_proceed": output.can_deploy,
            "platform_services": list(output.config_templates.keys()),
            "explanation": output.explanation,
        }


_pipeline: Optional[KnowledgeProcessingPipeline] = None
_explainer: Optional[ExplanationEngine] = None


def get_knowledge_pipeline() -> KnowledgeProcessingPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = KnowledgeProcessingPipeline()
    return _pipeline


def get_explanation_engine() -> ExplanationEngine:
    global _explainer
    if _explainer is None:
        _explainer = ExplanationEngine()
    return _explainer