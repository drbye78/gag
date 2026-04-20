# Revised Production-Grade Knowledge Domain Platform

## No Backward Compatibility - Breaking Changes OK

This revision leverages the freedom to make breaking changes where they significantly improve the design. The plan replaces or refactors existing components rather than layering new ones on top of legacy structures.

---

## 1. Breaking Changes Analysis

### 1.1 What Can Be Improved with Breaking Changes

| Current Component | Problem | Breaking Change Solution |
|------------------|---------|-------------------------|
| `IRFeature` (14 boolean fields) | Flat, no hierarchy, keyword extraction | Replace with semantic entity extraction |
| `Pattern` model | Flat conditions, string components | Rich objects with interfaces |
| `PlatformAdapter` | Monolithic, no cross-platform | Pluggable with composition |
| `ConstraintEngine` | Simple key-value evaluation | Rule engine with reasoning |
| Pattern matching | Keyword trigger matching | Semantic embedding similarity |
| Feature extraction | `in query_lower` | LLM-based extraction |

### 1.2 Scope of Breaking Changes

**Refactor (improve internally):**
- `core/patterns/schema.py` → Enhanced taxonomy
- `core/patterns/matcher.py` → Semantic matching
- `core/constraints/engine.py` → Rule engine
- `models/ir.py` → IRFeature v2

**Replace (new implementation):**
- `core/adapters/base.py` → Knowledge-first adapter
- `core/pipeline.py` → Unified knowledge pipeline

**Keep (working well):**
- API endpoints structure
- Test infrastructure
- Core models that aren't domain-specific

---

## 2. Revised Architecture

### 2.1 New Knowledge-First Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         REQUEST PROCESSING                                │
│  Query → Intent Detection → Entity Extraction → Knowledge Resolution     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE RESOLUTION ENGINE                            │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              Semantic Knowledge Graph                          │    │
│  │  Entities ←→ Relationships ←→ Patterns ←→ Constraints        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                      │
│         ┌──────────────────────────┼──────────────────────────┐          │
│         ▼                          ▼                          ▼          │
│  ┌─────────────┐          ┌─────────────┐          ┌─────────────┐   │
│  │  Ontology   │          │  Taxonomy   │          │   Use Cases │   │
│  │  Resolver  │          │   Matcher   │          │    Mapper   │   │
│  └─────────────┘          └─────────────┘          └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PLATFORM RESOLUTION                                    │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐ │
│  │    SAP      │   │   Tanzu     │   │   Power     │   │   (Future)  │ │
│  │   BTP       │   │             │   │  Platform   │   │   AWS/Azure  │ │
│  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Core Concept: Knowledge Graph First

Instead of extracting features → matching patterns → applying constraints, the new design:

1. **Parse query semantically** → Extract entities and relationships
2. **Query knowledge graph** → Find related entities, patterns, constraints
3. **Resolve to platform** → Generate platform-specific output

```python
# NEW: Semantic query resolution

class KnowledgeResolver:
    """Resolves queries against knowledge graph."""
    
    async def resolve(self, query: str) -> ResolutionResult:
        # 1. Extract entities from query
        entities = await self.entity_extractor.extract(query)
        
        # 2. Find relationships in knowledge graph
        related = await self.graph.find_related(entities)
        
        # 3. Match patterns based on relationships
        patterns = self.pattern_matcher.match_by_relations(related)
        
        # 4. Apply constraints
        violations = self.constraint_engine.validate(patterns, entities)
        
        # 5. Generate platform output
        return self.platform_resolver.resolve(patterns, violations)
```

---

## 3. Detailed Component Redesigns

### 3.1 IRFeature v2 (Breaking Change)

**Current**: 14 flat boolean fields
**New**: Semantic entity extraction with confidence scores

```python
# NEW: models/ir_v2.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum


class EntityRole(str, Enum):
    """Role of entity in the query."""
    SUBJECT = "subject"
    OBJECT = "object"
    ACTION = "action"
    CONSTRAINT = "constraint"
    QUALIFIER = "qualifier"


class ExtractedEntity(BaseModel):
    """Entity extracted from query with confidence."""
    id: str = Field(...)
    name: str = Field(...)
    type: str = Field(...)  # platform, service, pattern, technology
    
    # Extraction metadata
    role: EntityRole = Field(EntityRole.SUBJECT)
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Relationships
    relationships: List[str] = Field(default_factory=list)
    
    # Context
    context: Dict[str, Any] = Field(default_factory=dict)


class IntentType(str, Enum):
    """What the user wants to do."""
    DESIGN = "design"           # Create new architecture
    ANALYZE = "analyze"        # Analyze existing system
    TROUBLESHOOT = "troubleshoot"  # Fix problems
    MIGRATE = "migrate"        # Move from A to B
    OPTIMIZE = "optimize"      # Improve existing
    EXPLAIN = "explain"        # Understand something


class QueryIntent(BaseModel):
    """Parsed intent from user query."""
    primary: IntentType = Field(...)
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Supporting intents
    secondary: List[IntentType] = Field(default_factory=list)
    
    # Extracted entities
    entities: List[ExtractedEntity] = Field(default_factory=list)
    
    # Quality requirements (NFRs)
    quality_requirements: Dict[str, Any] = Field(default_factory=dict)


class IRFeatureV2(BaseModel):
    """V2: Semantic feature extraction."""
    # Intent
    intent: QueryIntent = Field(...)
    
    # Entities (replaces flat booleans)
    platforms: List[ExtractedEntity] = Field(default_factory=list)
    services: List[ExtractedEntity] = Field(default_factory=list)
    technologies: List[ExtractedEntity] = Field(default_factory=list)
    patterns: List[ExtractedEntity] = Field(default_factory=list)
    
    # Quality attributes (explicit)
    performance_requirements: Dict[str, Any] = Field(default_factory=dict)
    security_requirements: Dict[str, Any] = Field(default_factory=dict)
    scalability_requirements: Dict[str, Any] = Field(default_factory=dict)
    
    # Raw for reference
    raw_query: str = Field("")
    
    @property
    def all_entities(self) -> List[ExtractedEntity]:
        return (
            self.platforms 
            + self.services 
            + self.technologies 
            + self.patterns
        )
```

### 3.2 Knowledge Graph (New)

```python
# NEW: core/knowledge/graph.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Set
from enum import Enum
from datetime import datetime
import uuid


class NodeType(str, Enum):
    """Types of nodes in knowledge graph."""
    PLATFORM = "platform"
    SERVICE = "service"
    TECHNOLOGY = "technology"
    PATTERN = "pattern"
    CONSTRAINT = "constraint"
    USE_CASE = "use_case"
    REFERENCE_ARCH = "reference_arch"
    DECISION = "decision"


class EdgeType(str, Enum):
    """Types of edges in knowledge graph."""
    REQUIRES = "requires"
    PROVIDES = "provides"
    IMPLEMENTS = "implements"
    CONFLICTS = "conflicts"
    ALTERNATIVE = "alternative"
    DEPENDS_ON = "depends_on"
    WORKS_WITH = "works_with"
    COMPOSED_OF = "composed_of"


class KnowledgeNode(BaseModel):
    """Node in knowledge graph."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(...)
    type: NodeType = Field(...)
    
    # Properties
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    # Versioning
    version: str = Field("1.0.0")
    deprecated: bool = Field(False)
    
    # Metadata
    source: str = Field("")  # Where this knowledge came from
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeEdge(BaseModel):
    """Edge in knowledge graph."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = Field(...)
    target_id: str = Field(...)
    type: EdgeType = Field(...)
    
    # Edge properties
    weight: float = Field(1.0, ge=0.0, le=1.0)
    conditions: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeGraph(BaseModel):
    """Complete knowledge graph."""
    nodes: Dict[str, KnowledgeNode] = Field(default_factory=dict)
    edges: List[KnowledgeEdge] = Field(default_factory=list)
    
    # Indexes for fast lookup
    _by_type: Dict[NodeType, Set[str]] = Field(default_factory=dict)
    _by_name: Dict[str, Set[str]] = Field(default_factory=dict)
    
    def add_node(self, node: KnowledgeNode) -> None:
        self.nodes[node.id] = node
        
        # Update indexes
        if node.type not in self._by_type:
            self._by_type[node.type] = set()
        self._by_type[node.type].add(node.id)
        
        if node.name not in self._by_name:
            self._by_name[node.name] = set()
        self._by_name[node.name].add(node.id)
    
    def add_edge(self, edge: KnowledgeEdge) -> None:
        self.edges.append(edge)
    
    def find_by_type(self, node_type: NodeType) -> List[KnowledgeNode]:
        ids = self._by_type.get(node_type, set())
        return [self.nodes[nid] for nid in ids if nid in self.nodes]
    
    def find_by_name(self, name: str) -> List[KnowledgeNode]:
        ids = self._by_name.get(name, set())
        return [self.nodes[nid] for nid in ids if nid in self.nodes]
    
    def find_related(
        self, 
        node_id: str, 
        edge_types: List[EdgeType] = None,
        depth: int = 1
    ) -> List[KnowledgeNode]:
        """Find related nodes within depth hops."""
        if depth == 0:
            return []
        
        related_ids = set()
        for edge in self.edges:
            if edge.source_id == node_id:
                if edge_types is None or edge.type in edge_types:
                    related_ids.add(edge.target_id)
            elif edge.target_id == node_id:
                if edge_types is None or edge.type in edge_types:
                    related_ids.add(edge.source_id)
        
        result = [self.nodes[rid] for rid in related_ids if rid in self.nodes]
        
        # Recurse
        if depth > 1:
            for node in result[:]:
                deeper = self.find_related(node.id, edge_types, depth - 1)
                result.extend(deeper)
        
        return result
```

### 3.3 Semantic Pattern Matching (Breaking Change)

```python
# NEW: core/knowledge/patterns.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Set
from enum import Enum
import uuid


class PatternDomain(str, Enum):
    """Pattern domains (expanded from architecture)."""
    COMPUTE = "compute"
    DATA = "data"
    MESSAGING = "messaging"
    API = "api"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    OPERATIONS = "operations"
    INTEGRATION = "integration"


class PatternRelationship(str, Enum):
    """How patterns relate to each other."""
    REQUIRES = "requires"
    OPTIONAL_FOR = "optional_for"
    CONFLICTS_WITH = "conflicts_with"
    ALTERNATIVE_TO = "alternative_to"


class PatternPort(BaseModel):
    """Input/output port for pattern composition."""
    name: str = Field(...)
    type: str = Field(...)  # data type
    direction: str = Field(...)  # input, output
    description: str = Field("")


class PatternInterface(BaseModel):
    """Well-defined interface for pattern."""
    inputs: List[PatternPort] = Field(default_factory=list)
    outputs: List[PatternPort] = Field(default_factory=list)
    
    def get_port(self, name: str) -> Optional[PatternPort]:
        for port in self.inputs + self.outputs:
            if port.name == name:
                return port
        return None


class PatternV2(BaseModel):
    """V2: Rich pattern with interfaces and relationships."""
    id: str = Field(default_factory=lambda: f"pattern-{uuid.uuid4().hex[:8]}")
    name: str = Field(...)
    description: str = Field("")
    
    # Taxonomy
    domain: PatternDomain = Field(...)
    sub_domain: Optional[str] = Field(None)
    
    # Composition
    interface: PatternInterface = Field(PatternInterface(inputs=[], outputs=[]))
    
    # Relationships (not just conditions)
    requires_patterns: List[str] = Field(default_factory=list)  # Pattern IDs
    optional_patterns: List[str] = Field(default_factory=list)
    conflicts_with: List[str] = Field(default_factory=list)
    
    # Implementation references
    implementations: List[str] = Field(default_factory=list)  # Reference arch IDs
    
    # Quality impact (how this pattern affects NFRs)
    quality_impact: Dict[str, float] = Field(
        default_factory=dict,
        description="Impact on quality attributes: -1 to +1 scale"
    )
    
    # Metadata
    version: str = Field("1.0.0")
    source: str = Field("")
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class PatternMatcherV2(BaseModel):
    """V2: Semantic pattern matching using knowledge graph."""
    
    def __init__(self, knowledge_graph: KnowledgeGraph):
        self.graph = knowledge_graph
    
    def match(
        self, 
        entities: List[ExtractedEntity],
        intent: IntentType
    ) -> List[PatternMatch]:
        """Match patterns based on entities and intent."""
        matched = []
        
        # 1. Find pattern nodes related to extracted entities
        for entity in entities:
            related_patterns = self.graph.find_related(
                entity.id,
                edge_types=[EdgeType.IMPLEMENTS, EdgeType.WORKS_WITH],
                depth=2
            )
            
            for node in related_patterns:
                if node.type == NodeType.PATTERN:
                    score = self._calculate_match_score(node, entities, intent)
                    if score > 0.5:
                        matched.append(PatternMatch(
                            pattern=node,
                            score=score,
                            matched_entities=[entity.id],
                            reasoning=self._generate_reasoning(node, entities)
                        ))
        
        # 2. Apply pattern relationships (filter/conflicts)
        matched = self._apply_relationships(matched)
        
        return sorted(matched, key=lambda m: m.score, reverse=True)
    
    def _calculate_match_score(
        self,
        pattern: KnowledgeNode,
        entities: List[ExtractedEntity],
        intent: IntentType
    ) -> float:
        # Semantic similarity calculation
        score = pattern.confidence
        
        # Boost for entity alignment
        entity_types = {e.type for e in entities}
        if pattern.properties.get("target_types"):
            if entity_types & set(pattern.properties["target_types"]):
                score *= 1.2
        
        return min(1.0, score)
```

### 3.4 Rule-Based Constraints (Breaking Change)

```python
# NEW: core/knowledge/constraints.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import uuid


class RuleType(str, Enum):
    """Types of constraint rules."""
    MANDATORY = "mandatory"
    RECOMMENDED = "recommended"
    PROHIBITED = "prohibited"


class RuleCondition(BaseModel):
    """Condition for rule activation."""
    field: str = Field(...)  # e.g., "entity.type"
    operator: str = Field(...)  # eq, in, contains, regex
    value: Any = Field(...)


class RuleAction(BaseModel):
    """Action to take when rule triggers."""
    type: str = Field(...)  # warn, error, block, suggest
    message: str = Field(...)
    fix_suggestion: Optional[str] = Field(None)


class ConstraintRule(BaseModel):
    """V2: Rich constraint rule."""
    id: str = Field(default_factory=lambda: f"rule-{uuid.uuid4().hex[:8]}")
    name: str = Field(...)
    description: str = Field("")
    
    # Rule definition
    type: RuleType = Field(...)
    conditions: List[RuleCondition] = Field(default_factory=list)
    action: RuleAction = Field(...)
    
    # Scope
    applies_to: List[str] = Field(default_factory=list)  # Platform IDs, pattern IDs
    context: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    severity: str = Field("error")  # error, warning, info
    version: str = Field("1.0.0")


class RuleEngine(BaseModel):
    """V2: Rule-based constraint engine."""
    
    def __init__(self):
        self.rules: Dict[str, ConstraintRule] = {}
        self._compiled: Dict[str, Callable] = {}
    
    def add_rule(self, rule: ConstraintRule) -> None:
        self.rules[rule.id] = rule
        self._compiled[rule.id] = self._compile_rule(rule)
    
    def evaluate(
        self, 
        context: Dict[str, Any],
        scope: List[str]
    ) -> List[RuleResult]:
        """Evaluate all applicable rules."""
        results = []
        
        for rule_id, rule in self.rules.items():
            # Check scope
            if scope and not any(s in rule.applies_to for s in scope):
                continue
            
            # Check conditions
            if self._check_conditions(rule.conditions, context):
                results.append(RuleResult(
                    rule=rule,
                    triggered=True,
                    message=rule.action.message,
                    fix=rule.action.fix_suggestion,
                    severity=rule.severity
                ))
        
        return results
    
    def _compile_rule(self, rule: ConstraintRule) -> Callable:
        """Compile rule conditions to callable."""
        # Simplified: in production, use actual expression compiler
        def compiled(context: Dict[str, Any]) -> bool:
            return all(
                self._evaluate_condition(c, context) 
                for c in rule.conditions
            )
        return compiled
    
    def _check_conditions(
        self, 
        conditions: List[RuleCondition], 
        context: Dict[str, Any]
    ) -> bool:
        return all(self._evaluate_condition(c, context) for c in conditions)
    
    def _evaluate_condition(self, cond: RuleCondition, context: Dict[str, Any]) -> bool:
        value = self._get_nested(context, cond.field)
        
        if cond.operator == "eq":
            return value == cond.value
        elif cond.operator == "in":
            return value in cond.value
        elif cond.operator == "contains":
            return cond.value in str(value)
        elif cond.operator == "regex":
            import re
            return bool(re.match(cond.value, str(value)))
        
        return False
    
    def _get_nested(self, d: Dict, path: str) -> Any:
        keys = path.split(".")
        val = d
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return None
        return val


class RuleResult(BaseModel):
    """Result of rule evaluation."""
    rule: ConstraintRule
    triggered: bool
    message: str
    fix: Optional[str] = None
    severity: str
```

---

## 4. Module Structure (Revised)

```
core/
├── knowledge/                  # NEW: Unified knowledge layer
│   ├── __init__.py
│   ├── graph.py              # KnowledgeGraph
│   ├── resolver.py           # Query resolution
│   │
│   ├── ontology/             # Entity definitions
│   │   ├── __init__.py
│   │   ├── entities.py       # ExtractedEntity, EntityRole
│   │   └── types.py         # NodeType, EdgeType
│   │
│   ├── taxonomy/             # Pattern taxonomy
│   │   ├── __init__.py
│   │   ├── domains.py        # PatternDomain enum
│   │   └── patterns.py       # PatternV2, PatternMatcherV2
│   │
│   ├── usecases/             # Use cases
│   │   ├── __init__.py
│   │   └── model.py
│   │
│   ├── adrs/                 # Decision records
│   │   ├── __init__.py
│   │   └── model.py
│   │
│   ├── constraints/          # Rule engine
│   │   ├── __init__.py
│   │   └── rules.py          # RuleEngine, ConstraintRule
│   │
│   ├── compatibility/        # Tech compatibility
│   │   ├── __init__.py
│   │   └── matrix.py
│   │
│   ├── quality/              # Quality attributes
│   │   ├── __init__.py
│   │   └── model.py
│   │
│   └── reference/            # Reference architectures
│       ├── __init__.py
│       └── model.py
│
├── adapters/                  # REWRITE: Platform adapters
│   ├── __init__.py
│   ├── base.py              # New base with knowledge integration
│   ├── sap.py
│   ├── tanzu.py
│   └── powerplatform.py
│
├── pipeline.py               # REWRITE: Unified pipeline
│
# REMOVED (replaced by knowledge/):
# - core/patterns/ (replaced by knowledge/taxonomy/)
# - core/constraints/ (replaced by knowledge/constraints/)
```

---

## 5. Implementation Phases

### Phase 1: Core Knowledge Graph (Weeks 1-2)

| Task | Description |
|------|-------------|
| 5.1.1 | Create `core/knowledge/` module structure |
| 5.1.2 | Implement `KnowledgeGraph` with nodes/edges |
| 5.1.3 | Implement entity extraction (`ExtractedEntity`) |
| 5.1.4 | Build knowledge graph loader with seed data |

### Phase 2: Pattern System Rewrite (Weeks 3-4)

| Task | Description |
|------|-------------|
| 5.2.1 | Implement `PatternV2` with interfaces |
| 5.2.2 | Build `PatternMatcherV2` with graph traversal |
| 5.2.3 | Migrate existing 12 patterns to V2 format |
| 5.2.4 | Add SAP/Tanzu/PowerPlatform-specific patterns |

### Phase 3: Constraint Engine Rewrite (Weeks 5-6)

| Task | Description |
|------|-------------|
| 5.3.1 | Implement `RuleEngine` with condition evaluation |
| 5.3.2 | Create constraint rule DSL |
| 5.3.3 | Migrate existing constraints to rules |
| 5.3.4 | Add platform-specific rule sets |

### Phase 4: Pipeline & Integration (Weeks 7-8)

| Task | Description |
|------|-------------|
| 5.4.1 | Rewrite `core/pipeline.py` with knowledge-first approach |
| 5.4.2 | Implement `KnowledgeResolver` |
| 5.4.3 | Update adapter interfaces |
| 5.4.4 | Integrate with existing API |

### Phase 5: Platform Adapters (Weeks 9-10)

| Task | Description |
|------|-------------|
| 5.5.1 | Refactor `PlatformAdapter` base class |
| 5.5.2 | Update SAP BTP adapter |
| 5.5.3 | Update Tanzu adapter |
| 5.5.4 | Update PowerPlatform adapter |

### Phase 6: Testing & Migration (Weeks 11-12)

| Task | Description |
|------|-------------|
| 5.6.1 | Unit tests for all new modules |
| 5.6.2 | Integration tests |
| 5.6.3 | API tests |
| 5.6.4 | Remove deprecated code |

---

## 6. Breaking Changes Summary

| Old Component | New Component | Migration |
|--------------|---------------|-----------|
| `models/ir.IRFeature` | `models/ir_v2.IRFeatureV2` | Parallel until full migration |
| `core/patterns/*` | `core/knowledge/taxonomy/*` | Drop-in replacement |
| `core/constraints/*` | `core/knowledge/constraints/*` | Drop-in replacement |
| `core/adapters/base.py` | `core/adapters/base.py` | Refactor interface |
| `core/pipeline.py` | `core/pipeline.py` | Full rewrite |

---

## 7. Benefits of Breaking Changes

1. **Semantic understanding** - Entity extraction vs keyword matching
2. **Graph-based reasoning** - Relationships between patterns/constraints
3. **Composability** - Pattern interfaces for composition
4. **Extensibility** - Rule engine with dynamic rule loading
5. **Maintainability** - Single knowledge source of truth

---

This plan fully leverages the freedom to make breaking changes for a significantly improved architecture.