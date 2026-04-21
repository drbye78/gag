# Deployment Guide

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.12+ (for local development)

## Quick Start

```bash
# Clone and navigate
cd /home/roger/src/gag

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEBUG` | No | `false` | Enable debug logging |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `API_PORT` | No | `8000` | API port |
| `QDRANT_HOST` | No | `qdrant` | Qdrant service host |
| `FALKORDB_HOST` | No | `falkordb` | FalkorDB service host |
| `REDIS_URL` | No | `redis://redis:6379` | Redis URL |
| `LLM_PROVIDER` | No | `openrouter` | LLM provider |
| `LLM_MODEL` | No | `qwen-max` | Model name |
| `LLM_API_KEY` | Yes | - | API key for LLM |
| `JWT_SECRET` | No | random | JWT signing secret |
| `RATE_LIMIT_REQUESTS` | No | `100` | Requests per window |
| `RATE_LIMIT_WINDOW` | No | `60` | Window in seconds |
| `CORS_ORIGINS` | No | `*` | Allowed origins |

### SAP BTP Integration (Optional)

```bash
# Jira
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token

# GitHub
GITHUB_OWNER=your-org
GITHUB_REPO=your-repo
GITHUB_TOKEN=your-token

# Prometheus
PROMETHEUS_URL=http://prometheus:9090
ELASTIC_URL=http://elasticsearch:9200
```

## Docker Services

### API Service

```yaml
api:
    image: engineering-intelligence-api
    ports:
      - "8000:8000"
    environment:
      - QDRANT_HOST=qdrant
      - FALKORDB_HOST=falkordb
      - REDIS_URL=redis://redis:6379
    depends_on:
      - qdrant
      - falkordb
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

### Qdrant (Vector DB)

```yaml
qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"  # gRPC
    volumes:
      - qdrant-storage:/qdrant/storage
    restart: unless-stopped
```

### FalkorDB (Graph DB)

```yaml
falkordb:
    image: falkordb/falkordb:latest
    ports:
      - "7379:7379"
    volumes:
      - falkordb-data:/data
    restart: unless-stopped
```

### Redis (Cache)

```yaml
redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped
```

### Redis
Redis is used for caching (when available). The docker-compose.yml includes a Redis 7 Alpine
service with append-only file (AOF) persistence on port 6379.

## Deployment Modes

### Development

```bash
docker-compose up -d
# Uses InMemory backends where available
# Debug logging enabled
```

### Production

```yaml
# docker-compose.prod.yml
services:
  api:
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 512M
    environment:
      - DEBUG=false
      - LOG_LEVEL=WARNING
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Kubernetes

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: engineering-intelligence
spec:
  replicas: 3
  selector:
    matchLabels:
      app: engineering-intelligence
  template:
    metadata:
      labels:
        app: engineering-intelligence
    spec:
      containers:
      - name: api
        image: engineering-intelligence:latest
        ports:
        - containerPort: 8000
        resources:
          limits:
            cpu: "2"
            memory: 4Gi
        env:
        - name: QDRANT_HOST
          value: "qdrant-service"
        - name: LLM_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-secrets
              key: api-key
---
apiVersion: v1
kind: Service
metadata:
  name: engineering-intelligence
spec:
  selector:
    app: engineering-intelligence
  ports:
  - port: 80
    targetPort: 8000
```

## Health Checks

### API Health

```bash
curl http://localhost:8000/health
# {"status": "healthy", "version": "3.2.0"}
```

### Dependency Health

```bash
# Via internal endpoint (not exposed)
# Returns status of Qdrant, FalkorDB, Redis
```

## Monitoring

### Prometheus Metrics

Metrics available at `/metrics` (when `ENABLE_METRICS=true`):

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="POST",path="/query",status="200"} 1234

# HELP agent_executions Total agent executions  
# TYPE agent_executions counter
agent_executions{source="docs",status="success"} 567
```

### Logging

```bash
# View logs
docker-compose logs -f api

# Filter by level
docker-compose logs -f | grep ERROR
```

## Scaling

### Horizontal Scaling

```bash
# Scale API service
docker-compose up -d --scale api=3
```

### Database Scaling

- Qdrant: Use clustering for high availability
- FalkorDB: Use clustering for high availability  
- Redis: Use Redis Cluster for high availability

## Security

### TLS/SSL

```yaml
# docker-compose.tls.yml
services:
  api:
    ports:
      - "443:8000"
    volumes:
      - ./certs:/certs:ro
    environment:
      - TLS_CERT=/certs/server.crt
      - TLS_KEY=/certs/server.key
```

### Authentication

```bash
# Generate JWT secret
openssl rand -base64 32

# Set environment
export JWT_SECRET=your-generated-secret
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs api

# Check ports
netstat -tulpn | grep 8000

# Check resources
docker stats
```

### Out of Memory

```yaml
# Increase memory limit
services:
  api:
    deploy:
      resources:
        limits:
          memory: 4G
```

### Slow Performance

1. Check Qdrant index status
2. Enable query caching
3. Increase `MAX_WORKERS`
4. Scale horizontally

## Backup & Recovery

### Qdrant

```bash
# Backup
docker exec qdrant qdrantctl collections save my-collection

# Restore
docker exec qdrant qdrantctl collections restore my-collection
```

### FalkorDB

```bash
# Backup
docker cp falkordb:/data ./backup

# Restore
docker cp ./backup falkordb:/data
```

## Update & Migration

```bash
# Pull latest
docker-compose pull

# Recreate containers
docker-compose up -d --force-recreate

# Run migrations
docker-compose exec api python -m migrate
```