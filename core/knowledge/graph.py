from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Set
from enum import Enum
from datetime import datetime
import uuid


class NodeType(str, Enum):
    PLATFORM = "platform"
    SERVICE = "service"
    TECHNOLOGY = "technology"
    PATTERN = "pattern"
    CONSTRAINT = "constraint"
    USE_CASE = "use_case"
    REFERENCE_ARCH = "reference_arch"
    DECISION = "decision"


class EdgeType(str, Enum):
    REQUIRES = "requires"
    PROVIDES = "provides"
    IMPLEMENTS = "implements"
    CONFLICTS = "conflicts"
    ALTERNATIVE = "alternative"
    DEPENDS_ON = "depends_on"
    WORKS_WITH = "works_with"
    COMPOSED_OF = "composed_of"


class KnowledgeNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(...)
    type: NodeType = Field(...)
    properties: Dict[str, Any] = Field(default_factory=dict)
    version: str = Field("1.0.0")
    deprecated: bool = Field(False)
    source: str = Field("")
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeEdge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = Field(...)
    target_id: str = Field(...)
    type: EdgeType = Field(...)
    weight: float = Field(1.0, ge=0.0, le=1.0)
    conditions: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeGraph(BaseModel):
    nodes: Dict[str, KnowledgeNode] = Field(default_factory=dict)
    edges: List[KnowledgeEdge] = Field(default_factory=list)
    by_type: Dict[NodeType, Set[str]] = Field(default_factory=dict)
    by_name: Dict[str, Set[str]] = Field(default_factory=dict)

    model_config = {"extra": "ignore"}

    def add_node(self, node_or_id, name: str = "", node_type = None,
                 platform: Optional[str] = None, metadata: Optional[Dict] = None,
                 properties: Optional[Dict[str, Any]] = None) -> KnowledgeNode:
        """Add or update a node in the knowledge graph.

        Accepts either a KnowledgeNode object or individual parameters.
        """
        if isinstance(node_or_id, KnowledgeNode):
            node = node_or_id
        else:
            # Convenience signature: add_node(node_id, name, node_type, ...)
            if isinstance(node_type, str):
                try:
                    node_type = NodeType(node_type)
                except ValueError:
                    node_type = NodeType.SERVICE
            elif node_type is None:
                node_type = NodeType.SERVICE
            merged_props = dict(properties or {})
            if platform:
                merged_props["platform"] = platform
            if metadata:
                merged_props.update(metadata)
            node = KnowledgeNode(
                id=str(node_or_id),
                name=name,
                type=node_type,
                properties=merged_props,
            )

        # Remove old indices if updating an existing node
        if node.id in self.nodes:
            old = self.nodes[node.id]
            if old.type in self.by_type:
                self.by_type[old.type].discard(node.id)
            old_key = old.name.lower()
            if old_key in self.by_name:
                self.by_name[old_key].discard(node.id)

        self.nodes[node.id] = node
        if node.type not in self.by_type:
            self.by_type[node.type] = set()
        self.by_type[node.type].add(node.id)
        key = node.name.lower()
        if key not in self.by_name:
            self.by_name[key] = set()
        self.by_name[key].add(node.id)
        return node

    def add_edge(self, source_or_edge, target: Optional[str] = None,
                 edge_type = None, weight: float = 1.0) -> Optional[KnowledgeEdge]:
        """Add or update an edge between two nodes.

        Accepts either a KnowledgeEdge object or individual parameters.
        """
        if isinstance(source_or_edge, KnowledgeEdge):
            edge = source_or_edge
        else:
            if isinstance(edge_type, str):
                try:
                    edge_type = EdgeType(edge_type)
                except ValueError:
                    edge_type = EdgeType.DEPENDS_ON
            elif edge_type is None:
                edge_type = EdgeType.DEPENDS_ON
            edge = KnowledgeEdge(
                source_id=str(source_or_edge),
                target_id=str(target) if target else "",
                type=edge_type,
                weight=weight,
            )

        if edge.source_id not in self.nodes or edge.target_id not in self.nodes:
            return None

        # Check for existing edge to update
        for i, e in enumerate(self.edges):
            if e.source_id == edge.source_id and e.target_id == edge.target_id and e.type == edge.type:
                self.edges[i] = edge
                return edge
        self.edges.append(edge)
        return edge

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all its incident edges from the graph."""
        if node_id not in self.nodes:
            return False

        node = self.nodes[node_id]
        if node.type in self.by_type:
            self.by_type[node.type].discard(node_id)
        key = node.name.lower()
        if key in self.by_name:
            self.by_name[key].discard(node_id)

        del self.nodes[node_id]
        self.edges = [e for e in self.edges
                      if e.source_id != node_id and e.target_id != node_id]
        return True

    def search_nodes(self, query: str, node_type: Optional[str] = None) -> List[KnowledgeNode]:
        """Search nodes by name or id substring, optionally filtered by type."""
        results: List[KnowledgeNode] = []
        query_lower = query.lower()
        for node in self.nodes.values():
            if query_lower in node.name.lower() or query_lower in node.id.lower():
                if node_type is None or node.type.value == node_type:
                    results.append(node)
        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Return graph statistics for monitoring."""
        platforms: Set[str] = set()
        node_types: Set[str] = set()
        edge_types: Set[str] = set()
        for n in self.nodes.values():
            if n.type:
                node_types.add(n.type.value)
            plat = n.properties.get("platform")
            if plat:
                platforms.add(plat)
        for e in self.edges:
            if e.type:
                edge_types.add(e.type.value)
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "platforms": sorted(platforms),
            "node_types": sorted(node_types),
            "edge_types": sorted(edge_types),
        }

    def find_by_type(self, node_type: NodeType) -> List[KnowledgeNode]:
        ids = self.by_type.get(node_type, set())
        return [self.nodes[nid] for nid in ids if nid in self.nodes]

    def find_by_name(self, name: str) -> List[KnowledgeNode]:
        key = name.lower()
        ids = self.by_name.get(key, set())
        return [self.nodes[nid] for nid in ids if nid in self.nodes]

    def find_related(
        self,
        node_id: str,
        edge_types: List[EdgeType] = None,
        depth: int = 1
    ) -> List[KnowledgeNode]:
        if depth == 0 or node_id not in self.nodes:
            return []
        
        visited = set()
        
        def _recurse(current_id: str, current_depth: int) -> List[str]:
            if current_id in visited:
                return []
            visited.add(current_id)
            
            related_ids = set()
            for edge in self.edges:
                if edge.source_id == current_id:
                    if edge_types is None or edge.type in edge_types:
                        related_ids.add(edge.target_id)
                elif edge.target_id == current_id and edge.type == EdgeType.DEPENDS_ON:
                    if edge_types is None or edge.type in edge_types:
                        related_ids.add(edge.source_id)
            
            result = []
            for rid in related_ids:
                if rid in self.nodes:
                    result.append(rid)
                    if current_depth > 1:
                        result.extend(_recurse(rid, current_depth - 1))
            return result
        
        related_ids = _recurse(node_id, depth)
        return [self.nodes[rid] for rid in related_ids if rid in self.nodes]

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        return self.nodes.get(node_id)


_knowledge_graph: Optional[KnowledgeGraph] = None


def get_knowledge_graph() -> KnowledgeGraph:
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeGraph()
        _load_default_knowledge(_knowledge_graph)
    return _knowledge_graph


def _load_default_knowledge(graph: KnowledgeGraph) -> None:
    platforms = [
        ("sap", "SAP BTP", "sap,cloud,enterprise"),
        ("tanzu", "VMware Tanzu", "vmware,cloud-native,kubernetes"),
        ("powerplatform", "Microsoft Power Platform", "powerapps,powerautomate,dataverse,copilotstudio"),
        ("aws", "Amazon Web Services", "aws,cloud,serverless,lambda"),
        ("azure", "Microsoft Azure", "azure,cloud,functions"),
        ("gcp", "Google Cloud Platform", "gcp,cloud,serverless"),
    ]
    
    for pid, name, keywords in platforms:
        graph.add_node(KnowledgeNode(
            id=pid,
            name=name,
            type=NodeType.PLATFORM,
            properties={"keywords": keywords.split(",")},
        ))
    
    services = [
        ("xsuaa", "SAP XSUAA", "sap", "authentication,authorization"),
        ("hana", "SAP HANA", "sap", "database,in-memory"),
        ("kyma", "SAP Kyma Runtime", "sap", "serverless,functions"),
        ("dataverse", "Microsoft Dataverse", "powerplatform", "database,tables"),
        ("kubernetes", "Kubernetes", "tanzu", "container-orchestration"),
        ("lambda", "AWS Lambda", "aws", "serverless,functions"),
        ("s3", "AWS S3", "aws", "storage,object"),
        ("dynamodb", "AWS DynamoDB", "aws", "nosql,database"),
        ("functions", "Azure Functions", "azure", "serverless,functions"),
        ("cosmos", "Azure Cosmos DB", "azure", "nosql,database"),
        ("gcf", "GCP Cloud Functions", "gcp", "serverless,functions"),
        ("firestore", "GCP Firestore", "gcp", "nosql,database"),
    ]
    
    for sid, name, platform, desc in services:
        graph.add_node(KnowledgeNode(
            id=sid,
            name=name,
            type=NodeType.SERVICE,
            properties={"platform": platform, "description": desc},
        ))
        
        parent = platform if platform != "powerplatform" else "powerplatform"
        graph.add_edge(KnowledgeEdge(
            source_id=parent,
            target_id=sid,
            type=EdgeType.PROVIDES,
        ))
    
    technologies = [
        ("rest", "REST API"),
        ("graphql", "GraphQL"),
        ("kafka", "Apache Kafka"),
        ("oauth", "OAuth 2.0"),
        ("jwt", "JWT"),
        ("grpc", "gRPC"),
        ("postgresql", "PostgreSQL"),
        ("redis", "Redis"),
    ]
    
    for tid, name in technologies:
        graph.add_node(KnowledgeNode(
            id=tid,
            name=name,
            type=NodeType.TECHNOLOGY,
        ))