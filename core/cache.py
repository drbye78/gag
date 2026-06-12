"""Caching layer with in-memory TTL cache and optional Redis backend."""

import asyncio
import time
from typing import Any, Dict, Optional


class _CacheEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.expires_at = time.time() + ttl

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class InMemoryCache:
    def __init__(self):
        import threading

        self._store: Dict[str, _CacheEntry] = {}
        self._lock = threading.RLock()
        self._async_lock: Optional[asyncio.Lock] = None

    def _get_async_lock(self) -> asyncio.Lock:
        if self._async_lock is None:
            import asyncio

            self._async_lock = asyncio.Lock()
        return self._async_lock

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.is_expired:
                del self._store[key]
                return None
            return entry.value

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        with self._lock:
            self._store[key] = _CacheEntry(value, ttl)
            return True

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def exists(self, key: str) -> bool:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False
            if entry.is_expired:
                del self._store[key]
                return False
            return True

    def clear_pattern(self, pattern: str) -> int:
        import fnmatch

        with self._lock:
            deleted = 0
            for key in list(self._store.keys()):
                if fnmatch.fnmatch(key, pattern):
                    del self._store[key]
                    deleted += 1
            return deleted

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        return len(self._store)


class CacheWrapper:
    """Convenience wrapper with get-or-set semantics."""

    def __init__(
        self,
        cache: Optional[InMemoryCache] = None,
        default_ttl: int = 300,
    ):
        self.cache = cache or InMemoryCache()
        self.default_ttl = default_ttl

    def get_or_set(self, key: str, fn, ttl: Optional[int] = None) -> Any:
        """Synchronous get-or-set: calls fn() if key is missing.

        The entire check-then-set is wrapped in the cache's lock to
        prevent a race condition where multiple threads could both
        observe a cache miss and redundantly compute fn().

        NOTE: ``fn`` must be a plain synchronous callable.  If you need
        to call an async function, use ``get_or_set_async`` instead —
        passing an awaitable here will store the coroutine object rather
        than its result.
        """
        with self.cache._lock:
            cached = self.cache.get(key)
            if cached is not None:
                return cached

            result = fn()
            self.cache.set(key, result, ttl or self.default_ttl)
            return result

    async def get_or_set_async(self, key: str, fn, ttl: Optional[int] = None) -> Any:
        """Async get-or-set: awaits fn() if key is missing."""
        lock = self.cache._get_async_lock()
        async with lock:
            cached = self.cache.get(key)
            if cached is not None:
                return cached

            result = await fn()
            self.cache.set(key, result, ttl or self.default_ttl)
            return result

    def invalidate(self, key: str) -> bool:
        return self.cache.delete(key)


# ---------------------------------------------------------------------------
# Singleton accessors
# ---------------------------------------------------------------------------

_cache: Optional[InMemoryCache] = None


def get_cache() -> InMemoryCache:
    global _cache
    if _cache is None:
        _cache = InMemoryCache()
    return _cache


def get_cache_wrapper(ttl: Optional[int] = None) -> CacheWrapper:
    """Return a CacheWrapper with the given default TTL."""
    default = ttl if ttl is not None else 300
    return CacheWrapper(get_cache(), default_ttl=default)
