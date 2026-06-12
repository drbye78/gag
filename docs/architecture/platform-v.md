# Platform V - SberTech PaaS Platform

## Overview

Platform V is SberTech's comprehensive Russian PaaS platform for enterprise application development and deployment. With 70+ products, it's designed for high-scale, FSTEC-certified workloads.

**Key Facts:**
- **Vendor**: SberTech (Sberbank subsidiary)
- **Launch**: November 2020, public since 2021
- **Certification**: FSTEC (Russian security certification)
- **Fault Tolerance**: 99.99%
- **Scale**: ~100M customers at Sberbank

## Services by Category

### Databases & Data

| Service | Description | Capabilities |
|---------|-------------|-------------|
| **Platform V Pangolin** | PostgreSQL-compatible RDBMS | High availability, transparent encryption, audit |
| **Platform V Grid Center** | Database cluster administration | Web UI for cluster management |
| **Platform V Kintsugi** | Database maintenance tool | Technical support, tuning |
| **Platform V Corax** | Message broker + distributed DBMS | Kafka-compatible, streaming |
| **Platform V DataGrid** | In-memory computing (Apache Ignite) | Real-time analytics, distributed computing |

### Integration

| Service | Description | Capabilities |
|---------|-------------|-------------|
| **Platform V Synapse** | Enterprise integration platform | ESB replacement |
| **Platform V Synapse File Exchange** | Secure file sharing | Cloud file management |
| **Platform V Synapse Event Processing** | Stream event routing | Event streaming |
| **Platform V Synapse AI** | Microservice traffic AI | ML-based optimization |
| **Platform V Synapse API-management** | API publishing | Gateway, rate limiting |
| **Platform V Service Mesh** | Microservice integration | Discovery, load balancing |

### Compute

| Service | Description | Capabilities |
|---------|-------------|-------------|
| **Platform V Functions** | FaaS | Serverless, event-driven |
| **Platform V Batch** | Job scheduling | Batch processing |

### Development

| Service | Description | Capabilities |
|---------|-------------|-------------|
| **Platform V Works** | DevOps tool suite | CI/CD, task management |
| **Platform V Studio** | Low-code development | Visual builder |
| **GigaIDE** | AI-enhanced IDE | Code generation |
| **GigaCode** | AI developer assistant | Code completion |

### Data & Analytics

| Service | Description | Capabilities |
|---------|-------------|-------------|
| **Platform V DataSpace** | Data abstraction | Federation |
| **Platform V DataTools** | Log management | Archiving |

### Orchestration

| Service | Description | Capabilities |
|---------|-------------|-------------|
| **Platform V Flow** | BPM | Process orchestration |

### Operations

| Service | Description | Capabilities |
|---------|-------------|-------------|
| **Platform V Monitor** | Metrics | Monitoring, alerting |
| **Platform V Audit** | Audit | Compliance logging |
| **Platform V Configuration** | Config management | Centralized config |

### Security

| Service | Description | Capabilities |
|---------|-------------|-------------|
| **Platform V IAM** | Identity & access | OAuth2/OIDC, RBAC |
| **Platform V One Time Tokens** | Token management | Service authentication |

### ML/AI

| Service | Description | Capabilities |
|---------|-------------|-------------|
| **Model Execution Framework** | Cloud ML | Model serving |

### Operating System

| Service | Description | Capabilities |
|---------|-------------|-------------|
| **Platform V SberLinux OS Server** | Server OS | FSTEC-certified |

## Architecture Patterns

- Microservices
- Serverless (FaaS)
- Container-native (Kubernetes)
- Low-code
- Event-driven
- Service mesh
- Integration bus

## Constraints

### Hard Constraints
- DBMS required → Use Pangolin or Corax
- Production → Use SberLinux OS Server
- Authentication → Use Platform V IAM

### Soft Constraints
- Integration → Use Synapse
- Event-driven → Use Functions
- High-performance → Use DataGrid

## Use Cases

1. **Application Modernization** - Migrate legacy apps to microservices
2. **Import Substitution** - Replace Western software
3. **Event Streaming** - Build event-driven with Corax
4. **Real-time Analytics** - In-memory with DataGrid
5. **Serverless API** - Build APIs with Functions
6. **DevOps Automation** - CI/CD with Works
7. **Secure Access** - Identity with IAM

## Migration from Other Platforms

### From AWS
| AWS Service | Platform V Alternative |
|-------------|---------------------|
| RDS | Pangolin |
| SQS/SNS | Corax |
| Lambda | Functions |
| API Gateway | Synapse API-management |
| IAM | IAM |
| CloudWatch | Monitor |

### From Azure
| Azure Service | Platform V Alternative |
|-------------|---------------------|
| Azure SQL | Pangolin |
| Service Bus | Corax |
| Azure Functions | Functions |
| API Management | Synapse API-management |

### From VMware Tanzu
| Tanzu Service | Platform V Alternative |
|--------------|------------------------|
| PostgreSQL | Pangolin |
| Spring Cloud | Functions + Service Mesh |
| Tanzu Application Service | K8s + Synapse |

## Configuration Examples

### Pangolin (PostgreSQL)

```yaml
DATABASE_CONFIG:
  host: pangolin.platformv.internal
  port: 5432
  database: app_db
  ssl_mode: require
  encryption: transparent
```

### Synapse API

```yaml
SYNAPSE_CONFIG:
  api_gateway:
    host: synapse.platformv.internal
    port: 8080
  service_mesh:
    enabled: true
    circuit_breaker: true
```

### Platform V Functions

```python
from platformv.functions import handler

@handler(event_type="http")
def process_request(event):
    return {"status": 200, "body": {"message": "Hello!"}}
```

## Certification

Platform V components are registered in the Russian Software Register and certified by FSTEC for use in government and critical infrastructure.

## References

- Official: https://platformv.sbertech.ru
- Works: https://works.sbertech.ru
- Documentation: Platform V documentation portal