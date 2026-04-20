from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class UseCaseCategory(str, Enum):
    INTEGRATION = "integration"
    AUTOMATION = "automation"
    ANALYTICS = "analytics"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    OPERATIONS = "operations"
    DEVELOPMENT = "development"


class UseCasePriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class UseCase(BaseModel):
    id: str = Field(...)
    name: str = Field(...)
    description: str = Field(...)
    category: UseCaseCategory = Field(...)
    priority: UseCasePriority = Field(UseCasePriority.MEDIUM)
    platforms: List[str] = Field(default_factory=list)
    patterns: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    requirements: Dict[str, Any] = Field(default_factory=dict)
    acceptance_criteria: List[str] = Field(default_factory=list)
    effort_estimate: Optional[str] = Field(None)
    risk_level: Optional[str] = Field(None)
    owner: Optional[str] = Field(None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UseCaseRepository:
    def __init__(self):
        self._use_cases: Dict[str, UseCase] = {}
    
    def add(self, use_case: UseCase) -> None:
        self._use_cases[use_case.id] = use_case
    
    def get(self, use_case_id: str) -> Optional[UseCase]:
        return self._use_cases.get(use_case_id)
    
    def find_by_platform(self, platform: str) -> List[UseCase]:
        return [uc for uc in self._use_cases.values() if platform in uc.platforms]
    
    def find_by_category(self, category: UseCaseCategory) -> List[UseCase]:
        return [uc for uc in self._use_cases.values() if uc.category == category]
    
    def find_by_priority(self, priority: UseCasePriority) -> List[UseCase]:
        return [uc for uc in self._use_cases.values() if uc.priority == priority]
    
    def list_all(self) -> List[UseCase]:
        return list(self._use_cases.values())


def _create_default_use_cases() -> UseCaseRepository:
    repo = UseCaseRepository()
    
    use_cases = [
        UseCase(
            id="uc-sap-rest-integration",
            name="SAP REST API Integration",
            description="Integrate SAP BTP with external systems via REST APIs",
            category=UseCaseCategory.INTEGRATION,
            priority=UseCasePriority.HIGH,
            platforms=["sap"],
            patterns=["api-gateway", "rest"],
            technologies=["REST", "OAuth", "JWT"],
            requirements={"authentication": "OAuth 2.0", "rate_limiting": True},
        ),
        UseCase(
            id="uc-sap-function-flow",
            name="SAP Kyma Serverless Functions",
            description="Deploy serverless functions on SAP Kyma Runtime",
            category=UseCaseCategory.DEVELOPMENT,
            priority=UseCasePriority.HIGH,
            platforms=["sap"],
            patterns=["serverless", "functions"],
            technologies=["Node.js", "Python"],
            requirements={"runtime": "cloud-foundry"},
        ),
        UseCase(
            id="uc-k8s-microservices",
            name="Kubernetes Microservices Deployment",
            description="Deploy microservices on VMware Tanzu Kubernetes cluster",
            category=UseCaseCategory.OPERATIONS,
            priority=UseCasePriority.CRITICAL,
            platforms=["tanzu"],
            patterns=["microservices", "container"],
            technologies=["Kubernetes", "Helm", "Istio"],
            requirements={"ingress": True, "monitoring": True},
        ),
        UseCase(
            id="uc-powerapps-crm",
            name="Power Apps CRM Integration",
            description="Build Power Apps application with Dataverse backend",
            category=UseCaseCategory.AUTOMATION,
            priority=UseCasePriority.MEDIUM,
            platforms=["powerplatform"],
            patterns=["low-code"],
            technologies=["Power Apps", "Dataverse"],
            requirements={"dataverse": True},
        ),
        UseCase(
            id="uc-aws-lambda-api",
            name="AWS Lambda API Gateway",
            description="Build serverless API with Lambda and API Gateway",
            category=UseCaseCategory.DEVELOPMENT,
            priority=UseCasePriority.HIGH,
            platforms=["aws"],
            patterns=["serverless", "api-gateway"],
            technologies=["Lambda", "API Gateway", "DynamoDB"],
            requirements={"runtime": "python3.12"},
        ),
        UseCase(
            id="uc-azure-functions-http",
            name="Azure Functions HTTP Trigger",
            description="Create HTTP-triggered Azure Functions for API endpoints",
            category=UseCaseCategory.DEVELOPMENT,
            priority=UseCasePriority.HIGH,
            platforms=["azure"],
            patterns=["serverless", "http-trigger"],
            technologies=["Azure Functions", "Cosmos DB"],
            requirements={"durable": False},
        ),
        UseCase(
            id="uc-gcp-cloud-run",
            name="GCP Cloud Run Deployment",
            description="Deploy containerized application on GCP Cloud Run",
            category=UseCaseCategory.OPERATIONS,
            priority=UseCasePriority.HIGH,
            platforms=["gcp"],
            patterns=["container", "serverless"],
            technologies=["Cloud Run", "Cloud Build"],
            requirements={"auto_scaling": True},
        ),
    ]
    
    for uc in use_cases:
        repo.add(uc)
    
    return repo


_use_case_repo: Optional[UseCaseRepository] = None


def get_use_case_repository() -> UseCaseRepository:
    global _use_case_repo
    if _use_case_repo is None:
        _use_case_repo = _create_default_use_cases()
    return _use_case_repo