# Platform Adapters & Knowledge Layer Architecture

The system provides universal domain intelligence through pluggable platform adapters and a knowledge substrate. This document covers the adapter architecture, knowledge layer, and cross-platform reasoning.

## Architecture Overview

```
Query → Knowledge Resolver → Platform Adapter → Platform-specific Output
                      ↓
            Knowledge Graph (platforms, services, patterns)
```

## Platform Adapters

### Adapters (`core/adapters/`)

| Adapter | Platform ID | Services |
|---------|------------|----------|
| `SAPBTPAdapter` | `sap` | XSUAA, HANA, Kyma, CAP |
| `VMwareTanzuAdapter` | `tanzu` | Kubernetes, Spring, TAS |
| `PowerPlatformAdapter` | `powerplatform` | Power Apps, Dataverse |
| `AWSAdapter` | `aws` | Lambda, S3, DynamoDB, EKS |
| `AzureAdapter` | `azure` | Functions, Cosmos DB, AKS |
| `GCPAdapter` | `gcp` | Cloud Functions, Firestore, GKE |

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

### Adapter Registry

```python
registry = get_adapter_registry()
adapter = registry.get("aws")  # Get AWS adapter
adapter = registry.auto_detect(features)  # Auto-detect from IR features
platforms = registry.list_platforms()  # List all registered platforms
```

### Adapter Example: AWS Serverless

```python
adapter = registry.get("aws")

# Input features from query analysis
features = IRFeature(
    has_serverless=True,
    has_event_driven=True,
    has_async=True
)

# Transform to platform-specific output
output = adapter.transform_ir_to_platform(AdapterInput(
    ir_features=features,
    pattern_matches=[...],
    constraint_violations=[...],
    platform_context=...
))

# Output includes Lambda config, IAM role, CloudFormation template
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