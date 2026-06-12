from unified_ingestion.core.types import ArtifactType
from unified_ingestion.handlers.api_spec import APISpecHandler
from unified_ingestion.handlers.base import Chunk, Handler, HandlerResult
from unified_ingestion.handlers.bpmn import BPMNHandler
from unified_ingestion.handlers.config import ConfigHandler
from unified_ingestion.handlers.diagram import DiagramHandler
from unified_ingestion.handlers.document import DocumentHandler
from unified_ingestion.handlers.graphql import GraphQLHandler
from unified_ingestion.handlers.k8s import K8sHandler
from unified_ingestion.handlers.markdown import MarkdownHandler
from unified_ingestion.handlers.registry import get_handler_registry
from unified_ingestion.handlers.source_code import SourceCodeHandler
from unified_ingestion.handlers.text import TextHandler

try:
    from unified_ingestion.optimize import get_metrics_collector, with_retry

    OPTIMIZE_AVAILABLE = True
except ImportError:
    OPTIMIZE_AVAILABLE = False

    def with_retry(max_attempts: int = 3):
        def decorator(func):
            return func

        return decorator


_document_handler = DocumentHandler()
_markdown_handler = MarkdownHandler()
_source_code_handler = SourceCodeHandler()
_config_handler = ConfigHandler()
_text_handler = TextHandler()
_k8s_handler = K8sHandler()
_diagram_handler = DiagramHandler()
_bpmn_handler = BPMNHandler()
_api_spec_handler = APISpecHandler()
_grpc_handler = GraphQLHandler()


def register_handlers() -> None:
    registry = get_handler_registry()
    registry.register(ArtifactType.DOCUMENT.value, _document_handler)
    registry.register(ArtifactType.MARKDOWN.value, _markdown_handler)
    registry.register(ArtifactType.SOURCE_CODE.value, _source_code_handler)
    registry.register(ArtifactType.CONFIG.value, _config_handler)
    registry.register(ArtifactType.TEXT.value, _text_handler)
    registry.register(ArtifactType.CSV.value, _text_handler)
    registry.register(ArtifactType.TSV.value, _text_handler)
    registry.register(ArtifactType.JSON.value, _config_handler)
    registry.register(ArtifactType.YAML.value, _config_handler)
    registry.register(ArtifactType.TOML.value, _config_handler)
    registry.register(ArtifactType.ENV.value, _config_handler)
    registry.register(ArtifactType.K8S.value, _k8s_handler)
    registry.register(ArtifactType.HELM.value, _k8s_handler)
    registry.register(ArtifactType.DOCKERFILE.value, _k8s_handler)
    registry.register(ArtifactType.ISTIO.value, _k8s_handler)
    registry.register(ArtifactType.DIAGRAM.value, _diagram_handler)
    registry.register(ArtifactType.PLANTUML.value, _diagram_handler)
    registry.register(ArtifactType.MERMAID.value, _diagram_handler)
    registry.register(ArtifactType.C4.value, _diagram_handler)
    registry.register(ArtifactType.BPMN.value, _bpmn_handler)
    registry.register(ArtifactType.API_SPEC.value, _api_spec_handler)
    registry.register(ArtifactType.OPENAPI.value, _api_spec_handler)
    registry.register(ArtifactType.SWAGGER.value, _api_spec_handler)
    registry.register(ArtifactType.GRAPHQL.value, _grpc_handler)


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
