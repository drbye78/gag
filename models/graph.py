"""
Graph Schema - Knowledge graph models for FalkorDB.

Defines nodes and edges for architecture, code,
tickets, and metrics.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class GraphNodeType(str, Enum):
    ARCHITECTURE = "architecture"
    COMPONENT = "component"
    SERVICE = "service"
    DATABASE = "database"
    API = "api"
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    FILE = "file"
    DOCUMENT = "document"
    TICKET = "ticket"
    USER = "user"
    TEAM = "team"
    REPOSITORY = "repository"
    COMMIT = "commit"
    RELEASE = "release"
    METRIC = "metric"


class GraphEdgeType(str, Enum):
    CONTAINS = "contains"
    DEPENDS_ON = "depends_on"
    CALLS = "calls"
    IMPORTS = "imports"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    USES = "uses"
    CREATED_BY = "created_by"
    ASSIGNED_TO = "assigned_to"
    PART_OF = "part_of"
    REFERENCES = "references"
    DOCUMENTED_BY = "documented_by"
    DEPLOYED_IN = "deployed_in"
    LINKED_TO = "linked_to"
    RELATED_TO = "related_to"


class GraphNode(BaseModel):
    id: str = Field(...)
    node_type: GraphNodeType = Field(...)
    name: str = Field(...)
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GraphEdge(BaseModel):
    id: str = Field(...)
    edge_type: GraphEdgeType = Field(...)
    source_id: str = Field(...)
    target_id: str = Field(...)
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ComponentNode(GraphNode):
    node_type: GraphNodeType = Field(default=GraphNodeType.COMPONENT, frozen=True)
    component_type: Optional[str] = Field(None)
    technology: Optional[str] = Field(None)
    status: Optional[str] = Field(None)


class ServiceNode(GraphNode):
    node_type: GraphNodeType = Field(default=GraphNodeType.SERVICE, frozen=True)
    endpoint: Optional[str] = Field(None)
    http_method: Optional[str] = Field(None)
    protocol: Optional[str] = Field(None)


class CodeEntityNode(GraphNode):
    node_type: GraphNodeType = Field(default=GraphNodeType.FUNCTION, frozen=True)
    entity_type: str = Field(...)
    file_path: Optional[str] = Field(None)
    language: Optional[str] = Field(None)
    start_line: Optional[int] = Field(None)
    end_line: Optional[int] = Field(None)


class GraphQuery(BaseModel):
    node_types: list[GraphNodeType] = Field(default_factory=list)
    edge_types: list[GraphEdgeType] = Field(default_factory=list)
    properties_filter: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=100)
    depth: int = Field(default=2)


class SubgraphResult(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)
