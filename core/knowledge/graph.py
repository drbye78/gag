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

    def add_node(self, node: KnowledgeNode) -> None:
        self.nodes[node.id] = node
        if node.type not in self.by_type:
            self.by_type[node.type] = set()
        self.by_type[node.type].add(node.id)
        key = node.name.lower()
        if key not in self.by_name:
            self.by_name[key] = set()
        self.by_name[key].add(node.id)

    def add_edge(self, edge: KnowledgeEdge) -> None:
        if edge.source_id in self.nodes and edge.target_id in self.nodes:
            self.edges.append(edge)

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
        
        related_ids = set()
        for edge in self.edges:
            if edge.source_id == node_id:
                if edge_types is None or edge.type in edge_types:
                    related_ids.add(edge.target_id)
            elif edge.target_id == node_id and edge.type == EdgeType.DEPENDS_ON:
                if edge_types is None or edge.type in edge_types:
                    related_ids.add(edge.source_id)
        
        result = [self.nodes[rid] for rid in related_ids if rid in self.nodes]
        
        if depth > 1:
            for node in result[:]:
                deeper = self.find_related(node.id, edge_types, depth - 1)
                result.extend(deeper)
        
        return result

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