# FalkorDB Knowledge Graph Schema

This document describes the node and edge types used in the FalkorDB knowledge graph.

## Node Types

| Type | Description | Properties |
|------|-------------|-------------|
| `platform` | Cloud platform (AWS, Azure, GCP, SAP BTP, etc.) | name, description, services, region_support |
| `service` | Service/component within a platform | name, type, endpoints, metadata |
| `technology` | Technology stack (Kubernetes, Lambda, etc.) | name, version, category |
| `pattern` | Architectural pattern (microservices, serverless, etc.) | name, domain, confidence, implementations |
| `constraint` | Platform constraint (hard/soft) | name, severity, description |
| `use_case` | Pre-built use case | name, platform, description, steps |
| `reference_arch` | Reference architecture | name, description, components, platforms |
| `decision` | Architecture decision record (ADR) | title, status, context, decision, consequences |

## Edge Types

| Type | Description | Direction |
|------|-------------|------------|
| `requires` | Dependency requirement | node → required_node |
| `provides` | Capability offered | node → capability |
| `implements` | Implements a pattern | service → pattern |
| `conflicts` | Incompatible with | technology_a → technology_b |
| `alternative` | Alternative to | technology_a → technology_b |
| `depends_on` | Runtime dependency | service_a → service_b |
| `works_with` | Compatible with | technology → compatible_tech |
| `composed_of` | Contains sub-components | pattern → sub_pattern |

## Property Schema

### KnowledgeNode Properties

```python
{
    "id": "uuid",              # Auto-generated
    "name": "str",            # Required - unique name
    "type": "NodeType",       # Required - from enum
    "properties": {
        "description": "str",
        "documentation_url": "str",
        "category": "str",
        "region_support": ["us-east-1", ...],
        "tier": "free|paid|enterprise",
    },
    "version": "1.0.0",       # Semantic versioning
    "deprecated": false,
    "source": "str",          # Origin (e.g., "aws-docs", "manual")
    "confidence": 1.0,         # 0.0-1.0
    "created_at": "datetime",
}
```

### KnowledgeEdge Properties

```python
{
    "id": "uuid",
    "source_id": "uuid",
    "target_id": "uuid", 
    "type": "EdgeType",
    "weight": 1.0,            # 0.0-1.0
    "conditions": {
        "environment": "prod|staging|dev",
        "region": "str",
    },
    "confidence": 1.0,         # 0.0-1.0
    "created_at": "datetime",
}
```

## GraphQL Equivalent

```graphql
# Node: Platform
CREATE (p:Platform {
    id: "aws-001",
    name: "AWS",
    type: "platform",
    properties: {
        description: "Amazon Web Services",
        services: ["EC2", "S3", "Lambda", ...],
        region_support: ["us-east-1", "us-west-2", ...]
    },
    version: "1.0.0",
    deprecated: false,
    source: "aws-docs",
    confidence: 1.0
})

# Edge: Service implements Pattern
CREATE (s:Service {name: "Lambda"})-[r:IMPLEMENTS]->(p:Pattern {name: "serverless"})
```

## Example Queries

### Find all services for a platform
```python
# Find all AWS services
MATCH (p:Platform {name: "AWS"})-[:PROVIDES]->(s:Service)
RETURN s.name, s.type
```

### Find compatible patterns
```python
# Find patterns that work with Kubernetes
MATCH (t:Technology {name: "Kubernetes"})-[:WORKS_WITH]->(p:Pattern)
RETURN p.name, p.domain
```

### Validate constraint
```python
# Check if pattern violates constraints
MATCH (p:Pattern {name: "serverless"})
MATCH (c:Constraint)
WHERE (p)-[:CONFLICTS]->(c)
RETURN c.name, c.severity
```

## Migration Strategy

When schema changes:

1. **Add new property**: Backfill null values with defaults
2. **Rename type**: Create new, migrate data, delete old
3. **New edge type**: Add in code first, create edges incrementally

## Indexing

Recommended indexes:

```sql
# Node indexes
CREATE INDEX IF NOT EXISTS FOR (n:Platform) ON (n.name)
CREATE INDEX IF NOT EXISTS FOR (n:Service) ON (n.name) 
CREATE INDEX IF NOT EXISTS FOR (n:Pattern) ON (n.name)
CREATE INDEX IF NOT EXISTS FOR (n:Pattern) ON (n.domain)

# Edge indexes  
CREATE INDEX IF NOT EXISTS FOR ()-[r:IMPLEMENTS]->() ON (r.weight)
CREATE INDEX IF NOT EXISTS FOR ()-[r:DEPENDS_ON]->() ON (r.weight)
```
