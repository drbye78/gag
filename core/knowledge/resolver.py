from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from core.knowledge.constraints import get_rule_engine
from core.knowledge.graph import NodeType, get_knowledge_graph
from core.knowledge.ontology import (
    EntityRole,
    ExtractedEntity,
    IntentType,
    QueryIntent,
)
from core.knowledge.taxonomy import PatternMatch, get_patterns


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
    async def resolve(self, query: str, _visited: Optional[set] = None) -> ResolutionResult:
        """Resolve a knowledge query with circular reference detection.

        Args:
            query: The query string to resolve.
            _visited: Internal set of already-processed query hashes
                      used to prevent infinite recursion.
        """
        import hashlib

        if _visited is None:
            _visited = set()

        # Circular reference detection: hash the query and skip if already seen
        query_hash = hashlib.sha256(query.lower().encode()).hexdigest()
        if query_hash in _visited:
            return ResolutionResult(
                query=query,
                reasoning="Circular reference detected — skipping already-visited query",
                can_proceed=False,
            )
        _visited.add(query_hash)

        query_lower = query.lower()

        intent = self._detect_intent(query_lower)
        entities = self._extract_entities(query_lower)

        graph = get_knowledge_graph()

        platform = self._detect_platform(entities, graph)

        pattern_results = self._match_patterns(entities, intent, graph)

        context = self._build_context(entities, platform)
        violations = self._evaluate_constraints(context, platform)

        reasoning = self._generate_reasoning(intent, pattern_results, violations)

        confidence = self._compute_confidence(entities, pattern_results, violations)

        return ResolutionResult(
            query=query,
            intent=QueryIntent(
                primary=intent,
                confidence=confidence,
                entities=entities,
            ),
            patterns_matched=pattern_results,
            constraint_violations=violations,
            entities_found=entities,
            platform=platform,
            reasoning=reasoning,
            can_proceed=len([v for v in violations if v.severity == "error"]) == 0,
        )

    def _compute_confidence(
        self,
        entities: List[ExtractedEntity],
        patterns: List[PatternMatch],
        violations: List[Any],
    ) -> float:
        base_confidence = 0.5
        entity_score = min(len(entities) * 0.1, 0.2)
        pattern_score = min(len(patterns) * 0.1, 0.2)
        violation_penalty = min(len([v for v in violations if v.severity == "error"]) * 0.1, 0.3)
        return min(
            max(base_confidence + entity_score + pattern_score - violation_penalty, 0.0), 1.0
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
        # Lazy import to avoid circular dep: base.py → knowledge/graph → resolver → base.py
        from core.adapters.base import PLATFORM_DETECT_KEYWORDS

        entities = []

        for platform, keywords in PLATFORM_DETECT_KEYWORDS.items():
            for kw in keywords:
                if kw in query:
                    entities.append(
                        ExtractedEntity(
                            id=platform,
                            name=platform,
                            type="platform",
                            role=EntityRole.SUBJECT,
                            confidence=0.9,
                        )
                    )
                    break

        tech_keywords = ["rest", "graphql", "api", "database", "auth", "oauth", "jwt"]
        for kw in tech_keywords:
            if kw in query:
                entities.append(
                    ExtractedEntity(
                        id=kw,
                        name=kw,
                        type="technology",
                        role=EntityRole.CONSTRAINT,
                        confidence=0.7,
                    )
                )

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
        self, entities: List[ExtractedEntity], intent: IntentType, graph: Any
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
                matches.append(
                    PatternMatch(
                        pattern_id=pattern.id,
                        pattern_name=pattern.name,
                        score=min(1.0, score),
                        matched_entities=matches_ents,
                        reasoning=f"Matched {len(matches_ents)} entities",
                    )
                )

        return sorted(matches, key=lambda m: m.score, reverse=True)[:5]

    def _build_context(
        self, entities: List[ExtractedEntity], platform: Optional[str]
    ) -> Dict[str, Any]:
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
        self, intent: IntentType, patterns: List[PatternMatch], violations: List[Any]
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
