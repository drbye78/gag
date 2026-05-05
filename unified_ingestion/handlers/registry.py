from typing import Any, Callable, Dict, Optional, Type, Union

from unified_ingestion.handlers.base import Handler


class HandlerRegistry:
    def __init__(self):
        self._handlers: Dict[str, Any] = {}

    def register(self, artifact_type: str, handler: Any) -> None:
        self._handlers[artifact_type] = handler

    def get(self, artifact_type: str) -> Optional[Any]:
        return self._handlers.get(artifact_type)

    def list_types(self) -> list:
        return list(self._handlers.keys())


_registry: Optional[HandlerRegistry] = None


def get_handler_registry() -> HandlerRegistry:
    global _registry
    if _registry is None:
        _registry = HandlerRegistry()
    return _registry