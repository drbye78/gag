"""
IR (Intermediate Representation) Schema.

Defines the core IR types for representing engineering knowledge:
- Architecture descriptions
- UI/code artifacts

All schemas use Pydantic v2 with strict typing.
"""

from __future__ import annotations

from datetime import datetime, timezone


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional


class PlatformContext(BaseModel):
    """Platform-agnostic platform context for any technology stack."""
    platform: str = Field(..., description="Platform: sap, salesforce, powerplatform, tanzu, aws, azure, gcp")
    region: Optional[str] = Field(None, description="Region: eu10, us10, etc.")
    environment: Optional[str] = Field(None, description="Environment: dev, staging, prod")
    multi_tenant: bool = Field(default=False, description="Multi-tenant deployment")
    provider: Optional[str] = Field(None, description="Cloud provider: aws, azure, gcp, on-prem")
    version: Optional[str] = Field(None, description="Platform version")


class IRFeature(BaseModel):
    """Extracted features from IR for pattern matching and constraints."""
    # Core capabilities
    has_async: bool = Field(default=False, description="Uses async/event-driven patterns")
    has_auth: bool = Field(default=False, description="Requires authentication")
    has_database: bool = Field(default=False, description="Uses persistent storage")
    has_api: bool = Field(default=False, description="Exposes REST/GraphQL API")
    has_ui: bool = Field(default=False, description="Has user interface")
    has_batch: bool = Field(default=False, description="Has batch processing")
    
    # Architecture patterns
    has_microservices: bool = Field(default=False, description="Microservices architecture")
    has_event_driven: bool = Field(default=False, description="Event-driven architecture")
    has_serverless: bool = Field(default=False, description="Serverless/function as a service")
    has_container: bool = Field(default=False, description="Container-based")
    
    # Data & compliance
    data_classification: str = Field(default="internal", description="internal, pii, sensitive, public")
    compliance_requirements: List[str] = Field(default_factory=list, description="PCI, HIPAA, etc.")
    encryption_required: bool = Field(default=False, description="Data encryption required")
    
    # Integration
    integration_points: List[str] = Field(default_factory=list, description="External service integrations")
    uses_external_services: List[str] = Field(default_factory=list, description="Cloud service dependencies")
    
    # Operations
    scalability_required: bool = Field(default=False, description="Requires horizontal scaling")
    high_availability_required: bool = Field(default=False, description="Needs 99.9%+ SLA")
    multi_region_required: bool = Field(default=False, description="Multi-region deployment")
    
    # Cost sensitivity
    cost_sensitive: bool = Field(default=False, description="Cost optimization important")
    startup_cost_limit: Optional[float] = Field(None, description="Max initial cost in USD")


class EnrichedIR(BaseModel):
    """IR enriched with extracted features for knowledge processing."""
    input_ir: IRNode = Field(..., description="Original IR node")
    platform_context: PlatformContext = Field(..., description="Platform context")
    features: IRFeature = Field(..., description="Extracted features")
    confidence_score: float = Field(default=0.0, description="Confidence in feature extraction")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


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


class ComponentType(str, Enum):
    SERVICE = "service"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    API = "api"
    UI_COMPONENT = "ui_component"
    LIBRARY = "library"
    EXTERNAL_SERVICE = "external_service"
    DATA_STORE = "data_store"
    COMPUTE = "compute"


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


class IRNode(BaseModel):
    id: str = Field(..., description="Unique identifier for this IR node")
    content: str = Field(..., description="The actual content/text")
    artifact_type: ArtifactType = Field(..., description="Type of artifact")
    content_format: str = Field(default="markdown")
    title: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    status: ArtifactStatus = Field(default=ArtifactStatus.RAW)
    source_id: Optional[str] = Field(None)
    parent_id: Optional[str] = Field(None)
    technologies: list[Technology] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    indexed_at: Optional[datetime] = Field(None)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArchitectureIR(IRNode):
    artifact_type: ArtifactType = Field(default=ArtifactType.ARCHITECTURE, frozen=True)
    architecture_type: Optional[str] = Field(None)
    components: list[ComponentSpec] = Field(default_factory=list)
    relationships: list[RelationshipSpec] = Field(default_factory=list)
    data_flows: list[DataFlowSpec] = Field(default_factory=list)
    diagram_url: Optional[str] = Field(None)


class ComponentSpec(BaseModel):
    id: str = Field(...)
    name: str = Field(...)
    type: ComponentType = Field(...)
    description: Optional[str] = Field(None)
    technology: Optional[Technology] = Field(None)
    technologies: list[Technology] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    externals: list[str] = Field(default_factory=list)
    replicas: Optional[int] = Field(None)
    resources: Optional[ResourceSpec] = Field(None)


class RelationshipSpec(BaseModel):
    source_id: str = Field(...)
    target_id: str = Field(...)
    relationship_type: str = Field(...)
    protocol: Optional[str] = Field(None)
    description: Optional[str] = Field(None)


class DataFlowSpec(BaseModel):
    name: str = Field(...)
    from_component: str = Field(...)
    to_component: str = Field(...)
    data_type: str = Field(...)
    direction: str = Field(default="bidirectional")


class ResourceSpec(BaseModel):
    cpu: Optional[str] = Field(None)
    memory: Optional[str] = Field(None)
    storage: Optional[str] = Field(None)


class UIIR(IRNode):
    artifact_type: ArtifactType = Field(default=ArtifactType.UI, frozen=True)
    ui_type: Optional[str] = Field(None)
    framework: Optional[str] = Field(None)
    component_name: Optional[str] = Field(None)
    component_path: Optional[str] = Field(None)
    layout: Optional[str] = Field(None)
    theme: Optional[str] = Field(None)
    responsive: bool = Field(default=False)
    screen_id: Optional[str] = Field(None)
    user_flows: list[str] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)
    # Graph-first fields
    graph_node_id: Optional[str] = Field(None)
    element_count: int = Field(default=0)
    pattern_matches: list[str] = Field(default_factory=list)
    sap_candidates: list[str] = Field(default_factory=list)
    visual_embedding_id: Optional[str] = Field(None)


class CodeIR(IRNode):
    artifact_type: ArtifactType = Field(default=ArtifactType.CODE, frozen=True)
    language: Optional[str] = Field(None)
    framework: Optional[str] = Field(None)
    file_path: Optional[str] = Field(None)
    repo_url: Optional[str] = Field(None)
    start_line: Optional[int] = Field(None)
    end_line: Optional[int] = Field(None)
    entity_type: Optional[str] = Field(None)
    entity_name: Optional[str] = Field(None)
    imports: list[str] = Field(default_factory=list)
    exports: list[str] = Field(default_factory=list)
    calls: list[str] = Field(default_factory=list)
    http_method: Optional[str] = Field(None)
    endpoint: Optional[str] = Field(None)


class DocumentIR(IRNode):
    artifact_type: ArtifactType = Field(default=ArtifactType.DOCUMENTATION, frozen=True)
    doc_type: Optional[str] = Field(None)
    file_path: Optional[str] = Field(None)
    url: Optional[str] = Field(None)
    sections: list[str] = Field(default_factory=list)


class IRCollection(BaseModel):
    id: str = Field(...)
    name: str = Field(...)
    description: Optional[str] = Field(None)
    nodes: list[IRNode] = Field(default_factory=list)
    version: str = Field(default="1.0.0")
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def artifact_types(self) -> set[ArtifactType]:
        return {node.artifact_type for node in self.nodes}

    def add_node(self, node: IRNode) -> None:
        node.parent_id = self.id
        self.nodes.append(node)
        self.updated_at = datetime.now(timezone.utc)

    def get_nodes_by_type(self, artifact_type: ArtifactType) -> list[IRNode]:
        return [n for n in self.nodes if n.artifact_type == artifact_type]

    def get_node(self, node_id: str) -> Optional[IRNode]:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
