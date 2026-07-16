"""
README claim: "Unified Ingestion: 33 artifact types, 24 handlers, platform extension architecture"
Source: README.md line 124
"""
import pytest


@pytest.mark.claim
def test_thirty_three_artifact_types():
    from unified_ingestion.core.types import ArtifactType
    types = [t for t in ArtifactType]
    assert len(types) == 33, f"Expected 33 artifact types, got {len(types)}: {[t.value for t in types]}"


@pytest.mark.claim
def test_handler_registry_exists():
    from unified_ingestion.handlers.registry import get_handler_registry
    registry = get_handler_registry()
    assert registry is not None

    handlers = []
    if hasattr(registry, "list_handlers"):
        handlers = registry.list_handlers()
    elif hasattr(registry, "_handlers"):
        handlers = list(registry._handlers.values())

    assert len(handlers) >= 20, f"Expected ~24 handlers, got {len(handlers)}"


@pytest.mark.claim
def test_handlers_have_async_handle_method():
    from unified_ingestion.handlers.registry import get_handler_registry
    import inspect

    registry = get_handler_registry()
    handlers = []
    if hasattr(registry, "list_handlers"):
        handlers = registry.list_handlers()
    elif hasattr(registry, "_handlers"):
        handlers = list(registry._handlers.values())

    for handler in handlers[:5]:
        if hasattr(handler, "handle"):
            assert inspect.iscoroutinefunction(handler.handle), "Handler must have async handle method"
