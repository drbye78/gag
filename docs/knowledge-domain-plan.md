# Production-Grade Knowledge Domain Platform

## Comprehensive Enhancement Plan

---

## 1. Problem Statement

The current PlatformAdapter implementation provides ~35% of mandatory knowledge domain elements. It handles basic pattern matching and constraint validation but lacks the structural knowledge, reasoning depth, and operational maturity required for production-grade domain intelligence.

### Consolidated Gap Summary

| Category | Coverage | Critical Gaps |
|----------|----------|----------------|
| Ontology | 35% | No semantic relationships, no version handling |
| Taxonomy | 25% | Flat structure only |
| Components | 40% | String lists, no versioning, no interfaces |
| Integration | 30% | No cross-platform reasoning |
| Reference Architectures | 40% | Adapters exist but not linked |
| ADRs | 0% | Completely missing |
| Use Cases | 15% | Implicit only |

### Additional Technical Gaps

| Gap | Severity | Root Cause |
|-----|----------|-----------|
| Keyword-based extraction | 🔴 Critical | Brittle matching, no semantic understanding |
| No cross-platform reasoning | 🔴 Critical | Monolithic adapter design |
| No quality attributes/NFRs | 🟠 High | IRFeature too simple |
| No technology compatibility matrix | 🟠 High | No "X works with Y" knowledge |
| No risk assessment | 🟠 High | No security/compliance modeling |
| No migration paths | 🟠 High | No modernization guidance |
| No anti-pattern enforcement | 🟡 Medium | anti_patterns listed but unused |
| No reference implementations | 🟡 Medium | Can't point to working code |
| No learning/feedback loop | 🟡 Medium | Static matching |

---

## 2. Target Architecture

### 2.1 Core Knowledge Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   REST API  │  │   GraphQL   │  │    MCP     │  │   Web UI   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   ORCHESTRATION LAYER                              │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              KnowledgeProcessingPipeline                   │  │
│  │  (Query → Feature Extraction → Pattern Match → Validate)    │  │
│  └─────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────���────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE LAYER                                  │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │  Ontology  │  │  Taxonomy   │  │ Use Cases   │  │    ADRs    │  │
│  │  (Entities)│  │ (Patterns)  │  │ (Stories)   │  │ (Decisions) │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │Constraints │  │ Compatibility│  │  Quality   │  │ Reference  │  │
│  │ (Rules)    │  │   Matrix    │  │ Attributes │  │  Archs     │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  PLATFORM ADAPTER LAYER                             │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ │
│  │    SAP   │ │  Tanzu    │ │  Power    │ │   AWS    │ │  Azure   │ │
│  │   BTP    │ │          │ │  Platform │ │          │ │           │ │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 New Module Structure

```
core/
├── knowledge/                  # NEW: Core knowledge layer
│   ├── __init__.py
│   ├── ontology/              # Entity definitions + relationships
│   │   ├── __init__.py
│   │   ├── entities.py        # Entity, Relationship, EntityType
│   │   ├── schema.py         # Knowledge graph schema
│   │   └── loader.py        # Load/serialize ontology
│   │
│   ├── taxonomy/             # Pattern + domain taxonomy
│   │   ├── __init__.py
│   │   ├── domains.py        # Domain definitions
│   │   ├── patterns.py       # Enhanced Pattern model
│   │   └── matcher.py       # Semantic pattern matching
│   │
│   ├── usecases/            # Use case definitions
│   │   ├── __init__.py
│   │   ├── model.py         # UseCase, Scenario, AcceptanceCriteria
│   │   ├── repository.py    # Use case storage
│   │   └── mapper.py       # UseCase → Pattern mapping
│   │
│   ├── adrs/                # Architecture Decision Records
│   │   ├── __init__.py
│   │   ├── model.py         # ADR model
│   │   ├── repository.py    # ADR storage
│   │   └── templates.py    # ADR templates
│   │
│   ├── compatibility/       # Technology compatibility
│   │   ├── __init__.py
│   │   ├── matrix.py       # CompatibilityMatrix
│   │   ├── rules.py       # Tech compatibility rules
│   │   └── validator.py    # Stack validator
│   │
│   ├── quality/             # Quality attributes
│   │   ├── __init__.py
│   │   ├── model.py        # QualityAttribute, NFR
│   │   ├── collector.py    # Collect from query
│   │   └── assessor.py     # Assess against targets
│   │
│   └── reference/           # Reference architectures
│       ├── __init__.py
│       ├── model.py        # ReferenceArch
│       ├── catalog.py      # Arch catalog
│       └── linker.py      # Link to patterns/adapters
│
├── adapters/               # EXISTING: Platform adapters
│   ├── base.py
│   ├── sap.py
│   ├── tanzu.py
│   └── powerplatform.py
│
├── patterns/                # EXISTING: Pattern library
│   ├── schema.py
│   └── matcher.py
│
└── constraints/             # EXISTING: Constraints
    └── engine.py
```

---

## 3. Detailed Component Designs

### 3.1 Ontology Module (`knowledge/ontology/`)

**Purpose**: Define entities, relationships, and semantic knowledge.

```python
# knowledge/ontology/entities.py

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class EntityType(str, Enum):
    """Top-level entity categories."""
    PLATFORM = "platform"
    SERVICE = "service"
    COMPONENT = "component"
    PATTERN = "pattern"
    CONSTRAINT = "constraint"
    TECHNOLOGY = "technology"
    USE_CASE = "use_case"
    REFERENCE_ARCH = "reference_arch"


class RelationshipType(str, Enum):
    """Well-defined relationship types."""
    DEPENDS_ON = "depends_on"
    IMPLEMENTED_BY = "implemented_by"
    REQUIRES = "requires"
    CONFLICTS_WITH = "conflicts_with"
    WORKS_WITH = "works_with"
    ALTERNATIVE_TO = "alternative_to"
    EXTENDS = "extends"
    COMPOSED_OF = "composed_of"


class Entity(BaseModel):
    """Core entity in the knowledge graph."""
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Human-readable name")
    type: EntityType = Field(..., description="Entity category")
    description: str = Field("", description="What this entity is")
    
    # Semantic properties
    parent_id: Optional[str] = Field(None, description="Parent entity for taxonomy")
    version: Optional[str] = Field(None, description="Version if applicable")
    deprecated: bool = Field(False, description="Is this entity deprecated?")
    
    # Metadata
    source_reference: Optional[str] = Field(None, description="Documentation link")
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Relationship(BaseModel):
    """Relationship between entities."""
    id: str = Field(..., description="Unique identifier")
    source_id: str = Field(..., description="Source entity ID")
    target_id: str = Field(..., description="Target entity ID")
    relationship_type: RelationshipType = Field(...)
    
    # Relationship properties
    cardinality: str = Field("1:1", description="1:1, 1:N, N:M")
    bidirectional: bool = Field(False, description="Is relationship symmetric?")
    confidence: float = Field(1.0, description="Confidence 0-1")
    
    # Metadata
    description: str = Field("", description="What this relationship means")
    conditions: List[str] = Field(default_factory=list, description="When this relationship applies")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeGraph(BaseModel):
    """Complete knowledge graph."""
    entities: List[Entity] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        for e in self.entities:
            if e.id == entity_id:
                return e
        return None
    
    def get_related(self, entity_id: str, rel_type: RelationshipType) -> List[Entity]:
        related_ids = []
        for r in self.relationships:
            if r.source_id == entity_id and r.relationship_type == rel_type:
                related_ids.append(r.target_id)
            elif r.bidirectional and r.target_id == entity_id and r.relationship_type == rel_type:
                related_ids.append(r.source_id)
        
        return [e for e in self.entities if e.id in related_ids]
```

### 3.2 Taxonomy Module (`knowledge/taxonomy/`)

**Purpose**: Hierarchical pattern classification with domains.

```python
# knowledge/taxonomy/domains.py

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class Domain(str, Enum):
    """Top-level pattern domains."""
    ARCHITECTURE = "architecture"
    DATA = "data"
    NETWORK = "network"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    OPERATIONS = "operations"
    INTEGRATION = "integration"


class SubDomain(str, Enum):
    """Architecture sub-domains."""
    # Architecture
    COMPUTE = "compute"
    STORAGE = "storage"
    Messaging = "messaging"
    API = "api"
    
    # Data
    DATABASE = "database"
    ANALYTICS = "analytics"
    CACHE = "cache"
    
    # Security
    AUTH = "auth"
    ENCRYPTION = "encryption"
    NETWORK_SECURITY = "network_security"
    
    # Compliance
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI = "pci"


class TaxonomyNode(BaseModel):
    """Hierarchical taxonomy node."""
    id: str = Field(...)
    name: str = Field(...)
    domain: Domain = Field(...)
    sub_domain: Optional[SubDomain] = Field(None)
    parent_id: Optional[str] = Field(None, description="Parent node for hierarchy")
    
    # Classification
    description: str = ""
    keywords: List[str] = Field(default_factory=list)
    
    # Relationships to patterns
    pattern_ids: List[str] = Field(default_factory=list)
    
    # Priority and confidence
    priority: int = Field(5)
    confidence: float = Field(0.0)


class Taxonomy(BaseModel):
    """Complete taxonomy with hierarchy."""
    nodes: List[TaxonomyNode] = Field(default_factory=list)
    
    def get_by_domain(self, domain: Domain) -> List[TaxonomyNode]:
        return [n for n in self.nodes if n.domain == domain]
    
    def get_children(self, parent_id: str) -> List[TaxonomyNode]:
        return [n for n in self.nodes if n.parent_id == parent_id]
    
    def get_root_nodes(self) -> List[TaxonomyNode]:
        return [n for n in self.nodes if n.parent_id is None]
```

### 3.3 Use Case Module (`knowledge/usecases/`)

**Purpose**: Formalized user scenarios mapped to patterns.

```python
# knowledge/usecases/model.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class UseCaseType(str, Enum):
    """Types of use cases."""
    BUSINESS = "business"
    TECHNICAL = "technical"
    INTEGRATION = "integration"
    MIGRATION = "migration"


class Priority(str, Enum):
    """Use case priority."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Actor(BaseModel):
    """User or system performing actions."""
    name: str = Field(...)
    type: str = Field(..., description="user, system, service")


class Scenario(BaseModel):
    """A single user journey."""
    id: str = Field(...)
    name: str = Field(...)
    steps: List[str] = Field(default_factory=list, description="Step-by-step actions")
    
    # Preconditions
    preconditions: List[str] = Field(default_factory=list)
    
    # Expected results
    postconditions: List[str] = Field(default_factory=list)


class AcceptanceCriteria(BaseModel):
    """Criteria for validating use case completion."""
    id: str = Field(...)
    description: str = Field(...)
    
    # Validation
    testable: bool = Field(True, description="Can this be automatically tested?")
    validation_method: Optional[str] = Field(None, description="How to validate")
    expected_outcome: str = Field(...)


class UseCase(BaseModel):
    """Complete use case definition."""
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Human-readable name")
    type: UseCaseType = Field(...)
    
    # Classification
    description: str = Field("")
    domain: str = Field(..., description="Business domain")
    
    # Actors and scenarios
    actors: List[Actor] = Field(default_factory=list)
    scenarios: List[Scenario] = Field(default_factory=list)
    
    # Pattern mapping
    applicable_patterns: List[str] = Field(default_factory=list, description="Pattern IDs that apply")
    required_services: List[str] = Field(default_factory=list, description="Required platform services")
    
    # Constraints
    constraints: List[str] = Field(default_factory=list, description="Constraint IDs that apply")
    
    # Quality attributes
    required_quality: List[str] = Field(default_factory=list, description="Quality attributes needed")
    
    # Acceptance
    acceptance_criteria: List[AcceptanceCriteria] = Field(default_factory=list)
    
    # Priority
    priority: Priority = Field(Priority.MEDIUM)
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UseCaseToPatternMapper:
    """Maps use cases to applicable patterns."""
    
    def __init__(self):
        self._use_case_patterns: Dict[str, List[str]] = {}
        self._domain_patterns: Dict[str, List[str]] = {}
    
    def register_mapping(self, use_case: UseCase, pattern_ids: List[str]) -> None:
        self._use_case_patterns[use_case.id] = pattern_ids
    
    def get_patterns(self, use_case: UseCase) -> List[str]:
        # Direct mapping
        if use_case.id in self._use_case_patterns:
            return self._use_case_patterns[use_case.id]
        
        # Domain-based inference
        if use_case.domain in self._domain_patterns:
            return self._domain_patterns[use_case.domain]
        
        return use_case.applicable_patterns
```

### 3.4 ADR Module (`knowledge/adrs/`)

**Purpose**: Document architectural decisions with rationale.

```python
# knowledge/adrs/model.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class DecisionStatus(str, Enum):
    """Status of architectural decision."""
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


class DecisionCategory(str, Enum):
    """Category of decision."""
    ARCHITECTURE = "architecture"
    TECHNOLOGY = "technology"
    SECURITY = "security"
    PERFORMANCE = "performance"
    INTEGRATION = "integration"


class Alternative(BaseModel):
    """Alternative considered."""
    id: str = Field(...)
    name: str = Field(...)
    description: str = Field("")
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)


class ADR(BaseModel):
    """Architecture Decision Record."""
    id: str = Field(..., description="ADR number, e.g., ADR-001")
    title: str = Field(..., description="Short decision title")
    
    # Context
    status: DecisionStatus = Field(...)
    category: DecisionCategory = Field(...)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Decision
    decision: str = Field(..., description="The decision made")
    decision_date: Optional[datetime] = Field(None)
    
    # Context and rationale
    context: str = Field("", description="Context leading to decision")
    rationale: str = Field("", description="Why this decision was made")
    
    # Alternatives considered
    alternatives: List[Alternative] = Field(default_factory=list)
    selected_alternative: Optional[str] = Field(None)
    
    # Consequences
    positive_consequences: List[str] = Field(default_factory=list)
    negative_consequences: List[str] = Field(default_factory=list)
    
    # Related decisions
    supersedes: List[str] = Field(default_factory=list, description="ADR IDs this supersedes")
    superseded_by: Optional[str] = Field(None, description="ADR ID that supersedes this")
    
    # Metadata
    author: str = Field("")
    tags: List[str] = Field(default_factory=list)


class ADRRepository:
    """Repository for ADRs."""
    
    def __init__(self):
        self._adrs: Dict[str, ADR] = {}
    
    def add(self, adr: ADR) -> None:
        self._adrs[adr.id] = adr
    
    def get(self, adr_id: str) -> Optional[ADR]:
        return self._adrs.get(adr_id)
    
    def list_by_status(self, status: DecisionStatus) -> List[ADR]:
        return [a for a in self._adrs.values() if a.status == status]
    
    def list_by_category(self, category: DecisionCategory) -> List[ADR]:
        return [a for a in self._adrs.values() if a.category == category]
    
    def get_decision_chain(self, adr_id: str) -> List[ADR]:
        """Get full decision chain including superseded."""
        chain = []
        current = self.get(adr_id)
        
        while current:
            chain.append(current)
            if current.superseded_by:
                current = self.get(current.superseded_by)
            else:
                break
        
        return chain
```

### 3.5 Compatibility Module (`knowledge/compatibility/`)

**Purpose**: Define technology compatibility matrices.

```python
# knowledge/compatibility/matrix.py

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum


class CompatibilityLevel(str, Enum):
    """How well technologies work together."""
    SUPPORTED = "supported"
    RECOMMENDED = "recommended"
    NOT_SUPPORTED = "not_supported"
    DEPRECATED = "deprecated"
    REQUIRES_CONFIG = "requires_config"


class VersionConstraint(BaseModel):
    """Version constraint for a technology."""
    technology: str = Field(...)
    min_version: Optional[str] = Field(None)
    max_version: Optional[str] = Field(None)
    exact_version: Optional[str] = Field(None)


class TechnologyCompatibility(BaseModel):
    """Compatibility between two technologies."""
    technology_a: str = Field(...)
    technology_b: str = Field(...)
    compatibility: CompatibilityLevel = Field(...)
    
    # Details
    min_version_a: Optional[str] = Field(None)
    min_version_b: Optional[str] = Field(None)
    
    # Configuration required
    config_required: List[str] = Field(default_factory=list)
    
    # Notes
    notes: str = Field("")
    documentation_link: Optional[str] = Field(None)


class CompatibilityMatrix(BaseModel):
    """Complete compatibility matrix."""
    name: str = Field(..., description="Matrix name, e.g., 'SAP BTP Services'")
    version: str = Field("1.0.0")
    
    # Compatibility entries
    entries: List[TechnologyCompatibility] = Field(default_factory=list)
    
    def check_compatibility(self, tech_a: str, tech_b: str) -> Optional[CompatibilityLevel]:
        for entry in self.entries:
            if (entry.technology_a == tech_a and entry.technology_b == tech_b) or \
               (entry.technology_b == tech_a and entry.technology_a == tech_b):
                return entry.compatibility
        return None
    
    def validate_stack(self, technologies: List[str]) -> Dict[str, Any]:
        """Validate a complete technology stack."""
        violations = []
        warnings = []
        
        for i, tech_a in enumerate(technologies):
            for tech_b in technologies[i+1:]:
                compat = self.check_compatibility(tech_a, tech_b)
                
                if compat == CompatibilityLevel.NOT_SUPPORTED:
                    violations.append(f"{tech_a} not compatible with {tech_b}")
                elif compat == CompatibilityLevel.DEPRECATED:
                    warnings.append(f"{tech_a} deprecated with {tech_b}")
        
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
        }


class TechStackValidator:
    """Validates complete technology stacks."""
    
    def __init__(self):
        self._matrices: Dict[str, CompatibilityMatrix] = {}
    
    def register_matrix(self, matrix: CompatibilityMatrix) -> None:
        self._matrices[matrix.name] = matrix
    
    def validate(self, stack: List[str], domain: str = "default") -> Dict[str, Any]:
        if domain in self._matrices:
            return self._matrices[domain].validate_stack(stack)
        
        # Check all matrices
        all_violations = []
        for matrix in self._matrices.values():
            result = matrix.validate_stack(stack)
            all_violations.extend(result.get("violations", []))
        
        return {
            "valid": len(all_violations) == 0,
            "violations": all_violations,
        }
```

### 3.6 Quality Attributes Module (`knowledge/quality/`)

**Purpose**: Handle Non-Functional Requirements (NFRs).

```python
# knowledge/quality/model.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class QualityAttributeType(str, Enum):
    """Types of quality attributes."""
    PERFORMANCE = "performance"
    SECURITY = "security"
    SCALABILITY = "scalability"
    AVAILABILITY = "availability"
    MAINTAINABILITY = "maintainability"
    USABILITY = "usability"
    RELIABILITY = "reliability"
    DEPLOYABILITY = "deployability"


class TargetType(str, Enum):
    """How quality target is expressed."""
    EXACT = "exact"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    RANGE = "range"


class QualityTarget(BaseModel):
    """Target for a quality attribute."""
    attribute: QualityAttributeType = Field(...)
    target_type: TargetType = Field(...)
    value: str = Field(..., description="Target value, e.g., '99.9%', '<100ms'")
    unit: str = Field("", description="Unit of measurement")
    
    # Context
    conditions: List[str] = Field(default_factory=list)
    notes: str = Field("")


class QualityProfile(BaseModel):
    """Collection of quality targets for a system."""
    id: str = Field(...)
    name: str = Field(..., description="Profile name, e.g., 'SAP CAP Production'")
    description: str = Field("")
    
    # Targets
    targets: List[QualityTarget] = Field(default_factory=list)
    
    # Metadata
    platform: Optional[str] = Field(None)
    environment: Optional[str] = Field(None, description="dev, staging, prod")


class QualityAssessor(BaseModel):
    """Assesses architecture against quality targets."""
    
    def assess(self, profile: QualityProfile, features: Dict[str, Any]) -> Dict[str, Any]:
        results = []
        
        for target in profile.targets:
            assessment = self._assess_target(target, features)
            results.append(assessment)
        
        passed = [r for r in results if r.get("passed")]
        failed = [r for r in results if not r.get("passed")]
        
        return {
            "profile": profile.name,
            "overall_passed": len(failed) == 0,
            "passed": passed,
            "failed": failed,
            "score": len(passed) / len(results) if results else 1.0,
        }
    
    def _assess_target(self, target: QualityTarget, features: Dict[str, Any]) -> Dict[str, Any]:
        # Simplified assessment logic
        # Real implementation would be more sophisticated
        feature_value = features.get(target.attribute.value)
        
        return {
            "attribute": target.attribute.value,
            "target": target.value,
            "actual": feature_value,
            "passed": True,  # Simplified
        }
```

### 3.7 Reference Architecture Module (`knowledge/reference/`)

**Purpose**: Curated reference architectures linked to patterns.

```python
# knowledge/reference/model.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class ArchType(str, Enum):
    """Type of reference architecture."""
    FOUNDATIONAL = "foundational"
    REFERENCE = "reference"
    PATTERN = "pattern"
    TEMPLATE = "template"


class ComponentRef(BaseModel):
    """Reference to a component in the architecture."""
    name: str = Field(...)
    type: str = Field(...)
    technology: str = Field(...)
    
    # Configuration
    config_template: Optional[str] = Field(None)
    config_values: Dict[str, Any] = Field(default_factory=dict)
    
    # Dependencies
    depends_on: List[str] = Field(default_factory=list)


class DataFlowRef(BaseModel):
    """Data flow in the reference architecture."""
    from_component: str = Field(...)
    to_component: str = Field(...)
    protocol: str = Field(...)
    data_format: Optional[str] = Field(None)


class ReferenceArchitecture(BaseModel):
    """Complete reference architecture."""
    id: str = Field(..., description="Unique identifier")
    name: str = Field(...)
    type: ArchType = Field(...)
    
    # Description
    description: str = Field("")
    platform: str = Field(..., description="Platform this arch targets")
    
    # Components
    components: List[ComponentRef] = Field(default_factory=list)
    data_flows: List[DataFlowRef] = Field(default_factory=list)
    
    # Pattern linkage
    patterns: List[str] = Field(default_factory=list, description="Pattern IDs this arch uses")
    
    # Constraints
    constraints: List[str] = Field(default_factory=list, description="Constraint IDs that apply")
    
    # Quality expectations
    quality_profile: Optional[str] = Field(None)
    
    # Code reference
    repo_url: Optional[str] = Field(None, description="Reference implementation")
    documentation_url: Optional[str] = Field(None)
    
    # Metadata
    version: str = Field("1.0.0")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ReferenceArchCatalog:
    """Catalog of reference architectures."""
    
    def __init__(self):
        self._archs: Dict[str, ReferenceArchitecture] = {}
    
    def add(self, arch: ReferenceArchitecture) -> None:
        self._archs[arch.id] = arch
    
    def get(self, arch_id: str) -> Optional[ReferenceArchitecture]:
        return self._archs.get(arch_id)
    
    def list_by_platform(self, platform: str) -> List[ReferenceArchitecture]:
        return [a for a in self._archs.values() if a.platform == platform]
    
    def find_by_patterns(self, pattern_ids: List[str]) -> List[ReferenceArchitecture]:
        results = []
        for arch in self._archs.values():
            if any(p in pattern_ids for p in arch.patterns):
                results.append(arch)
        return results
```

---

## 4. Implementation Phases

### Phase 1: Foundation (Weeks 1-2)

**Goal**: Establish core knowledge infrastructure.

| Task | Files | Description |
|------|-------|-------------|
| 4.1.1 | `knowledge/__init__.py` | Module structure |
| 4.1.2 | `knowledge/ontology/entities.py` | Entity, Relationship models |
| 4.1.3 | `knowledge/taxonomy/domains.py` | Domain enum, TaxonomyNode |
| 4.1.4 | Knowledge base loader | Load/unload utilities |

### Phase 2: Knowledge Definitions (Weeks 3-4)

**Goal**: Populate core knowledge structures.

| Task | Files | Description |
|------|-------|-------------|
| 4.2.1 | `knowledge/usecases/model.py` | UseCase, Scenario models |
| 4.2.2 | `knowledge/adrs/model.py` | ADR model with templates |
| 4.2.3 | Seed data for 10 use cases | Business scenarios |
| 4.2.4 | Seed 20 ADRs for SAP/Tanzu/PowerPlatform | Initial decisions |

### Phase 3: Intelligence Enhancements (Weeks 5-6)

**Goal**: Add compatibility and quality handling.

| Task | Files | Description |
|------|-------|-------------|
| 4.3.1 | `knowledge/compatibility/matrix.py` | Compatibility matrix |
| 4.3.2 | `knowledge/quality/model.py` | Quality profiles |
| 4.3.3 | Technology compatibility data | 50+ tech relationships |
| 4.3.4 | Quality profiles per platform | Production profiles |

### Phase 4: Reference Architectures (Weeks 7-8)

**Goal**: Create reference architecture system.

| Task | Files | Description |
|------|-------|-------------|
| 4.4.1 | `knowledge/reference/model.py` | Reference architecture models |
| 4.4.2 | SAP BTP reference arch | 3 complete architectures |
| 4.4.3 | Tanzu reference arch | 2 complete architectures |
| 4.4.4 | PowerPlatform reference arch | 2 complete architectures |

### Phase 5: Integration & API (Weeks 9-10)

**Goal**: Expose new capabilities via API.

| Task | Files | Description |
|------|-------|-------------|
| 4.5.1 | Extend `/api/adapters.py` | New knowledge endpoints |
| 4.5.2 | `/knowledge/query` endpoint | Unified knowledge query |
| 4.5.3 | `/knowledge/search` endpoint | Semantic search |
| 4.5.4 | `/knowledge/validate` endpoint | Stack validation |

### Phase 6: Testing & Documentation (Weeks 11-12)

**Goal**: Verify and document.

| Task | Files | Description |
|------|-------|-------------|
| 4.6.1 | Unit tests for new modules | 80% coverage minimum |
| 4.6.2 | Integration tests | API endpoint tests |
| 4.6.3 | API documentation | OpenAPI specs |
| 4.6.4 | Architecture documentation | Component docs |

---

## 5. Backward Compatibility

All existing APIs remain unchanged. New capabilities are additive:

```python
# EXISTING API (unchanged)
POST /adapter/query        # Works as before
GET  /adapter/platforms   # Works as before
GET  /adapter/patterns    # Works as before

# NEW APIs (additive)
GET  /knowledge/ontology     # Entity search
GET  /knowledge/taxonomy    # Domain taxonomy
GET  /knowledge/usecases      # Use case catalog
GET  /knowledge/adrs         # Decision records
GET  /knowledge/compatible   # Stack validation
GET  /knowledge/reference  # Reference architectures
POST /knowledge/validate    # Validate stack
```

---

## 6. Success Metrics

| Metric | Target |
|--------|--------|
| Knowledge domain coverage | 85%+ (from 35%) |
| Taxonomy domains | 6+ (from 1) |
| Use cases defined | 50+ |
| ADRs documented | 100+ |
| Technology compatibility entries | 200+ |
| Reference architectures | 10+ |
| Test coverage | 85%+ |

---

## 7. Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Scope creep | Fixed phase boundaries |
| Knowledge curation effort | Seed data only, extensibility built-in |
| Performance impact | Lazy loading, caching |
| Adoption | Additive changes only |

---

This plan provides a production-grade, extensible knowledge domain platform that addresses all identified gaps while maintaining backward compatibility.