"""
Entity Graph Cache — production-grade cache for entity relationship data.

Provides TTL-based caching of entity graphs retrieved from FalkorDB,
with LRU eviction, hit-rate tracking, and cross-retriever integration.
"""

import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EntityGraphCacheEntry:
    """A cached entity with its relationships and traversal paths."""

    entity_name: str
    relations: List[Dict[str, Any]] = field(default_factory=list)
    graph_paths: Dict[str, List[str]] = field(default_factory=dict)
    related_entities: List[str] = field(default_factory=list)
    source_results: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    hit_count: int = 0
    ttl: int = 3600  # 1 hour default

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl

    def touch(self) -> None:
        self.last_accessed = time.time()
        self.hit_count += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_name": self.entity_name,
            "relations": self.relations,
            "graph_paths": self.graph_paths,
            "related_entities": self.related_entities,
            "source_results": self.source_results,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "hit_count": self.hit_count,
            "ttl": self.ttl,
            "is_expired": self.is_expired,
        }


class EntityGraphCache:
    """TTL-based LRU cache for entity graph data.

    Thread-safe via OrderedDict (single-threaded async context assumed).
    Capacity defaults to 500 entries.
    """

    def __init__(self, capacity: int = 500, default_ttl: int = 3600):
        self.capacity = capacity
        self.default_ttl = default_ttl
        self._store: OrderedDict[str, EntityGraphCacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, entity_name: str) -> Optional[EntityGraphCacheEntry]:
        """Retrieve a cached entry if present and not expired."""
        entry = self._store.get(entity_name)
        if entry is None:
            self._misses += 1
            return None

        if entry.is_expired:
            del self._store[entity_name]
            self._misses += 1
            return None

        # LRU: move to end
        self._store.move_to_end(entity_name)
        entry.touch()
        self._hits += 1
        return entry

    def put(
        self,
        entity_name: str,
        entry: EntityGraphCacheEntry,
    ) -> None:
        """Insert or update a cache entry. Evicts oldest on capacity."""
        if entity_name in self._store:
            self._store.move_to_end(entity_name)
            self._store[entity_name] = entry
        else:
            if len(self._store) >= self.capacity:
                # Evict oldest (FIFO end of OrderedDict)
                self._store.popitem(last=False)
            self._store[entity_name] = entry

    def invalidate(self, entity_name: str) -> bool:
        """Remove a specific entity from the cache."""
        if entity_name in self._store:
            del self._store[entity_name]
            return True
        return False

    def invalidate_by_prefix(self, prefix: str) -> int:
        """Remove all entities matching a prefix."""
        to_remove = [k for k in self._store if k.startswith(prefix)]
        for k in to_remove:
            del self._store[k]
        return len(to_remove)

    def clear(self) -> None:
        """Remove all cached entries."""
        self._store.clear()
        self._hits = 0
        self._misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Return cache statistics for monitoring."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        oldest_entry = None
        if self._store:
            oldest_key, oldest_val = next(iter(self._store.items()))
            oldest_entry = {
                "entity_name": oldest_key,
                "age_seconds": round(time.time() - oldest_val.created_at, 1),
                "hit_count": oldest_val.hit_count,
            }

        return {
            "size": len(self._store),
            "capacity": self.capacity,
            "hit_rate": round(hit_rate, 4),
            "hits": self._hits,
            "misses": self._misses,
            "oldest_entry": oldest_entry,
            "utilization_pct": round(len(self._store) / self.capacity * 100, 1),
        }

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_cache: Optional[EntityGraphCache] = None


def get_entity_graph_cache() -> EntityGraphCache:
    global _cache
    if _cache is None:
        _cache = EntityGraphCache()
    return _cache
