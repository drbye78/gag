"""Unified ingestion handlers — lazy imports to avoid cascading dependencies."""
from unified_ingestion.handlers.base import Handler, HandlerResult, Chunk
from unified_ingestion.core.types import ArtifactType
from unified_ingestion.handlers.registry import get_handler_registry

try:
    from unified_ingestion.optimize import with_retry, get_metrics_collector
    OPTIMIZE_AVAILABLE = True
except ImportError:
    OPTIMIZE_AVAILABLE = False
    def with_retry(max_attempts: int = 3):
        def decorator(func):
            return func
        return decorator

# Lazy handler instances — created on first registration
_handlers_cache = {}

def _get_or_create(handler_cls):
    """Get cached handler instance or create new one."""
    if handler_cls.__name__ not in _handlers_cache:
        _handlers_cache[handler_cls.__name__] = handler_cls()
    return _handlers_cache[handler_cls.__name__]


def register_handlers() -> None:
    """Register all handlers — imports are lazy to avoid cascading deps."""
    registry = get_handler_registry()

    # Lazy imports — only loaded when handlers are actually registered
    from unified_ingestion.handlers.document import DocumentHandler
    from unified_ingestion.handlers.markdown import MarkdownHandler
    from unified_ingestion.handlers.source_code import SourceCodeHandler
    from unified_ingestion.handlers.config import ConfigHandler
    from unified_ingestion.handlers.text import TextHandler
    from unified_ingestion.handlers.k8s import K8sHandler
    from unified_ingestion.handlers.diagram import DiagramHandler
    from unified_ingestion.handlers.bpmn import BPMNHandler
    from unified_ingestion.handlers.api_spec import APISpecHandler
    from unified_ingestion.handlers.graphql import GraphQLHandler

    registry.register(ArtifactType.DOCUMENT.value, _get_or_create(DocumentHandler))
    registry.register(ArtifactType.MARKDOWN.value, _get_or_create(MarkdownHandler))
    registry.register(ArtifactType.SOURCE_CODE.value, _get_or_create(SourceCodeHandler))
    registry.register(ArtifactType.CONFIG.value, _get_or_create(ConfigHandler))
    registry.register(ArtifactType.TEXT.value, _get_or_create(TextHandler))
    registry.register(ArtifactType.CSV.value, _get_or_create(TextHandler))
    registry.register(ArtifactType.TSV.value, _get_or_create(TextHandler))
    registry.register(ArtifactType.JSON.value, _get_or_create(ConfigHandler))
    registry.register(ArtifactType.YAML.value, _get_or_create(ConfigHandler))
    registry.register(ArtifactType.TOML.value, _get_or_create(ConfigHandler))
    registry.register(ArtifactType.ENV.value, _get_or_create(ConfigHandler))
    registry.register(ArtifactType.K8S.value, _get_or_create(K8sHandler))
    registry.register(ArtifactType.HELM.value, _get_or_create(K8sHandler))
    registry.register(ArtifactType.DOCKERFILE.value, _get_or_create(K8sHandler))
    registry.register(ArtifactType.ISTIO.value, _get_or_create(K8sHandler))
    registry.register(ArtifactType.DIAGRAM.value, _get_or_create(DiagramHandler))
    registry.register(ArtifactType.PLANTUML.value, _get_or_create(DiagramHandler))
    registry.register(ArtifactType.MERMAID.value, _get_or_create(DiagramHandler))
    registry.register(ArtifactType.C4.value, _get_or_create(DiagramHandler))
    registry.register(ArtifactType.BPMN.value, _get_or_create(BPMNHandler))
    registry.register(ArtifactType.API_SPEC.value, _get_or_create(APISpecHandler))
    registry.register(ArtifactType.OPENAPI.value, _get_or_create(APISpecHandler))
    registry.register(ArtifactType.SWAGGER.value, _get_or_create(APISpecHandler))
    registry.register(ArtifactType.GRAPHQL.value, _get_or_create(GraphQLHandler))


def get_handler(artifact_type: str) -> Handler:
    registry = get_handler_registry()
    handler = registry.get(artifact_type)
    if handler is None:
        raise ValueError(f"No handler registered for artifact type: {artifact_type}")
    if isinstance(handler, Handler):
        return handler
    if callable(handler):
        return handler()
    raise ValueError(f"Invalid handler for artifact type: {artifact_type}")


__all__ = [
    "Handler",
    "HandlerResult",
    "Chunk",
    "DocumentHandler",
    "MarkdownHandler",
    "SourceCodeHandler",
    "ConfigHandler",
    "TextHandler",
    "K8sHandler",
    "DiagramHandler",
    "BPMNHandler",
    "APISpecHandler",
    "GraphQLHandler",
    "register_handlers",
    "get_handler",
]