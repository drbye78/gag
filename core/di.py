"""Dependency injection container with lifecycle management."""

import logging
import threading
from typing import Any, Callable, Dict, Optional, Type, TypeVar
from contextlib import asynccontextmanager

from core.config import Settings, get_settings
from core.pool import HttpPool, get_http_pool
from core.errors import ServiceUnavailableError

logger = logging.getLogger(__name__)


class AppContainer:
    """Central DI container with singleton and scoped lifecycles.
    
    Thread-safe implementation using locks for singleton registration/resolution.
    """

    _instance: Optional["AppContainer"] = None
    _lock = threading.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> "AppContainer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized_internal = False
        return cls._instance

    def __init__(self, settings: Optional[Settings] = None):
        if self._initialized_internal:
            return
        self.settings = settings or get_settings()
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[..., Any]] = {}
        self._pools: Dict[str, Any] = {}
        self._singletons_lock = threading.Lock()
        self._factories_lock = threading.Lock()
        self._initialized = False
        self._initialized_internal = True

    def register_singleton(self, cls: Type, instance: Any) -> None:
        with self._singletons_lock:
            self._singletons[cls] = instance

    def register_factory(self, cls: Type, factory: Callable[..., Any]) -> None:
        with self._factories_lock:
            self._factories[cls] = factory

    def singleton(self, cls: Type) -> Optional[Any]:
        with self._singletons_lock:
            return self._singletons.get(cls)

    def get_or_create(self, cls: Type) -> Any:
        """Get existing singleton or create via factory."""
        with self._singletons_lock:
            if cls in self._singletons:
                return self._singletons[cls]
        
        with self._factories_lock:
            if cls in self._factories:
                instance = self._factories[cls]()
                with self._singletons_lock:
                    self._singletons[cls] = instance
                return instance
        
        raise KeyError(f"No singleton or factory registered for {cls}")

    def register_override(self, cls: Type, instance: Any) -> None:
        """Register override for testing - thread-safe."""
        with self._singletons_lock:
            self._singletons[cls] = instance

    def clear_overrides(self) -> None:
        """Clear all singleton overrides - for testing."""
        with self._singletons_lock:
            self._singletons.clear()
        with self._factories_lock:
            self._factories.clear()

    async def init(self) -> None:
        """Initialize all pooled resources."""
        if self._initialized:
            return

        settings = self.settings
        self._pools["http"] = HttpPool(
            max_connections=settings.max_workers * 4,
            max_keepalive_connections=settings.max_workers * 2,
            keepalive_expiry=30.0,
        )
        await self._pools["http"].start()

        self._initialized = True
        logger.info("AppContainer initialized")

    async def close(self) -> None:
        """Clean up all resources."""
        for pool in self._pools.values():
            await pool.stop()
        self._pools.clear()
        self._singletons.clear()
        self._initialized = False
        logger.info("AppContainer closed")

    @asynccontextmanager
    async def lifespan(self):
        """Async context manager for container lifecycle."""
        await self.init()
        try:
            yield self
        finally:
            await self.close()


_container: Optional[AppContainer] = None


def get_container() -> AppContainer:
    global _container
    if _container is None:
        _container = AppContainer()
    return _container


async def init_container() -> AppContainer:
    """Initialize container and all dependencies."""
    container = get_container()
    await container.init()
    return container


async def close_container() -> None:
    """Close container and release resources."""
    global _container
    if _container is not None:
        await _container.close()
        _container = None