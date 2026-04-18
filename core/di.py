"""Dependency injection container with lifecycle management."""

import logging
from typing import Any, Dict, Optional, Type, TypeVar
from contextlib import asynccontextmanager

from core.config import Settings, get_settings
from core.pool import HttpPool, get_http_pool
from core.errors import ServiceUnavailableError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AppContainer:
    """Central DI container with singleton and scoped lifecycles."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Any] = {}
        self._pools: Dict[str, Any] = {}
        self._initialized = False

    def register_singleton(self, cls: Type[T], instance: T) -> None:
        self._singletons[cls] = instance

    def register_factory(self, cls: Type[T], factory: Any) -> None:
        self._factories[cls] = factory

    def singleton(self, cls: Type[T]) -> Optional[T]:
        return self._singletons.get(cls)

    def scoped(self, cls: Type[T]) -> T:
        if cls in self._factories:
            return self._factories[cls](self)
        raise KeyError(f"No factory registered for {cls}")

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