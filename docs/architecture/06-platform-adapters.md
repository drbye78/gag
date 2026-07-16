# Platform Adapters & Knowledge Layer Architecture

The system provides universal domain intelligence through pluggable platform adapters and a knowledge substrate. This document covers the adapter architecture, knowledge layer, and cross-platform reasoning.

## Architecture Overview

```
Query → Knowledge Resolver → Platform Adapter → Platform-specific Output
                      ↓
            Knowledge Graph (platforms, services, patterns)
```

### Data Flow

```
1. User Query: "deploy lambda with dynamodb"
2. Knowledge Resolver extracts: IRFeature(has_serverless=True, has_database=True)
3. Pattern Matching: serverless, data patterns
4. Constraint Check: all passed
5. Platform Adapter Selection: AWSAdapter
6. Output Generation: Lambda config, IAM role, CloudFormation
```

## Platform Adapters

### Adapters (`core/adapters/`)

| Adapter | Platform ID | Services | File |
|---------|------------|---------|------|
| `SAPBTPAdapter` | `sap` | XSUAA, HANA, Kyma, CAP | `sap.py` |
| `VMwareTanzuAdapter` | `tanzu` | Kubernetes, Spring, TAS | `tanzu.py` |
| `PowerPlatformAdapter` | `powerplatform` | Power Apps, Dataverse | `powerplatform.py` |
| `AWSAdapter` | `aws` | Lambda, S3, DynamoDB, EKS | `clouds.py` |
| `AzureAdapter` | `azure` | Functions, Cosmos DB, AKS | `clouds.py` |
| `GCPAdapter` | `gcp` | Cloud Functions, Firestore, GKE | `clouds.py` |

### Adapter Interface (`core/adapters/base.py`)

```python
class PlatformAdapter(ABC):
    @property
    def platform_id(self) -> str: ...

    @property
    def supported_services(self) -> List[str]: ...

    @property
    def patterns(self) -> List[Pattern]: ...

    @property
    def constraints(self) -> List[Constraint]: ...

    def transform_ir_to_platform(self, input: AdapterInput) -> AdapterOutput:
        # Transform generic IR to platform-specific artifacts
        ...

    def generate_config(self, features: IRFeature) -> Dict[str, str]:
        # Generate platform-specific config
        ...

    def generate_code(self, features: IRFeature) -> Dict[str, str]:
        # Generate platform-specific code
        ...
```

### Creating a Custom Adapter

```python
from core.adapters.base import PlatformAdapter, AdapterInput, AdapterOutput

class MyCustomAdapter(PlatformAdapter):
    @property
    def platform_id(self) -> str:
        return "myplatform"
    
    @property
    def supported_services(self) -> List[str]:
        return ["service1", "service2"]
    
    @property
    def patterns(self) -> List[Pattern]:
        return [
            Pattern(id="my-pattern", domain=PatternDomain.ARCHITECTURE)
        ]
    
    @property
    def constraints(self) -> List[Constraint]:
        return [
            Constraint(id="max-timeout", type=ConstraintType.HARD, 
                      condition={"timeout": {"lt": 300}})
        ]
    
    def transform_ir_to_platform(self, input: AdapterInput) -> AdapterOutput:
        # Transform IR features to platform artifacts
        return AdapterOutput(
            configs=self.generate_config(input.ir_features),
            code=self.generate_code(input.ir_features),
            metadata={"platform": self.platform_id}
        )
    
    def generate_config(self, features: IRFeature) -> Dict[str, str]:
        # Generate platform config (YAML, JSON, etc.)
        return {"config.yaml": "..."}
    
    def generate_code(self, features: IRFeature) -> Dict[str, str]:
        # Generate platform code
        return {"main.py": "..."}
```

### Adapter Registry

```python
from core.adapters import get_adapter_registry

# Get specific adapter
registry = get_adapter_registry()
adapter = registry.get("aws")

# Auto-detect from features
adapter = registry.auto_detect(features)

# List all platforms
platforms = registry.list_platforms()

# Check platform capabilities
if registry.has_service("aws", "lambda"):
    ...
```

### Adapter Example: AWS Serverless

```python
adapter = registry.get("aws")

# Input features from query analysis
features = IRFeature(
    has_serverless=True,
    has_event_driven=True,
    has_async=True,
    has_database=True,
    has_storage=True
)

# Transform to platform-specific output
output = adapter.transform_ir_to_platform(AdapterInput(
    ir_features=features,
    pattern_matches=[serverless_pattern, event_driven_pattern],
    constraint_violations=[],
    platform_context={"region": "us-east-1"}
))

# Output includes Lambda config, IAM role, CloudFormation template
print(output.configs)  # { "lambda.yaml": "...", "iam.yaml": "..." }
print(output.code)       # { "handler.py": "..." }
```

## Knowledge Layer

### Knowledge Graph (`core/knowledge/graph.py`)

| Node Type | Description |
|-----------|-------------|
| `PLATFORM` | Cloud platform (AWS, Azure, GCP, SAP, Tanzu) |
| `SERVICE` | Managed service (Lambda, Functions, HANA) |
| `TECHNOLOGY` | Technology (REST, GraphQL, Kubernetes) |
| `PATTERN` | Architectural pattern |
| `CONSTRAINT` | Platform constraint |
| `USE_CASE` | Use case definition |
| `REFERENCE_ARCH` | Reference architecture |
| `DECISION` | Architecture decision |

### Edge Types

| Edge Type | Description |
|-----------|-------------|
| `REQUIRES` | Service requires another |
| `PROVIDES` | Platform provides service |
| `IMPLEMENTS` | Pattern implements architecture |
| `CONFLICTS` | Incompatible with |
| `ALTERNATIVE` | Alternative to |
| `DEPENDS_ON` | Dependency |
| `WORKS_WITH` | Compatible with |
| `COMPOSED_OF` | Contains |

### Seed Data

**Platforms** (6):
- SAP BTP, VMware Tanzu, Power Platform, AWS, Azure, GCP

**Services** (12):
- SAP: XSUAA, HANA, Kyma
- AWS: Lambda, S3, DynamoDB
- Azure: Functions, Cosmos DB
- GCP: Cloud Functions, Firestore

## Ontology (`core/knowledge/ontology.py`)

### Extracted Entities

| Type | Attributes |
|------|------------|
| `ExtractedEntity` | name, type, role, properties, confidence |
| `EntityRole` | PRIMARY, RELATED, DEPENDENCY |
| `QueryIntent` | type, query, context, expected_sources |

### IR Features (v2)

Platform-agnostic feature extraction:

```python
class IRFeatureV2(BaseModel):
    # Serverless
    has_serverless: bool = False
    has_functions: bool = False

    # Data
    has_database: bool = False
    has_storage: bool = False

    # Integration
    has_async: bool = False
    has_event_driven: bool = False
    has_api: bool = False

    # Security
    has_auth: bool = False
    has_oauth: bool = False

    # Architecture
    has_microservices: bool = False
    has_container: bool = False
```

## Taxonomy (`core/knowledge/taxonomy.py`)

### Pattern Domains

| Domain | Patterns |
|--------|-----------|
| `ARCHITECTURE` | microservices, serverless, event-driven, cqrs, saga |
| `INTEGRATION` | api-gateway, message-queue, etl, webhook |
| `DATA` | relational, nosql, cache, search |
| `INFRASTRUCTURE` | container,编排, serverless, hybrid |
| `SECURITY` | oauth, jwt, iam, encryption |

### Pattern Examples

| Pattern | Domain | Quality Impact |
|---------|--------|----------------|
| `microservices` | ARCHITECTURE | Scalability +2, Complexity +1, Ops +2 |
| `serverless` | ARCHITECTURE | Cost -2, Vendor lock-in +1, Latency +1 |
| `event-driven` | ARCHITECTURE | Coupling -1, Complexity +1, Observability +2 |
| `cqrs` | ARCHITECTURE | Performance +2, Complexity +2, Consistency -1 |
| `api-gateway` | INTEGRATION | Security +2, Rate limiting +2, Latency +1 |

## Constraints (`core/knowledge/constraints.py`)

### Constraint Types

| Type | Behavior |
|------|----------|
| `HARD` | Fail if violated |
| `SOFT` | Warning if violated |

### Example Rules

```python
rules = [
    ConstraintRule(
        id="serverless-timeout",
        type=HARD,
        condition={"has_serverless": True, "timeout_seconds": {"gt": 900}},
        message="Lambda max timeout is 900 seconds",
        fix="Reduce timeout or use ECS"
    ),
    ConstraintRule(
        id="database-region",
        type=SOFT,
        condition={"database_region": {"ne": "primary_region"}},
        message="Cross-region database has latency",
        fix="Use primary region for database"
    )
]
```

## Use Cases (`core/knowledge/usecases.py`)

### Pre-built Use Cases (7)

| ID | Name | Platforms | Category |
|----|------|-----------|-----------|
| `uc-sap-rest-integration` | SAP REST API Integration | SAP | INTEGRATION |
| `uc-sap-function-flow` | SAP Kyma Serverless | SAP | DEVELOPMENT |
| `uc-k8s-microservices` | Kubernetes Microservices | Tanzu | OPERATIONS |
| `uc-powerapps-crm` | Power Apps CRM | Power Platform | AUTOMATION |
| `uc-aws-lambda-api` | AWS Lambda API Gateway | AWS | DEVELOPMENT |
| `uc-azure-functions-http` | Azure Functions HTTP | Azure | DEVELOPMENT |
| `uc-gcp-cloud-run` | GCP Cloud Run | GCP | OPERATIONS |

## ADRs (`core/knowledge/adrs.py`)

### Architecture Decision Records (5)

| ID | Title | Status |
|----|-------|--------|
| `adr-001` | Use Serverless for Event-Driven | ACCEPTED |
| `adr-002` | Use Kubernetes for Container Orchestration | ACCEPTED |
| `adr-003` | Use Managed Databases Over Self-Hosted | ACCEPTED |
| `adr-004` | Use API Gateway for All External APIs | ACCEPTED |
| `adr-005` | Adopt Platform-Agnostic Patterns | ACCEPTED |

## Reference Architectures (`core/knowledge/reference.py`)

### Pre-built Architectures (8)

| ID | Name | Type | Platforms |
|----|------|------|-----------|
| `ref-serverless-aws` | AWS Serverless API | SERVERLESS | AWS |
| `ref-serverless-azure` | Azure Serverless API | SERVERLESS | Azure |
| `ref-serverless-gcp` | GCP Serverless API | SERVERLESS | GCP |
| `ref-microservices-k8s` | Kubernetes Microservices | MICROSERVICES | Tanzu, AWS, Azure, GCP |
| `ref-event-driven-aws` | AWS Event-Driven | EVENT_DRIVEN | AWS |
| `ref-event-driven-azure` | Azure Event-Driven | EVENT_DRIVEN | Azure |
| `ref-api-gateway-sap` | SAP API Gateway | API_GATEWAY | SAP |
| `ref-hybrid-sap-cloud` | SAP Hybrid Integration | HYBRID | SAP |

## Knowledge Resolver (`core/knowledge/resolver.py`)

### Capabilities

| Function | Description |
|----------|-------------|
| `resolve_intent()` | Detect query intent from text |
| `extract_entities()` | Extract named entities |
| `match_patterns()` | Find matching patterns |
| `evaluate_constraints()` | Check constraint violations |
| `get_recommendations()` | Get platform recommendations |

### Example Usage

```python
resolver = get_resolver()

result = await resolver.resolve(
    query="deploy lambda function with dynamodb"
)

# Returns:
# ResolutionResult(
#   intent=QueryIntent(type=IntentType.DESIGN),
#   entities=[Entity(name="lambda"), Entity(name="dynamodb")],
#   patterns=[Pattern(id="serverless"), Pattern(id="data")],
#   constraints=[],
#   recommendations=["aws", "lambda", "dynamodb"]
# )
```

## Platform-Agnostic Reasoning

The system enables cross-platform reasoning:

```python
# Compare "AWS Lambda" vs "Azure Functions" vs "GCP Cloud Functions"
result = await resolver.resolve(
    query="compare serverless functions across aws azure gcp"
)

# Returns platform-agnostic features, recommendations, and patterns
# that can map to any cloud provider
```

## Knowledge API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/knowledge/query` | POST | Knowledge-based query |
| `/knowledge/graph` | GET | Knowledge graph stats |
| `/knowledge/patterns` | GET | List all patterns |
| `/knowledge/constraints/{platform}` | GET | Platform constraints |

---

## Developer Guide

### Creating a Custom Adapter

This guide shows how to create a custom platform adapter for a new platform (e.g., Oracle Cloud, DigitalOcean).

#### Step 1: Define the Adapter Class

```python
from core.adapters.base import PlatformAdapter, AdapterOutput
from pydantic import BaseModel

class OracleCloudAdapter(PlatformAdapter):
    """Oracle Cloud Infrastructure adapter."""

    platform: str = "oracle"
    supported_services: list[str] = [
        "functions",
        "object_storage",
        "autonomous_db",
        "apiGateway"
    ]

    async def transform_ir_to_platform(
        self,
        input: AdapterInput
    ) -> AdapterOutput:
        # Transform IR features to Oracle-specific config
        configs = {}
        code = {}

        if input.ir_features.has_serverless:
            configs["function.yaml"] = self._generate_fn_config(input)
            code["handler.py"] = self._generate_handler(input)

        if input.ir_features.has_storage:
            configs["bucket.yaml"] = self._generate_bucket_config(input)

        return AdapterOutput(configs=configs, code=code)

    def _generate_fn_config(self, input: AdapterInput) -> str:
        return """Generate Oracle Functions config."""
        return """
        functions:
          fn_compartment_id: ${COMPARTMENT_ID}
          application:
            displayName: ${APP_NAME}
            sourceDirectory: src
        """

    def _generate_handler(self, input: AdapterInput) -> str:
        return """Generate handler code."""
        return '''def handler(ctx, data):
    return {"status": "ok"}
'''
```

#### Step 2: Register the Adapter

```python
# core/adapters/registry.py
from core.adapters import adapter_registry

@adapter_registry.register("oracle")
class OracleCloudAdapter(PlatformAdapter):
    ...

# Now available via registry
adapter = adapter_registry.get("oracle")
```

#### Step 3: Add to Knowledge Graph

```python
# core/knowledge/seed.py
ORACLE_SERVICES = {
    "oracle": {
        "functions": {
            "name": "Oracle Functions",
            "type": "serverless",
            "runtime": ["python", "node", "java", "go"],
            "memory": "1024MB",
            "timeout": "300s"
        },
        "object_storage": {
            "name": "Object Storage",
            "type": "storage",
            "tier": "Standard"
        }
    }
}
```

#### Step 4: Add Platform Constraints

```python
# core/constraints/oracle.py
from core.constraints.base import PlatformConstraints

class OracleConstraints(PlatformConstraints):
    platform = "oracle"

    hard_constraints = [
        Constraint(
            id="oracle_region",
            message="Oracle functions require specific region",
            check=lambda ctx: ctx.get("region") in OCI_REGIONS
        ),
        Constraint(
            id="oracle_memory",
            message="Max memory is 1024MB",
            check=lambda ctx: ctx.get("memory", 0) <= 1024
        )
    ]

    soft_constraints = [
        Constraint(
            id="oracle_cold_start",
            message="Consider warm containers for low latency",
            severity="warning"
        )
    ]
```

#### Step 5: Test the Adapter

```python
# tests/test_oracle_adapter.py
import pytest
from core.adapters import adapter_registry

@pytest.mark.asyncio
async def test_oracle_serverless():
    adapter = adapter_registry.get("oracle")

    result = await adapter.transform_ir_to_platform(AdapterInput(
        ir_features=IRFeature(has_serverless=True),
        pattern_matches=[serverless_pattern],
        constraint_violations=[],
        platform_context={"region": "us-phoenix-1"}
    ))

    assert "function.yaml" in result.configs
    assert "handler.py" in result.code
```

### Adapter Interface Reference

| Method | Description | Required |
|--------|-------------|----------|
| `transform_ir_to_platform()` | Transform IR to platform output | Yes |
| `validate_constraints()` | Check platform constraints | Yes |
| `list_services()` | List available services | No |
| `get_service_config()` | Get service configuration | No |

### Best Practices

1. **Inherit from base class** - Use `PlatformAdapter` base class
2. **Implement all required methods** - `transform_ir_to_platform()`, `validate_constraints()`
3. **Add logging** - Use `structlog` for debugging
4. **Handle errors gracefully** - Return empty configs, not exceptions
5. **Add tests** - Cover all service transformations
6. **Document limitations** - Note unsupported features