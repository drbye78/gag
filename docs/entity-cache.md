# Entity Graph Cache

The entity graph cache accelerates entity-aware reasoning by caching relationship data from FalkorDB, avoiding repeated graph database queries.

## Architecture

```
Query → Extract Entities → Check Cache → [Hit: use cached] / [Miss: query FalkorDB → cache → use]
```

## Cache Properties

| Property | Value |
|---|---|
| Type | LRU (Least Recently Used) |
| Capacity | 500 entries |
| TTL | 1 hour (3600 seconds) |
| Eviction | Oldest entry when full |

## How It Works

1. **Entity extraction**: When a query arrives, capitalized words are extracted as potential entity names (e.g., "AuthService", "APIGateway").

2. **Cache lookup**: For each entity, the cache is checked. On a **hit**, the cached relations and graph paths are used directly.

3. **Cache miss**: On a miss, the graph retriever queries FalkorDB for the entity's relationships, builds an `EntityGraphCacheEntry`, and stores it.

4. **Reasoning**: The cached entity graph is passed to `EntityAwareReasoningEngine.reason()` which uses it to build context-aware reasoning steps.

## API Endpoints

### Get Cache Statistics
```
GET /entity/cache/stats
```

Returns:
```json
{
  "size": 42,
  "capacity": 500,
  "hit_rate": 0.73,
  "hits": 156,
  "misses": 58,
  "utilization_pct": 8.4,
  "oldest_entry": {
    "entity_name": "AuthService",
    "age_seconds": 3600,
    "hit_count": 12
  }
}
```

### Invalidate Cache
```
POST /entity/cache/invalidate
{"entity_name": "AuthService"}
```

Or `{}` to clear the entire cache.

## Monitoring

Monitor these metrics:
- **hit_rate**: Target > 0.6. Low hit rate may indicate high entity churn or too-short TTL.
- **utilization_pct**: Target < 80%. High utilization means cache is near capacity and evicting frequently.
- **size**: Current entry count. Should stabilize after warm-up period.

## Tuning

In `retrieval/entity_cache.py`:
```python
EntityGraphCache(capacity=500, default_ttl=3600)
```

- Increase `capacity` for systems with many distinct entities
- Decrease `ttl` if entity relationships change frequently
- Monitor `oldest_entry.age_seconds` to verify TTL is working

## Integration Points

- `EnhancedHybridRetriever.search_with_enhanced_reasoning()` — checks cache before querying graph DB
- `EntitySearchTool` — uses cached entity data for faster search
- `EntityAwareReasoningEngine` — receives cached entity graph for context building
