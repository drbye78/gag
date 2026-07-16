"""
Knowledge Module

Unified knowledge layer for domain intelligence:
- KnowledgeGraph: Semantic entity and relationship storage
- Ontology: Entity definitions and types
- Taxonomy: Pattern domain classification
- Use Cases: Scenario definitions
- ADRs: Architecture decision records
- Constraints: Rule-based validation
- Compatibility: Technology compatibility matrices
- Quality: Non-functional requirements
- Reference: Reference architectures
"""

from core.knowledge.graph import (
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeEdge,
    NodeType,
    EdgeType,
    get_knowledge_graph,
)
from core.knowledge.ontology import (
    ExtractedEntity,
    EntityRole,
    QueryIntent,
    IntentType,
    IRFeatureV2,
)
from core.knowledge.taxonomy import (
    PatternV2,
    PatternDomain,
    PatternMatcherV2,
    PatternMatch,
)
from core.knowledge.constraints import (
    ConstraintRule,
    RuleEngine,
    RuleResult,
    RuleType,
)
from core.knowledge.resolver import (
    KnowledgeResolver,
    ResolutionResult,
)
from core.knowledge.usecases import (
    UseCase,
    UseCaseCategory,
    UseCasePriority,
    UseCaseRepository,
    get_use_case_repository,
)
from core.knowledge.adrs import (
    ADR,
    ADRStatus,
    ADRDecision,
    ADRRepository,
    get_adr_repository,
)
from core.knowledge.reference import (
    ReferenceArchitecture,
    ReferenceArchitectureType,
    ReferenceArchitectureRepository,
    get_reference_architecture_repository,
)

__all__ = [
    # Graph
    "KnowledgeGraph",
    "KnowledgeNode", 
    "KnowledgeEdge",
    "NodeType",
    "EdgeType",
    # Ontology
    "ExtractedEntity",
    "EntityRole",
    "QueryIntent", 
    "IntentType",
    "IRFeatureV2",
    # Taxonomy
    "PatternV2",
    "PatternDomain",
    "PatternMatcherV2",
    "PatternMatch",
    # Constraints
    "ConstraintRule",
    "RuleEngine",
    "RuleResult", 
    "RuleType",
    # Resolver
    "KnowledgeResolver",
    "ResolutionResult",
    # Use Cases
    "UseCase",
    "UseCaseCategory",
    "UseCasePriority",
    "UseCaseRepository",
    "get_use_case_repository",
    # ADRs
    "ADR",
    "ADRStatus", 
    "ADRDecision",
    "ADRRepository",
    "get_adr_repository",
    # Reference Architectures
    "ReferenceArchitecture",
    "ReferenceArchitectureType",
    "ReferenceArchitectureRepository",
    "get_reference_architecture_repository",
]