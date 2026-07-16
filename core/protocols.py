"""Protocol interfaces for core layer - inverts dependency from core->models."""

from typing import Protocol, Any, Dict, List, Optional
from datetime import datetime

from models.ir import ArtifactType, ArtifactStatus, Technology


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