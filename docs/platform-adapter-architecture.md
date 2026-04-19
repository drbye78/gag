# Platform Adapter Architecture

## Overview

The Platform Adapter architecture enables the Engineering Intelligence System to reason about and generate solutions for any technology stack through a pluggable adapter system. This allows the system to support SAP BTP, VMware Tanzu, Microsoft Power Platform, AWS, Azure, and other platforms without modifying core logic.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     KNOWLEDGE PROCESSING PIPELINE                    │
│                                                                      │
│   Input Query ──► IR Features ──► Pattern Matcher ──► Constraints │
│                                                │                    │
│                                                ▼                    │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                   PLATFORM ADAPTERS                          │  │
│   │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐   │  │
│   │  │ SAP BTP     │ │ VMware Tanzu │ │ Power Platform  │   │  │
│   │  │ Adapter     │ │ Adapter     │ │ Adapter         │   │  │
│   │  └──────────────┘ └──────────────┘ └──────────────────┘   │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                │                    │
│                                                ▼                    │
│                              Config Templates + Code + Explanation    │
└─────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. IR Feature Extraction (`models/ir.py`)

Platform-agnostic feature representation:

```python
class IRFeature(BaseModel):
    has_async: bool
    has_auth: bool
    has_database: bool
    has_api: bool
    has_ui: bool
    has_microservices: bool
    has_event_driven: bool
    has_serverless: bool
    has_container: bool
    data_classification: str
    compliance_requirements: List[str]
    scalability_required: bool
    high_availability_required: bool
    multi_tenant: bool
```

### 2. Pattern Library (`core/patterns/`)

Architectural patterns that apply across platforms:

| Pattern | Domain | Key Benefits |
|---------|--------|---------------|
| event_driven | Architecture | Decoupling, Scalability |
| microservices | Architecture | Independent scaling |
| serverless | Architecture | Auto-scaling, Pay per use |
| api_first | Architecture | Documentation, Integrations |
| cqrs | Architecture | Optimized read/write |
| circuit_breaker | Architecture | Failure isolation |
| backends_for_frontend | Architecture | Frontend optimization |
| strangler_fig | Architecture | Incremental migration |

### 3. Constraint Engine (`core/constraints/`)

Platform-specific rules that validate architectures:

**Constraint Types:**
- **Hard**: Must pass (blocks deployment)
- **Soft**: Advisory (warnings)

**Platform Constraints:**

| Platform | Constraint | Type | Message |
|----------|-----------|------|---------|
| SAP BTP | XSUAA Required | Hard | SAP BTP apps require authentication |
| SAP BTP | Multi-tenant IAS | Soft | Multi-tenant needs Identity Authentication |
| Power Platform | Dataverse Required | Hard | Power Apps require Dataverse |
| VMware Tanzu | Service Account | Soft | Should use service accounts |
| VMware Tanzu | Resource Limits | Soft | Production needs resource limits |

### 4. Platform Adapters (`core/adapters/`)

Each adapter provides:

```python
class PlatformAdapter(ABC):
    @property
    def platform_id(self) -> str
    
    @property
    def supported_services(self) -> List[str]
    
    @property
    def patterns(self) -> List[Pattern]
    
    @property
    def constraints(self) -> ConstraintSet
    
    def transform_ir_to_platform(self, input: AdapterInput) -> AdapterOutput
    
    def generate_config(self, features: IRFeature) -> Dict[str, str]
    
    def generate_code(self, features: IRFeature) -> Dict[str, str]
```

#### SAP BTP Adapter

**Supported Services:**
- xsuaa, identity, hana, hdi-container
- destination, connectivity, workflow
- mta, approuter, business-logic

**Generated Configs:**
- `xsuaa.json` - XSUAA service configuration
- `mta.yaml` - MTA deployment descriptor
- `package.json` - CAP application package

#### VMware Tanzu Adapter

**Supported Services:**
- spring-boot, spring-cloud-function
- knative, eventing
- service-bindings, ingress

**Generated Configs:**
- `deployment.yaml` - Kubernetes deployment
- `knative-service.yaml` - Knative service
- `pom.xml` - Maven project

#### Power Platform Adapter

**Supported Services:**
- powerapps, powerpages, powerautomate
- dataverse, dynamics
- copilot-studio, ai-builder

**Generated Configs:**
- `dataverse-table.json` - Dataverse table schema
- `powerautomate-flow.json` - Flow definition

## Processing Flow

```python
async def process(query: str, platform: str) -> AdapterOutput:
    # 1. Extract features from query
    features = extract_features(query)
    
    # 2. Match against patterns
    patterns = pattern_matcher.match(features)
    
    # 3. Evaluate constraints
    violations = constraint_engine.evaluate(features, platform)
    
    # 4. Get platform adapter
    adapter = registry.get(platform)
    
    # 5. Transform to platform-specific output
    return adapter.transform(
        features=features,
        patterns=patterns,
        violations=violations
    )
```

## Extending the Platform

### Adding a New Platform

1. **Create the adapter:**

```python
# core/adapters/aws.py
class AWSAdapter(PlatformAdapter):
    @property
    def platform_id(self) -> str:
        return "aws"
    
    # Implement all abstract methods...
```

2. **Register in registry:**

```python
# core/adapters/__init__.py
from core.adapters.aws import AWSAdapter
registry.register(AWSAdapter())
```

3. **Add platform constraints:**

```python
# core/constraints/engine.py
aws_constraints = ConstraintSet(
    id="aws",
    name="AWS Constraints",
    constraints=[
        Constraint(
            id="aws_iam_required",
            name="IAM Required",
            domain="security",
            type="hard",
            feature="has_auth",
            operator="eq",
            threshold=True,
            message="AWS resources require IAM roles",
            fix_hint="Add IAM role to resource",
            platforms=["aws"]
        )
    ]
)
```

### Adding a New Pattern

```python
# core/patterns/schema.py
new_pattern = Pattern(
    id="hexagonal",
    name="Hexagonal Architecture",
    domain="architecture",
    triggers=["hexagonal", "ports", "adapters"],
    conditions=[
        PatternCondition(feature="has_api", operator="eq", value=True),
    ],
    components=["port", "adapter", "domain"],
    benefits=["Testability", "Flexibility"],
    tradeoffs=["Complexity"],
    priority=8,
    confidence=0.85
)
library.register(new_pattern)
```

## Auto-Detection

The adapter registry supports automatic platform detection:

```python
registry.auto_detect(features: IRFeature) -> PlatformAdapter

# Detection rules:
# "sap" → xsuaa, hana, cap, cloudfoundry, kyma
# "salesforce" → salesforce, lightning, apex
# "powerplatform" → powerapps, dataverse, powerautomate
# "tanzu" → tanzu, spring, knative, pivotal
# "aws" → lambda, s3, ec2, iam
# "azure" → azure, function, aks
```

## Output Format

Each adapter produces:

```python
class AdapterOutput:
    recommendations: List[Dict]      # Suggested patterns/approaches
    architecture_diagram: str         # Optional diagram
    config_templates: Dict[str, str]  # Platform-specific configs
    code_snippets: Dict[str, str]      # Code templates
    deployment_manifests: Dict[str, str] # K8s/helm manifests
    explanation: str                  # Human-readable explanation
    confidence: float                 # 0-1 confidence score
    can_deploy: bool                 # If no hard constraints violated
```

## Example Usage

```python
from models.ir import PlatformContext
from core.pipeline import get_knowledge_pipeline

pipeline = get_knowledge_pipeline()

result = await pipeline.process(
    query="Build a serverless API with authentication",
    platform_context=PlatformContext(platform="sap")
)

print(result.config_templates)  # xsuaa.json, mta.yaml
print(result.can_deploy)       # False if constraints violated
print(result.explanation)       # "Recommended: Serverless | Blocking issues: 1"
```

## Benefits

1. **Platform Agnostic Core**: Logic doesn't change when adding new platforms
2. **Extensible**: New platforms = new adapter file, no core changes
3. **Validated**: Constraint engine prevents invalid architectures
4. **Traceable**: Full reasoning from query to output
5. **Generative**: Produces deployable configs, not just recommendations
