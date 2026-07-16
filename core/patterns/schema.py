from pydantic import BaseModel, Field
from typing import Any, Optional


class PatternCondition(BaseModel):
    feature: str
    operator: str
    value: Any
    description: str = ""


class PatternRelationship(BaseModel):
    source: str
    target: str
    relationship_type: str
    description: str = ""
    async_compatible: bool = True


class Pattern(BaseModel):
    id: str
    name: str
    domain: str
    
    triggers: list[str] = []
    conditions: list[PatternCondition] = []
    
    components: list[str] = []
    relationships: list[PatternRelationship] = []
    
    benefits: list[str] = []
    tradeoffs: list[str] = []
    anti_patterns: list[str] = []
    
    priority: int = 5
    confidence: float = 0.0
    source_reference: Optional[str] = None


class PatternMatchResult(BaseModel):
    pattern: Pattern
    match_score: float
    matched_conditions: list[str] = []
    unmatched_conditions: list[str] = []
    confidence_boost: float = 0.0


class PatternLibrary:
    def __init__(self):
        self._patterns: dict[str, Pattern] = {}
        self._index_by_trigger: dict[str, list[str]] = {}
        self._domain_index: dict[str, list[str]] = {}
    
    def register(self, pattern: Pattern) -> None:
        self._patterns[pattern.id] = pattern
        
        for trigger in pattern.triggers:
            if trigger not in self._index_by_trigger:
                self._index_by_trigger[trigger] = []
            self._index_by_trigger[trigger].append(pattern.id)
        
        domain = pattern.domain
        if domain not in self._domain_index:
            self._domain_index[domain] = []
        self._domain_index[domain].append(pattern.id)
    
    def query(self, features: "IRFeature") -> list[Pattern]:
        candidates = set()
        
        feature_dict = features.model_dump()
        for trigger, pattern_ids in self._index_by_trigger.items():
            if trigger.lower() in str(feature_dict).lower():
                candidates.update(pattern_ids)
        
        return [self._patterns[pid] for pid in candidates if pid in self._patterns]
    
    def get(self, pattern_id: str) -> Optional[Pattern]:
        return self._patterns.get(pattern_id)
    
    def list_by_domain(self, domain: str) -> list[Pattern]:
        pattern_ids = self._domain_index.get(domain, [])
        return [self._patterns[pid] for pid in pattern_ids if pid in self._patterns]
    
    def all(self) -> list[Pattern]:
        return list(self._patterns.values())


_pattern_library: Optional[PatternLibrary] = None


def get_pattern_library() -> PatternLibrary:
    global _pattern_library
    if _pattern_library is None:
        _pattern_library = PatternLibrary()
        _load_default_patterns(_pattern_library)
    return _pattern_library


def _load_default_patterns(library: PatternLibrary) -> None:
    from typing import List
    
    patterns = [
        Pattern(
            id="event_driven",
            name="Event-Driven Architecture",
            domain="architecture",
            triggers=["event", "kafka", "eventing", "async"],
            conditions=[
                PatternCondition(feature="has_async", operator="eq", value=True),
                PatternCondition(feature="has_event_driven", operator="eq", value=True),
            ],
            components=["event_bus", "producer", "consumer"],
            benefits=["Decoupling", "Scalability", "Resilience"],
            tradeoffs=["Complexity", "Debugging difficulty"],
            priority=8,
            confidence=0.85,
        ),
        Pattern(
            id="microservices",
            name="Microservices Architecture",
            domain="architecture",
            triggers=["microservice", "service", "api gateway"],
            conditions=[
                PatternCondition(feature="has_microservices", operator="eq", value=True),
            ],
            components=["api_gateway", "service_a", "service_b"],
            benefits=["Independent scaling", "Technology flexibility", "Fault isolation"],
            tradeoffs=["Distributed system complexity", "Data consistency"],
            priority=9,
            confidence=0.9,
        ),
        Pattern(
            id="serverless",
            name="Serverless Architecture",
            domain="architecture",
            triggers=["lambda", "function", "serverless", "faas"],
            conditions=[
                PatternCondition(feature="has_serverless", operator="eq", value=True),
            ],
            components=["function", "trigger", "state"],
            benefits=["No server management", "Auto-scaling", "Pay per use"],
            tradeoffs=["Cold starts", "Vendor lock-in", "Stateless"],
            priority=7,
            confidence=0.8,
        ),
        Pattern(
            id="api_first",
            name="API-First Design",
            domain="architecture",
            triggers=["rest", "graphql", "api", "openapi"],
            conditions=[
                PatternCondition(feature="has_api", operator="eq", value=True),
            ],
            components=["api", "documentation", "validation"],
            benefits=["CLIs", "Integrations", "Documentation"],
            tradeoffs=["Initial effort", "Versioning"],
            priority=9,
            confidence=0.95,
        ),
        Pattern(
            id="multi_tenant",
            name="Multi-Tenant Architecture",
            domain="architecture",
            triggers=["multi", "tenant", "saas"],
            conditions=[
                PatternCondition(feature="multi_tenant", operator="eq", value=True),
            ],
            components=["tenant_isolation", "billing", "usage_tracking"],
            benefits=["Shared infrastructure", "Cost efficiency"],
            tradeoffs=["Security isolation", "Resource contention"],
        priority=8,
            confidence=0.8,
        ),
        Pattern(
            id="saas_multi_tenant",
            name="SaaS Multi-Tenant Architecture",
            domain="architecture",
            triggers=["multi-tenant", "saas", "shared"],
            conditions=[
                PatternCondition(feature="multi_tenant", operator="eq", value=True),
            ],
            components=["tenant_isolation", "usage_tracking", "billing"],
            benefits=["Shared infrastructure", "Cost efficiency", "Centralized updates"],
            tradeoffs=["Security isolation", "Resource contention", "Tenant specific customization limits"],
            priority=9,
            confidence=0.85,
        ),
        Pattern(
            id="api_gateway",
            name="API Gateway Pattern",
            domain="architecture",
            triggers=["gateway", "api gateway", "kong", "ingress"],
            conditions=[
                PatternCondition(feature="has_api", operator="eq", value=True),
                PatternCondition(feature="has_microservices", operator="eq", value=True),
            ],
            components=["gateway", "auth", "rate_limiter"],
            benefits=["Centralized auth", "Rate limiting", "Request routing"],
            tradeoffs=["Single point of failure", "Additional latency"],
            priority=8,
            confidence=0.9,
        ),
        Pattern(
            id="cqrs",
            name="CQRS Pattern",
            domain="architecture",
            triggers=["cqrs", "read/write separation", "event source"],
            conditions=[
                PatternCondition(feature="has_async", operator="eq", value=True),
            ],
            components=["command_model", "query_model", "event_bus"],
            benefits=["Optimized reads/writes", "Scalability", "Audit trail"],
            tradeoffs=["Complexity", "Eventual consistency"],
            priority=7,
            confidence=0.75,
        ),
        Pattern(
            id="circuit_breaker",
            name="Circuit Breaker Pattern",
            domain="architecture",
            triggers=["resilience", "circuit breaker", "fallback"],
            conditions=[],
            components=["breaker", "fallback", "monitor"],
            benefits=["Failure isolation", "Graceful degradation", "Self-healing"],
            tradeoffs=["Additional complexity", "Tuning required"],
            priority=8,
            confidence=0.85,
        ),
        Pattern(
            id="strangler_fig",
            name="Strangler Fig Pattern",
            domain="architecture",
            triggers=["migration", "strangler", "gradual"],
            conditions=[],
            components=["facade", "legacy", "new_service"],
            benefits=["Incremental migration", "Risk reduction", "Parallel run"],
            tradeoffs=["Dual running", "Data sync complexity"],
            priority=7,
            confidence=0.8,
        ),
        Pattern(
            id="backends_for_frontend",
            name="BFF - Backend for Frontend",
            domain="architecture",
            triggers=["bff", "frontend", "mobile", "web"],
            conditions=[
                PatternCondition(feature="has_ui", operator="eq", value=True),
            ],
            components=["web_bff", "mobile_bff", "aggregator"],
            benefits=["Frontend optimization", "API versioning", "Team autonomy"],
            tradeoffs=["Code duplication", "Maintenance overhead"],
            priority=8,
            confidence=0.85,
        ),
        Pattern(
            id="edge_computing",
            name="Edge Computing",
            domain="architecture",
            triggers=["edge", "cdn", "latency"],
            conditions=[],
            components=["edge_node", "origin", "cache"],
            benefits=["Low latency", "Bandwidth reduction", "Offline capability"],
            tradeoffs=["Consistency challenges", "Deployment complexity"],
            priority=6,
            confidence=0.7,
        ),
    ]
    
    for pattern in patterns:
        library.register(pattern)