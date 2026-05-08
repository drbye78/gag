# FalkorDB Client

FalkorDB client for knowledge graph operations.

## Overview

The `FalkorDBClient` provides a Python interface to FalkorDB (graph database). It handles connection pooling, parameterized queries, and validation.

## Quick Usage

```python
from graph.client import FalkorDBClient

client = FalkorDBClient(host="localhost", port=7379)

# Query
result = await client.query("MATCH (n:Service) RETURN n.name LIMIT 10")

# Execute
await client.execute("CREATE (n:Service {name: $name})", {"name": "AuthService"})
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FALKORDB_HOST` | `localhost` | FalkorDB host |
| `FALKORDB_PORT` | `7379` | FalkorDB port |
| `FALKORDB_USER` | | Username |
| `FALKORDB_PASS` | | Password |

## API

### Query

```python
result = await client.query(
    "MATCH (n:Service) RETURN n.name, n.type LIMIT $limit",
    {"limit": 10}
)
```

### Execute

```python
await client.execute(
    "CREATE (n:Service {name: $name, type: $type})",
    {"name": "AuthService", "type": "AWS"}
)
```

### Node Types

Allowed node types:
- Component, Service, API, Endpoint, Database
- Function, Class, Module, File, Entity
- Incident, Requirement, Architecture, Community

### Edge Types

Allowed edge types:
- CALLS, DEFINES, IMPORTS, RETURNS, CONTAINS
- INHERITS, IMPLEMENTS, DEPENDS_ON, RELATED_TO
- DOCUMENTED_BY, TRIGGERS, AFFECTS, IN_COMMUNITY

## Validation

The client validates node/edge types and parameters:

```python
from graph.client import FalkorDBClient

client = FalkorDBClient()

# Validated node type
result = client.query_node("Service", limit=10)

# Validated edge traversal
result = client.query_edge(
    from_node="Service",
    edge_type="DEPENDS_ON",
    to_node="Database",
    depth=2,
)
```

## Connection Pooling

Uses HTTP connection pooling:

```python
from core.pool import get_http_pool

pool = get_http_pool()
client = FalkorDBClient(host="localhost", port=7379, pool=pool)
```

## Errors

| Error | Description |
|-------|------------|
| `StorageError` | Query execution failed |
| `ServiceUnavailableError` | FalkorDB not available |
| `ValidationError` | Invalid node/edge type |

## Cypher Builder

Use `cypher_builder` for safe query construction:

```python
from graph.cypher_builder import CypherBuilder

query = CypherBuilder.match("Service").where(name="Auth").build()
```