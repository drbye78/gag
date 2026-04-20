from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from core.knowledge.graph import get_knowledge_graph, NodeType, EdgeType
from core.knowledge.ontology import ExtractedEntity, QueryIntent, IntentType, IRFeatureV2, EntityRole
from core.knowledge.taxonomy import PatternMatch, get_patterns
from core.knowledge.constraints import get_rule_engine


class ResolutionResult(BaseModel):
    query: str = Field(...)
    intent: Optional[QueryIntent] = Field(None)
    patterns_matched: List[PatternMatch] = Field(default_factory=list)
    constraint_violations: List[Any] = Field(default_factory=list)
    entities_found: List[ExtractedEntity] = Field(default_factory=list)
    platform: Optional[str] = Field(None)
    reasoning: str = Field("")
    can_proceed: bool = Field(True)


class KnowledgeResolver(BaseModel):
    async def resolve(self, query: str) -> ResolutionResult:
        query_lower = query.lower()
        
        intent = self._detect_intent(query_lower)
        entities = self._extract_entities(query_lower)
        
        graph = get_knowledge_graph()
        
        platform = self._detect_platform(entities, graph)
        
        pattern_results = self._match_patterns(entities, intent, graph)
        
        context = self._build_context(entities, platform)
        violations = self._evaluate_constraints(context, platform)
        
        reasoning = self._generate_reasoning(intent, pattern_results, violations)
        
        return ResolutionResult(
            query=query,
            intent=QueryIntent(
                primary=intent,
                confidence=0.8,
                entities=entities,
            ),
            patterns_matched=pattern_results,
            constraint_violations=violations,
            entities_found=entities,
            platform=platform,
            reasoning=reasoning,
            can_proceed=len([v for v in violations if v.severity == "error"]) == 0,
        )

    def _detect_intent(self, query: str) -> IntentType:
        if any(kw in query for kw in ["create", "build", "design", "new", "implement"]):
            return IntentType.DESIGN
        elif any(kw in query for kw in ["fix", "error", "broken", "issue", "problem"]):
            return IntentType.TROUBLESHOOT
        elif any(kw in query for kw in ["migrate", "move", "convert", "upgrade"]):
            return IntentType.MIGRATE
        elif any(kw in query for kw in ["optimize", "improve", "performance", "faster"]):
            return IntentType.OPTIMIZE
        elif any(kw in query for kw in ["explain", "understand", "how does", "what is"]):
            return IntentType.EXPLAIN
        else:
            return IntentType.ANALYZE

    def _extract_entities(self, query: str) -> List[ExtractedEntity]:
        entities = []
        graph = get_knowledge_graph()
        
        platform_keywords = {
            "sap": ["xsuaa", "hana", "btp", "cap", "cloudfoundry", "kyma"],
            "tanzu": ["tanzu", "pivotal", "spring", "kubernetes", "knative"],
            "powerplatform": ["powerapps", "powerautomate", "dataverse", "copilot"],
        }
        
        for platform, keywords in platform_keywords.items():
            for kw in keywords:
                if kw in query:
                    entities.append(ExtractedEntity(
                        id=platform,
                        name=platform,
                        type="platform",
                        role=EntityRole.SUBJECT,
                        confidence=0.9,
                    ))
                    break
        
        tech_keywords = ["rest", "graphql", "api", "database", "auth", "oauth", "jwt"]
        for kw in tech_keywords:
            if kw in query:
                entities.append(ExtractedEntity(
                    id=kw,
                    name=kw,
                    type="technology",
                    role=EntityRole.CONSTRAINT,
                    confidence=0.7,
                ))
        
        return entities

    def _detect_platform(self, entities: List[ExtractedEntity], graph: Any) -> Optional[str]:
        for entity in entities:
            if entity.type == "platform":
                return entity.id
        
        for entity in entities:
            node = graph.get_node(entity.id)
            if node and node.type == NodeType.PLATFORM:
                return node.id
        
        return None

    def _match_patterns(
        self,
        entities: List[ExtractedEntity],
        intent: IntentType,
        graph: Any
    ) -> List[PatternMatch]:
        matches = []
        patterns = get_patterns()
        
        for pattern in patterns:
            score = 0.0
            matches_ents = []
            
            for entity in entities:
                if entity.type == "platform":
                    score += 0.3
                    matches_ents.append(entity.id)
                elif entity.type == "technology":
                    if entity.id in pattern.quality_impact:
                        score += 0.2
                        matches_ents.append(entity.id)
            
            if score > 0:
                matches.append(PatternMatch(
                    pattern_id=pattern.id,
                    pattern_name=pattern.name,
                    score=min(1.0, score),
                    matched_entities=matches_ents,
                    reasoning=f"Matched {len(matches_ents)} entities",
                ))
        
        return sorted(matches, key=lambda m: m.score, reverse=True)[:5]

    def _build_context(self, entities: List[ExtractedEntity], platform: Optional[str]) -> Dict[str, Any]:
        context = {"platform": platform or "unknown"}
        
        for entity in entities:
            context[entity.type] = True
        
        return context

    def _evaluate_constraints(self, context: Dict[str, Any], platform: Optional[str]) -> List[Any]:
        if not platform:
            return []
        
        engine = get_rule_engine()
        return engine.evaluate(context, [platform])

    def _generate_reasoning(
        self,
        intent: IntentType,
        patterns: List[PatternMatch],
        violations: List[Any]
    ) -> str:
        parts = [f"Intent: {intent.value}"]
        
        if patterns:
            top = patterns[0]
            parts.append(f"Recommended: {top.pattern_name} ({top.score:.0%})")
        
        errors = [v for v in violations if v.severity == "error"]
        if errors:
            parts.append(f"Blocking: {len(errors)} issues")
        
        return " | ".join(parts)


_resolver: Optional[KnowledgeResolver] = None


def get_resolver() -> KnowledgeResolver:
    global _resolver
    if _resolver is None:
        _resolver = KnowledgeResolver()
    return _resolver