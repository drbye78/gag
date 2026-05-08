# Prometheus Metrics

Built-in Prometheus metrics for observability. Exposes metrics at `/metrics` endpoint.

## Overview

The system tracks request latency, retrieval operations, LLM calls, and token usage via Prometheus-compatible metrics.

## Metrics Endpoint

```
GET /metrics
```

Returns metrics in Prometheus text format (when `ENABLE_METRICS=true`).

## Available Metrics

### Request Metrics

| Metric | Type | Description |
|--------|------|------------|
| `request_latency_seconds` | Histogram | Request latency in seconds |
| `requests_total` | Counter | Total requests by method/path/status |
| `errors_total` | Counter | Total errors by method/path/error |
| `active_requests` | Gauge | Active requests |

**Latency Buckets**: 5ms, 10ms, 25ms, 50ms, 75ms, 100ms, 250ms, 500ms, 750ms, 1s, 2.5s, 5s, 7.5s, 10s

### Retrieval Metrics

| Metric | Type | Description |
|--------|------|------------|
| `retrieval_latency_seconds` | Histogram | Retrieval latency by source |
| `retrieval_count_total` | Counter | Total retrievals by source |

**Sources**: docs, code, graph, telemetry, tickets, knowledge

### LLM Metrics

| Metric | Type | Description |
|--------|------|------------|
| `llm_calls_total` | Counter | LLM calls by model/status |
| `llm_latency_seconds` | Histogram | LLM call latency by model |
| `tokens_used_total` | Counter | Tokens used by model/type |

**Token Types**: prompt, completion

**Latency Buckets**: 100ms, 250ms, 500ms, 750ms, 1s, 2.5s, 5s, 7.5s, 10s, 15s, 30s, 60s

## Usage in Code

```python
from core.prometheus_metrics import (
    record_request,
    record_error,
    record_retrieval,
    record_llm,
    increment_active_requests,
)

# Track request
record_request("POST", "/query", 200, 0.25)

# Track error
record_error("POST", "/query", "timeout")

# Track retrieval
record_retrieval("docs", 0.15, count=1)

# Track LLM call
record_llm("qwen-max", 2.5, 1500, "success")  # model, latency, tokens, status

# Track active requests
increment_active_requests(1)  # increment
increment_active_requests(-1)  # decrement
```

## Integration

### Prometheus Scrape Config

```yaml
scrape_configs:
  - job_name: 'eis'
    static_configs:
      - targets: ['localhost:8000']
```

### Grafana Dashboard

Key queries:

```promql
# Request latency p99
histogram_quantile(0.99, rate(request_latency_seconds_bucket[5m]))

# Error rate
rate(errors_total[5m]) / rate(requests_total[5m])

# Tokens per minute
rate(tokens_used_total[1m])
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_METRICS` | `true` | Enable metrics endpoint |
| `PROMETHEUS_URL` | `http://localhost:9090` | Prometheus URL |

## Metrics JSON Endpoint

For JSON format:

```
GET /metrics
Accept: application/json
```

Returns:

```json
{
  "request_latency_seconds": {...},
  "requests_total": {...},
  "tokens_used_total": {...}
}
```