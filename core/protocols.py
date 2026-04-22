"""Protocol interfaces for core layer - inverts dependency from core->models."""

from typing import Protocol, Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class IRFeatureProtocol(Protocol):
    """Extracted features from IR for pattern matching and constraints."""
    has_async: bool
    has_auth: bool
    has_database: bool
    has_api: bool
    has_ui: bool
    has_batch: bool
    has_microservices: bool
    has_event_driven: bool
    has_serverless: bool
    has_container: bool
    data_classification: str
    compliance_requirements: List[str]
    encryption_required: bool
    integration_points: List[str]
    uses_external_services: List[str]
    scalability_required: bool
    high_availability_required: bool
    multi_region_required: bool
    cost_sensitive: bool
    startup_cost_limit: Optional[float]


class PlatformContextProtocol(Protocol):
    """Platform-agnostic platform context for any technology stack."""
    platform: str
    region: Optional[str]
    environment: Optional[str]
    multi_tenant: bool
    provider: Optional[str]
    version: Optional[str]


class IRNodeProtocol(Protocol):
    """IR node representing an artifact."""
    id: str
    content: str
    artifact_type: "ArtifactType"
    content_format: str
    title: Optional[str]
    description: Optional[str]
    status: "ArtifactStatus"
    source_id: Optional[str]
    parent_id: Optional[str]
    technologies: List["Technology"]
    created_at: datetime
    updated_at: datetime
    indexed_at: Optional[datetime]
    metadata: Dict[str, Any]


class ArtifactType(str, Enum):
    ARCHITECTURE = "architecture"
    UI = "ui"
    CODE = "code"
    DOCUMENTATION = "documentation"
    CONFIG = "config"
    DEPLOYMENT = "deployment"


class ArtifactStatus(str, Enum):
    RAW = "raw"
    PROCESSED = "processed"
    VALIDATED = "validated"
    INDEXED = "indexed"
    ENRICHED = "enriched"


class Technology(str, Enum):
    FASTAPI = "fastapi"
    FLASK = "flask"
    DJANGO = "django"
    EXPRESS = "express"
    SPRING = "spring"
    QDRANT = "qdrant"
    FALKORDB = "falkordb"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    REDIS = "redis"
    OPENAI = "openai"
    QWEN = "qwen"
    GLM = "glm"
    QWEN_VL = "qwen_vl"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    LANGGRAPH = "langgraph"
    OPENTELEMETRY = "opentelemetry"


class EnrichedIRProtocol(Protocol):
    """IR enriched with extracted features for knowledge processing."""
    input_ir: IRNodeProtocol
    platform_context: PlatformContextProtocol
    features: IRFeatureProtocol
    confidence_score: float
    metadata: Dict[str, Any]


# Aliases for backward compatibility with imports from core.protocols
IRFeature = IRFeatureProtocol
PlatformContext = PlatformContextProtocol
IRNode = IRNodeProtocol
EnrichedIR = EnrichedIRProtocol