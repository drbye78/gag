# Smoke Tests

Run these after deployment to verify the system is operational.

## Health Check

```bash
curl http://localhost:8000/health
# Expected: {"status": "ok", "version": "4.2.0"}
```

## Metrics

```bash
curl http://localhost:8000/metrics
# Expected: 200 OK with metrics JSON
```

## Authentication

```bash
# Login and get token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "..."}'
# Expected: JWT token
```

## Query Endpoint

```bash
TOKEN=$(cat token.txt)
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
# Expected: {"answer": "...", "sources": [...]}
```

## Circuit Breaker Test

```bash
# Trigger failures until circuit opens
# Check circuit state
curl http://localhost:8000/health
# Circuit should show "open" after failures
```

## Deployment Verification

Check all services:
```bash
docker-compose ps
# All services should be "Up"
```

Check logs:
```bash
docker-compose logs --tail=50
# No ERROR logs
```