from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class ADRStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class ADRDecision(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    SUPERSEDED = "superseded"


class ADR(BaseModel):
    id: str = Field(...)
    title: str = Field(...)
    status: ADRStatus = Field(ADRStatus.PROPOSED)
    context: str = Field(...)
    decision: str = Field(...)
    consequences: str = Field(...)
    related_patterns: List[str] = Field(default_factory=list)
    related_platforms: List[str] = Field(default_factory=list)
    superseded_by: Optional[str] = Field(None)
    notes: List[str] = Field(default_factory=list)
    owner: Optional[str] = Field(None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ADRRepository:
    def __init__(self):
        self._adrs: Dict[str, ADR] = {}
    
    def add(self, adr: ADR) -> None:
        self._adrs[adr.id] = adr
    
    def get(self, adr_id: str) -> Optional[ADR]:
        return self._adrs.get(adr_id)
    
    def find_by_status(self, status: ADRStatus) -> List[ADR]:
        return [a for a in self._adrs.values() if a.status == status]
    
    def find_by_platform(self, platform: str) -> List[ADR]:
        return [a for a in self._adrs.values() if platform in a.related_platforms]
    
    def find_by_pattern(self, pattern: str) -> List[ADR]:
        return [a for a in self._adrs.values() if pattern in a.related_patterns]
    
    def list_all(self) -> List[ADR]:
        return list(self._adrs.values())


def _create_default_adrs() -> ADRRepository:
    repo = ADRRepository()
    
    adrs = [
        ADR(
            id="adr-001",
            title="Use Serverless for Event-Driven Workloads",
            status=ADRStatus.ACCEPTED,
            context="Need to handle variable workloads efficiently without managing infrastructure",
            decision="Use serverless functions (Lambda/Azure Functions/Cloud Functions) for event-driven processing",
            consequences="Reduced operational overhead but increasedvendor lock-in risk",
            related_patterns=["serverless", "event-driven"],
            related_platforms=["aws", "azure", "gcp", "sap"],
        ),
        ADR(
            id="adr-002",
            title="Use Kubernetes for Container Orchestration",
            status=ADRStatus.ACCEPTED,
            context="Need consistent container orchestration across environments",
            decision="Use Kubernetes (EKS/AKS/GKE/Tanzu) for all container workloads",
            consequences="Requires Kubernetes expertise but provides portability",
            related_patterns=["microservices", "container"],
            related_platforms=["aws", "azure", "gcp", "tanzu"],
        ),
        ADR(
            id="adr-003",
            title="Use Managed Databases Over Self-Hosted",
            status=ADRStatus.ACCEPTED,
            context="Database operations are overhead and require specialized skills",
            decision="Use managed database services (DynamoDB/Cosmos DB/Firestore/HANA)",
            consequences="Less operational control but reduced maintenance burden",
            related_patterns=["database"],
            related_platforms=["aws", "azure", "gcp", "sap"],
        ),
        ADR(
            id="adr-004",
            title="Use API Gateway for All External APIs",
            status=ADRStatus.ACCEPTED,
            context="Need consistent API management, authentication, and rate limiting",
            decision="Use platform-specific API Gateway services",
            consequences="Unified API management but adds a new service",
            related_patterns=["api-gateway"],
            related_platforms=["aws", "azure", "gcp", "sap"],
        ),
        ADR(
            id="adr-005",
            title="Adopt Platform-Agnostic Patterns",
            status=ADRStatus.ACCEPTED,
            context="Need to support multiple cloud platforms with minimal code changes",
            decision="Use platform-agnostic patterns that can map to any provider",
            consequences="May not use all native platform features",
            related_patterns=["serverless", "microservices", "event-driven"],
            related_platforms=["aws", "azure", "gcp", "tanzu"],
        ),
    ]
    
    for adr in adrs:
        repo.add(adr)
    
    return repo


_adr_repo: Optional[ADRRepository] = None


def get_adr_repository() -> ADRRepository:
    global _adr_repo
    if _adr_repo is None:
        _adr_repo = _create_default_adrs()
    return _adr_repo