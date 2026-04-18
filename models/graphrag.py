from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class EntityType(str, Enum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    CONCEPT = "CONCEPT"
    EVENT = "EVENT"
    LOCATION = "LOCATION"
    PRODUCT = "PRODUCT"
    TECHNOLOGY = "TECHNOLOGY"
    DOCUMENT = "DOCUMENT"
    PROCESS = "PROCESS"
    COMPONENT = "COMPONENT"
    SERVICE = "SERVICE"
    API = "API"
    FUNCTION = "FUNCTION"
    CLASS = "CLASS"
    MODULE = "MODULE"


class RelationshipType(str, Enum):
    RELATED_TO = "RELATED_TO"
    PART_OF = "PART_OF"
    WORKS_FOR = "WORKS_FOR"
    LOCATED_AT = "LOCATED_AT"
    USES = "USES"
    DEPENDS_ON = "DEPENDS_ON"
    CREATED_BY = "CREATED_BY"
    DEFINED_IN = "DEFINED_IN"
    REFERENCES = "REFERENCES"
    CONTAINS = "CONTAINS"
    IMPLEMENTS = "IMPLEMENTS"
    MANAGES = "MANAGES"
    CALLS = "CALLS"
    IMPORTS = "IMPORTS"
    INHERITS = "INHERITS"


class EntityNode(BaseModel):
    id: str = Field(..., description="Unique entity identifier")
    name: str = Field(..., description="Entity name")
    entity_type: EntityType = Field(..., description="Type of entity")
    description: Optional[str] = Field(None, description="Entity description")
    properties: dict[str, Any] = Field(default_factory=dict)
    source_id: Optional[str] = Field(None, description="Source document ID")
    confidence: float = Field(default=1.0, description="Extraction confidence")


class RelationshipEdge(BaseModel):
    source_id: str = Field(..., description="Source entity ID")
    target_id: str = Field(..., description="Target entity ID")
    relationship_type: RelationshipType = Field(..., description="Type of relationship")
    confidence: float = Field(default=1.0, description="Relationship confidence")
    context: Optional[str] = Field(None, description="Context from source text")
    properties: dict[str, Any] = Field(default_factory=dict)


class Community(BaseModel):
    id: str = Field(..., description="Community ID")
    name: str = Field(..., description="Community name")
    member_ids: list[str] = Field(default_factory=list, description="Member entity IDs")
    size: int = Field(default=0, description="Number of members")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GraphRAGConfig(BaseModel):
    enabled: bool = Field(default=False, description="Enable GraphRAG processing")
    use_llm_extraction: bool = Field(default=False, description="Use LLM for extraction")
    structural_chunking: bool = Field(default=True, description="Use structural chunking")
    incremental: bool = Field(default=True, description="Enable incremental processing")
    community_detection: bool = Field(default=True, description="Run community detection")
    max_entities: int = Field(default=100, description="Max entities per document")
    default_hops: int = Field(default=3, description="Default graph traversal depth")
    entity_types: list[EntityType] = Field(
        default_factory=lambda: [
            EntityType.PERSON,
            EntityType.ORGANIZATION,
            EntityType.CONCEPT,
            EntityType.TECHNOLOGY,
        ]
    )
    relationship_types: list[RelationshipType] = Field(
        default_factory=lambda: [
            RelationshipType.RELATED_TO,
            RelationshipType.DEPENDS_ON,
            RelationshipType.REFERENCES,
        ]
    )


class GraphRAGQueryRequest(BaseModel):
    query: str = Field(..., description="User query")
    include_entities: bool = Field(default=True, description="Include entities in response")
    include_relationships: bool = Field(default=True, description="Include relationships in response")
    include_communities: bool = Field(default=False, description="Include communities in response")
    max_hops: int = Field(default=3, description="Maximum graph traversal hops")


class GraphRAGQueryResponse(BaseModel):
    query: str
    answer: str
    entities: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    communities: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.0
    sources: list[dict[str, Any]] = Field(default_factory=list)
    took_ms: int = 0


class EntitySearchRequest(BaseModel):
    source_id: Optional[str] = Field(None, description="Filter by source document")
    entity_type: Optional[EntityType] = Field(None, description="Filter by entity type")
    limit: int = Field(default=100, description="Maximum results")


class EntitySearchResponse(BaseModel):
    entities: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class RelationshipSearchRequest(BaseModel):
    source_id: Optional[str] = Field(None, description="Filter by source")
    relationship_type: Optional[RelationshipType] = Field(None, description="Filter by type")
    limit: int = Field(default=100, description="Maximum results")


class RelationshipSearchResponse(BaseModel):
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class CommunityResponse(BaseModel):
    id: str
    name: str
    members: list[dict[str, Any]] = Field(default_factory=list)
    size: int = 0


class GraphRAGStatsResponse(BaseModel):
    total_entities: int = 0
    total_relationships: int = 0
    total_communities: int = 0
    entity_types: dict[str, int] = Field(default_factory=dict)
    relationship_types: dict[str, int] = Field(default_factory=dict)
    avg_entities_per_community: float = 0.0