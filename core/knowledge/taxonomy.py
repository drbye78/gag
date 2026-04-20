from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum


class PatternDomain(str, Enum):
    COMPUTE = "compute"
    DATA = "data"
    MESSAGING = "messaging"
    API = "api"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    OPERATIONS = "operations"
    INTEGRATION = "integration"


class PatternMatch(BaseModel):
    pattern_id: str = Field(...)
    pattern_name: str = Field(...)
    score: float = Field(ge=0.0, le=1.0)
    matched_entities: List[str] = Field(default_factory=list)
    reasoning: str = Field("")


class PatternV2(BaseModel):
    id: str = Field(...)
    name: str = Field(...)
    description: str = Field("")
    domain: PatternDomain = Field(...)
    sub_domain: Optional[str] = Field(None)
    requires_patterns: List[str] = Field(default_factory=list)
    optional_patterns: List[str] = Field(default_factory=list)
    conflicts_with: List[str] = Field(default_factory=list)
    implementations: List[str] = Field(default_factory=list)
    quality_impact: Dict[str, float] = Field(default_factory=dict)
    version: str = Field("1.0.0")
    source: str = Field("")
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class PatternMatcherV2(BaseModel):
    def __init__(self, graph: Any = None):
        self.graph = graph

    def match(
        self,
        entities: List[Any],
        intent: str
    ) -> List[PatternMatch]:
        from core.knowledge.graph import NodeType, EdgeType, get_knowledge_graph
        
        matched = []
        graph = get_knowledge_graph()
        
        for entity in entities:
            related = graph.find_related(
                entity.get("id", ""),
                edge_types=[EdgeType.IMPLEMENTS, EdgeType.WORKS_WITH],
                depth=2
            )
            
            for node in related:
                if node.type == NodeType.PATTERN:
                    matched.append(PatternMatch(
                        pattern_id=node.id,
                        pattern_name=node.name,
                        score=node.confidence,
                        matched_entities=[entity.get("id", "")],
                        reasoning=f"Matched via knowledge graph",
                    ))
        
        return sorted(matched, key=lambda m: m.score, reverse=True)


_patterns: List[PatternV2] = []


def get_patterns() -> List[PatternV2]:
    global _patterns
    if not _patterns:
        _load_default_patterns(_patterns)
    return _patterns


def _load_default_patterns(patterns: List[PatternV2]) -> None:
    patterns.extend([
        PatternV2(
            id="microservices",
            name="Microservices Architecture",
            description="Decompose into independent services",
            domain=PatternDomain.COMPUTE,
            requires_patterns=["api_gateway"],
            quality_impact={"maintainability": 0.8, "scalability": 0.9},
            confidence=0.9,
        ),
        PatternV2(
            id="event_driven",
            name="Event-Driven Architecture",
            description="Decouple via events",
            domain=PatternDomain.MESSAGING,
            requires_patterns=["event_bus"],
            quality_impact={"coupling": -0.7, "scalability": 0.8},
            confidence=0.85,
        ),
        PatternV2(
            id="serverless",
            name="Serverless",
            description="Function as a service",
            domain=PatternDomain.COMPUTE,
            quality_impact={"cost": -0.5, "scalability": 0.9},
            confidence=0.8,
        ),
        PatternV2(
            id="cqrs",
            name="CQRS",
            description="Separate read and write models",
            domain=PatternDomain.DATA,
            requires_patterns=["event_store"],
            quality_impact={"performance": 0.7, "complexity": 0.5},
            confidence=0.75,
        ),
        PatternV2(
            id="api_gateway",
            name="API Gateway",
            description="Central entry point for APIs",
            domain=PatternDomain.API,
            quality_impact={"security": 0.6, "simplicity": 0.5},
            confidence=0.9,
        ),
        PatternV2(
            id="circuit_breaker",
            name="Circuit Breaker",
            description="Handle failures gracefully",
            domain=PatternDomain.INTEGRATION,
            quality_impact={"reliability": 0.8, "complexity": 0.3},
            confidence=0.85,
        ),
    ])