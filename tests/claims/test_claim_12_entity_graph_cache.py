"""
README claim: "Entity graph cache: LRU eviction (500 entries, 1h TTL) with REST API for monitoring"
Source: README.md line 83
"""
import pytest
import asyncio


@pytest.mark.claim
@pytest.mark.asyncio
async def test_entity_cache_lru_eviction():
    from retrieval.entity_cache import EntityGraphCache, EntityGraphCacheEntry
    cache = EntityGraphCache(capacity=10, default_ttl=3600)
    for i in range(11):
        entry = EntityGraphCacheEntry(entity_name=f"entity_{i}", relations=[])
        await cache.put(f"entity_{i}", entry)
    # entity_0 should be evicted (oldest)
    assert await cache.get("entity_0") is None, "LRU eviction not working -- oldest entry not evicted"
    assert await cache.get("entity_10") is not None, "Newest entry should still be in cache"


@pytest.mark.claim
@pytest.mark.asyncio
async def test_entity_cache_ttl_expiry():
    from retrieval.entity_cache import EntityGraphCache, EntityGraphCacheEntry
    cache = EntityGraphCache(capacity=10, default_ttl=0)
    # Create entry with TTL of 0 (expires immediately)
    entry = EntityGraphCacheEntry(entity_name="entity", relations=[], ttl=0)
    await cache.put("entity", entry)
    await asyncio.sleep(0.1)
    # Entry should be expired
    result = await cache.get("entity")
    assert result is None, f"TTL expiry not working -- entry should have expired, got {result}"


@pytest.mark.claim
def test_entity_cache_stats_endpoint_exists():
    from api.main import app
    routes = []
    for r in app.routes:
        if hasattr(r, 'path'):
            routes.append(r.path)
        if hasattr(r, 'original_router') and hasattr(r.original_router, 'routes'):
            routes.extend(sr.path for sr in r.original_router.routes)
    assert "/entity/cache/stats" in routes, "/entity/cache/stats endpoint not found"


@pytest.mark.claim
def test_entity_cache_invalidate_endpoint_exists():
    from api.main import app
    routes = []
    for r in app.routes:
        if hasattr(r, 'path'):
            routes.append(r.path)
        if hasattr(r, 'original_router') and hasattr(r.original_router, 'routes'):
            routes.extend(sr.path for sr in r.original_router.routes)
    assert "/entity/cache/invalidate" in routes, "/entity/cache/invalidate endpoint not found"
