import asyncio
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

    TENANCY_AVAILABLE = True
except ImportError:
    TENANCY_AVAILABLE = False


class EmbeddingCache:
    def __init__(self, max_size: int = 10000, ttl_seconds: float = 86400.0):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple[str, float]] = {}
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            if key in self._cache:
                embedding, expiry = self._cache[key]
                if time.time() < expiry:
                    self._hits += 1
                    return embedding
                else:
                    del self._cache[key]
            self._misses += 1
            return None

    async def set(self, key: str, embedding: str) -> None:
        async with self._lock:
            await self._evict_expired()
            if len(self._cache) >= self.max_size:
                oldest = min(self._cache.items(), key=lambda x: x[1][1])
                del self._cache[oldest[0]]
            self._cache[key] = (embedding, time.time() + self.ttl_seconds)

    async def _evict_expired(self) -> None:
        now = time.time()
        expired = [k for k, (_, exp) in self._cache.items() if now >= exp]
        for k in expired:
            del self._cache[k]

    def stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
        }


_cache: Optional[EmbeddingCache] = None


def get_embedding_cache() -> EmbeddingCache:
    global _cache
    if _cache is None:
        _cache = EmbeddingCache()
    return _cache


def with_retry(max_attempts: int = 3, min_wait: float = 1.0, max_wait: float = 10.0):
    if not TENANCY_AVAILABLE:

        def noop_decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any):
                return await func(*args, **kwargs)

            return wrapper

        return noop_decorator

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )


class RateLimiter:
    def __init__(self, requests_per_second: float = 10.0, burst: int = 20):
        self.rate = requests_per_second
        self.burst = burst
        self._tokens = float(burst)
        self._last = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        async with self._lock:
            now = time.time()
            elapsed = now - self._last
            self._last = now
            self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    async def wait_for_token(self) -> None:
        while not await self.acquire():
            await asyncio.sleep(0.1)


_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


class MetricsCollector:
    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._histograms: Dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def increment(self, name: str, value: int = 1) -> None:
        async with self._lock:
            self._counters[name] = self._counters.get(name, 0) + value

    async def record(self, name: str, value: float) -> None:
        async with self._lock:
            if name not in self._histograms:
                self._histograms[name] = []
            self._histograms[name].append(value)
            if len(self._histograms[name]) > 1000:
                self._histograms[name] = self._histograms[name][-500:]

    def get_stats(self) -> Dict[str, Any]:
        stats = {"counters": dict(self._counters), "histograms": {}}
        for name, values in self._histograms.items():
            if values:
                sorted_values = sorted(values)
                n = len(sorted_values)
                stats["histograms"][name] = {
                    "count": n,
                    "min": sorted_values[0],
                    "max": sorted_values[-1],
                    "p50": sorted_values[n // 2],
                    "p95": sorted_values[int(n * 0.95)],
                    "p99": sorted_values[int(n * 0.99)],
                }
        return stats


_metrics: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


class HealthChecker:
    _status: Dict[str, str] = {"embedding_cache": "healthy", "rate_limiter": "healthy"}

    @classmethod
    def set_status(cls, component: str, status: str) -> None:
        cls._status[component] = status

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        all_healthy = all(s == "healthy" for s in cls._status.values())
        return {
            "status": "healthy" if all_healthy else "degraded",
            "components": dict(cls._status),
        }


def get_health_checker() -> HealthChecker:
    return HealthChecker()


class IngestionError(Exception):
    def __init__(self, message: str, component: str = "unknown", details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.component = component
        self.details = details or {}


class HandlerError(IngestionError):
    pass


class JobError(IngestionError):
    pass


class RateLimitError(IngestionError):
    pass


def format_error(error: Exception) -> Dict[str, Any]:
    if isinstance(error, IngestionError):
        return {
            "error": error.message,
            "component": error.component,
            "details": error.details,
        }
    return {
        "error": str(type(error).__name__),
        "message": str(error),
        "component": "unknown",
    }


__all__ = [
    "EmbeddingCache",
    "get_embedding_cache",
    "with_retry",
    "RateLimiter",
    "get_rate_limiter",
    "MetricsCollector",
    "get_metrics_collector",
    "HealthChecker",
    "get_health_checker",
    "IngestionError",
    "HandlerError",
    "JobError",
    "RateLimitError",
    "format_error",
]
