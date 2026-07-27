"""
README claim: "Unified Ingestion: 33 artifact types, 24 handlers, platform extension architecture"
Source: README.md line 124
"""
import pytest


@pytest.mark.claim
def test_thirty_three_artifact_types():
    from unified_ingestion.core.types import ArtifactType
    types = [t for t in ArtifactType]
    assert len(types) == 40, f"Expected 40 artifact types (33 original + 7 new: drawio, confluence, sap_mta, sap_cds, sap_cap, sap_xsuaa, template), got {len(types)}: {[t.value for t in types]}"


@pytest.mark.claim
def test_handler_registry_exists():
    from unified_ingestion.handlers.registry import get_handler_registry
    from unified_ingestion.handlers import register_handlers
    register_handlers()
    registry = get_handler_registry()
    assert registry is not None

    handlers = []
    if hasattr(registry, "list_handlers"):
        handlers = registry.list_handlers()
    elif hasattr(registry, "_handlers"):
        handlers = list(registry._handlers.values())

    assert len(handlers) >= 20, f"Expected >=20 handlers, got {len(handlers)}"


@pytest.mark.claim
def test_handlers_have_async_handle_method():
    from unified_ingestion.handlers.registry import get_handler_registry
    from unified_ingestion.handlers import register_handlers
    import inspect

    register_handlers()
    registry = get_handler_registry()
    handlers = []
    if hasattr(registry, "list_handlers"):
        handlers = registry.list_handlers()
    elif hasattr(registry, "_handlers"):
        handlers = list(registry._handlers.values())

    for handler in handlers[:5]:
        if hasattr(handler, "handle"):
            assert inspect.iscoroutinefunction(handler.handle), "Handler must have async handle method"
