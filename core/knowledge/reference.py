from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum


class ReferenceArchitectureType(str, Enum):
    SERVERLESS = "serverless"
    MICROSERVICES = "microservices"
    EVENT_DRIVEN = "event-driven"
    DATA_PIPELINE = "data-pipeline"
    API_GATEWAY = "api-gateway"
    HYBRID_INTEGRATION = "hybrid-integration"


class ReferenceArchitecture(BaseModel):
    id: str = Field(...)
    name: str = Field(...)
    type: ReferenceArchitectureType = Field(...)
    description: str = Field(...)
    platforms: List[str] = Field(default_factory=list)
    components: List[str] = Field(default_factory=list)
    data_flow: List[str] = Field(default_factory=list)
    quality_attributes: Dict[str, str] = Field(default_factory=dict)
    diagram: Optional[str] = Field(None)


class ReferenceArchitectureRepository:
    def __init__(self):
        self._refs: Dict[str, ReferenceArchitecture] = {}
    
    def add(self, ref: ReferenceArchitecture) -> None:
        self._refs[ref.id] = ref
    
    def get(self, ref_id: str) -> Optional[ReferenceArchitecture]:
        return self._refs.get(ref_id)
    
    def find_by_type(self, ref_type: ReferenceArchitectureType) -> List[ReferenceArchitecture]:
        return [r for r in self._refs.values() if r.type == ref_type]
    
    def find_by_platform(self, platform: str) -> List[ReferenceArchitecture]:
        return [r for r in self._refs.values() if platform in r.platforms]
    
    def list_all(self) -> List[ReferenceArchitecture]:
        return list(self._refs.values())


def _create_default_references() -> ReferenceArchitectureRepository:
    repo = ReferenceArchitectureRepository()
    
    refs = [
        ReferenceArchitecture(
            id="ref-serverless-aws",
            name="AWS Serverless API",
            type=ReferenceArchitectureType.SERVERLESS,
            description="Serverless HTTP API using Lambda and API Gateway with DynamoDB",
            platforms=["aws"],
            components=["API Gateway", "Lambda", "DynamoDB", "CloudWatch"],
            data_flow=["Client → API Gateway → Lambda → DynamoDB"],
            quality_attributes={
                "scalability": "Automatic",
                "cost": "Pay-per-request",
                "availability": "99.95%",
            },
        ),
        ReferenceArchitecture(
            id="ref-serverless-azure",
            name="Azure Serverless API",
            type=ReferenceArchitectureType.SERVERLESS,
            description="Serverless HTTP API using Azure Functions with Cosmos DB",
            platforms=["azure"],
            components=["Azure Functions", "Cosmos DB", "Application Insights"],
            data_flow=["Client → Azure Functions → Cosmos DB"],
            quality_attributes={
                "scalability": "Automatic",
                "cost": "Pay-per-execution",
                "availability": "99.95%",
            },
        ),
        ReferenceArchitecture(
            id="ref-serverless-gcp",
            name="GCP Serverless API",
            type=ReferenceArchitectureType.SERVERLESS,
            description="Serverless HTTP API using Cloud Functions with Firestore",
            platforms=["gcp"],
            components=["Cloud Functions", "Firestore", "Cloud Monitoring"],
            data_flow=["Client → Cloud Functions → Firestore"],
            quality_attributes={
                "scalability": "Automatic",
                "cost": "Pay-per-invocation",
                "availability": "99.95%",
            },
        ),
        ReferenceArchitecture(
            id="ref-microservices-k8s",
            name="Kubernetes Microservices",
            type=ReferenceArchitectureType.MICROSERVICES,
            description="Containerized microservices on Kubernetes with service mesh",
            platforms=["tanzu", "aws", "azure", "gcp"],
            components=["Kubernetes", "Ingress", "Service Mesh", "Prometheus", "Grafana"],
            data_flow=["Client → Ingress → Service → Database"],
            quality_attributes={
                "scalability": "Manual + HPA",
                "cost": "Fixed + compute",
                "availability": "99.9%",
            },
        ),
        ReferenceArchitecture(
            id="ref-event-driven-aws",
            name="AWS Event-Driven",
            type=ReferenceArchitectureType.EVENT_DRIVEN,
            description="Event-driven architecture using Lambda, SNS/SQS, and EventBridge",
            platforms=["aws"],
            components=["Lambda", "SNS", "SQS", "EventBridge", "DynamoDB"],
            data_flow=["Event → SNS → Lambda → DynamoDB"],
            quality_attributes={
                "scalability": "Automatic",
                "coupling": "Loose",
                "availability": "99.95%",
            },
        ),
        ReferenceArchitecture(
            id="ref-event-driven-azure",
            name="Azure Event-Driven",
            type=ReferenceArchitectureType.EVENT_DRIVEN,
            description="Event-driven architecture using Event Hub and Azure Functions",
            platforms=["azure"],
            components=["Event Hub", "Azure Functions", "Cosmos DB"],
            data_flow=["Event → Event Hub → Functions → Cosmos DB"],
            quality_attributes={
                "scalability": "Automatic",
                "coupling": "Loose",
                "availability": "99.95%",
            },
        ),
        ReferenceArchitecture(
            id="ref-api-gateway-sap",
            name="SAP API Gateway",
            type=ReferenceArchitectureType.API_GATEWAY,
            description="SAP BTP API Gateway for exposing enterprise services",
            platforms=["sap"],
            components=["API Gateway", "XSUAA", "Destination Service", "SAP S/4HANA"],
            data_flow=["External → API Gateway → XSUAA → Destination → S/4HANA"],
            quality_attributes={
                "scalability": "Enterprise",
                "security": "Enterprise-grade",
                "availability": "99.9%",
            },
        ),
        ReferenceArchitecture(
            id="ref-hybrid-sap-cloud",
            name="SAP Hybrid Integration",
            type=ReferenceArchitectureType.HYBRID_INTEGRATION,
            description="Hybrid integration between SAP on-premise and cloud",
            platforms=["sap"],
            components=["SAP Cloud Connector", "XSUAA", "Destination Service", "SAP S/4HANA"],
            data_flow=["On-premise → Cloud Connector → Cloud → S/4HANA"],
            quality_attributes={
                "security": "High",
                "latency": "Network-dependent",
                "availability": "99.9%",
            },
        ),
    ]
    
    for ref in refs:
        repo.add(ref)
    
    return repo


_ref_arch_repo: Optional[ReferenceArchitectureRepository] = None


def get_reference_architecture_repository() -> ReferenceArchitectureRepository:
    global _ref_arch_repo
    if _ref_arch_repo is None:
        _ref_arch_repo = _create_default_references()
    return _ref_arch_repo