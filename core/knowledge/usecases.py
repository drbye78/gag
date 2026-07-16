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
        # Normalize platform name (accept "sap_btp", "sapbtp", or "sap")
        normalized = platform.replace("_", "").lower()
        # Also handle "sapbtp" → "sap" (the platform ID in the data)
        if normalized == "sapbtp":
            normalized = "sap"
        return [
            uc for uc in self._use_cases.values()
            if any(
                self._normalize_platform(p) == normalized
                for p in uc.platforms
            )
        ]

    @staticmethod
    def _normalize_platform(p: str) -> str:
        n = p.replace("_", "").lower()
        if n == "sapbtp":
            n = "sap"
        return n

    # Alias for test/API compatibility
    def get_by_platform(self, platform: str) -> List[UseCase]:
        return self.find_by_platform(platform)

    def find_by_category(self, category: UseCaseCategory) -> List[UseCase]:
        return [uc for uc in self._use_cases.values() if uc.category == category]
    
    def find_by_priority(self, priority: UseCasePriority) -> List[UseCase]:
        return [uc for uc in self._use_cases.values() if uc.priority == priority]
    
    def list_all(self) -> List[UseCase]:
        return list(self._use_cases.values())

    # Alias for test/API compatibility
    def get_all(self) -> List[UseCase]:
        return self.list_all()


def _create_default_use_cases() -> UseCaseRepository:
    repo = UseCaseRepository()
    
    use_cases = [
        # === SAP BTP (7 use cases across 7 categories) ===
        UseCase(
            id="uc-sap-rest-integration",
            name="SAP REST API Integration",
            description="Integrate SAP BTP with external systems via REST APIs using XSUAA authentication",
            category=UseCaseCategory.INTEGRATION,
            priority=UseCasePriority.HIGH,
            platforms=["sap"],
            patterns=["api-gateway", "rest"],
            technologies=["REST", "OAuth", "JWT", "XSUAA"],
            requirements={"authentication": "OAuth 2.0", "rate_limiting": True},
        ),
        UseCase(
            id="uc-sap-cap-automation",
            name="SAP CAP Workflow Automation",
            description="Automate business workflows using SAP Cloud Application Programming Model",
            category=UseCaseCategory.AUTOMATION,
            priority=UseCasePriority.HIGH,
            platforms=["sap"],
            patterns=["event-driven", "service"],
            technologies=["CAP", "Node.js", "HANA"],
            requirements={"workflow_engine": True},
        ),
        UseCase(
            id="uc-sap-analytics",
            name="SAP HANA Analytics Dashboard",
            description="Build analytics dashboards on SAP HANA with real-time data visualization",
            category=UseCaseCategory.ANALYTICS,
            priority=UseCasePriority.MEDIUM,
            platforms=["sap"],
            patterns=["data-pipeline", "dashboard"],
            technologies=["HANA", "SAP Analytics Cloud"],
            requirements={"real_time": True},
        ),
        UseCase(
            id="uc-sap-security-xsuaa",
            name="SAP XSUAA Security Configuration",
            description="Configure XSUAA for enterprise-grade authentication and authorization",
            category=UseCaseCategory.SECURITY,
            priority=UseCasePriority.CRITICAL,
            platforms=["sap"],
            patterns=["security", "auth"],
            technologies=["XSUAA", "OAuth 2.0", "SAML"],
            requirements={"mfa": True},
        ),
        UseCase(
            id="uc-sap-audit-compliance",
            name="SAP Audit Log Compliance",
            description="Maintain audit logs for compliance with GDPR, SOX, and industry regulations",
            category=UseCaseCategory.COMPLIANCE,
            priority=UseCasePriority.HIGH,
            platforms=["sap"],
            patterns=["audit", "logging"],
            technologies=["Audit Log Service", "Data Retention"],
            requirements={"retention_days": 365},
        ),
        UseCase(
            id="uc-sap-function-flow",
            name="SAP Kyma Serverless Functions",
            description="Deploy serverless functions on SAP Kyma Runtime for event-driven processing",
            category=UseCaseCategory.OPERATIONS,
            priority=UseCasePriority.HIGH,
            platforms=["sap"],
            patterns=["serverless", "functions"],
            technologies=["Kyma", "Node.js", "Python"],
            requirements={"runtime": "kyma"},
        ),
        UseCase(
            id="uc-sap-cicd",
            name="SAP BTP CI/CD Pipeline",
            description="Continuous integration and deployment pipeline for SAP BTP applications",
            category=UseCaseCategory.DEVELOPMENT,
            priority=UseCasePriority.MEDIUM,
            platforms=["sap"],
            patterns=["ci-cd", "automation"],
            technologies=["Jenkins", "MTA", "Cloud Foundry CLI"],
            requirements={"auto_deploy": True},
        ),

        # === AWS (7 use cases across 7 categories) ===
        UseCase(
            id="uc-aws-lambda-api",
            name="AWS Lambda API Gateway",
            description="Build serverless API with Lambda and API Gateway for HTTP request processing",
            category=UseCaseCategory.DEVELOPMENT,
            priority=UseCasePriority.HIGH,
            platforms=["aws"],
            patterns=["serverless", "api-gateway"],
            technologies=["Lambda", "API Gateway", "DynamoDB"],
            requirements={"runtime": "python3.12"},
        ),
        UseCase(
            id="uc-aws-eventbridge-integration",
            name="AWS EventBridge Integration",
            description="Integrate SaaS applications via EventBridge event bus",
            category=UseCaseCategory.INTEGRATION,
            priority=UseCasePriority.HIGH,
            platforms=["aws"],
            patterns=["event-driven", "pub-sub"],
            technologies=["EventBridge", "SNS", "SQS"],
            requirements={"schema_registry": True},
        ),
        UseCase(
            id="uc-aws-step-functions",
            name="AWS Step Functions Automation",
            description="Automate multi-step business processes with Step Functions orchestration",
            category=UseCaseCategory.AUTOMATION,
            priority=UseCasePriority.MEDIUM,
            platforms=["aws"],
            patterns=["workflow", "orchestration"],
            technologies=["Step Functions", "Lambda"],
            requirements={"retry_logic": True},
        ),
        UseCase(
            id="uc-aws-athena-analytics",
            name="AWS Athena Data Analytics",
            description="Run interactive queries on S3 data using Athena for analytics",
            category=UseCaseCategory.ANALYTICS,
            priority=UseCasePriority.MEDIUM,
            platforms=["aws"],
            patterns=["data-lake", "query"],
            technologies=["Athena", "S3", "Glue"],
            requirements={"data_format": "Parquet"},
        ),
        UseCase(
            id="uc-aws-iam-security",
            name="AWS IAM Security Hardening",
            description="Implement least-privilege IAM policies and security best practices",
            category=UseCaseCategory.SECURITY,
            priority=UseCasePriority.CRITICAL,
            platforms=["aws"],
            patterns=["security", "iam"],
            technologies=["IAM", "KMS", "Secrets Manager"],
            requirements={"mfa": True, "password_policy": True},
        ),
        UseCase(
            id="uc-aws-config-compliance",
            name="AWS Config Compliance Rules",
            description="Monitor compliance with Config rules for HIPAA, PCI-DSS, and CIS benchmarks",
            category=UseCaseCategory.COMPLIANCE,
            priority=UseCasePriority.HIGH,
            platforms=["aws"],
            patterns=["compliance", "monitoring"],
            technologies=["Config", "CloudTrail", "Security Hub"],
            requirements={"auto_remediation": True},
        ),
        UseCase(
            id="uc-aws-ecs-operations",
            name="AWS ECS Fargate Operations",
            description="Operate containerized services on ECS Fargate with auto-scaling",
            category=UseCaseCategory.OPERATIONS,
            priority=UseCasePriority.HIGH,
            platforms=["aws"],
            patterns=["container", "serverless"],
            technologies=["ECS", "Fargate", "Application Load Balancer"],
            requirements={"auto_scaling": True},
        ),

        # === Azure (7 use cases across 7 categories) ===
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
            id="uc-azure-logic-apps-integration",
            name="Azure Logic Apps Integration",
            description="Integrate enterprise systems via Logic Apps connectors",
            category=UseCaseCategory.INTEGRATION,
            priority=UseCasePriority.HIGH,
            platforms=["azure"],
            patterns=["workflow", "integration"],
            technologies=["Logic Apps", "Service Bus", "API Management"],
            requirements={"connector_count": 200},
        ),
        UseCase(
            id="uc-azure-automation-runbook",
            name="Azure Automation Runbook",
            description="Automate infrastructure tasks with Azure Automation runbooks",
            category=UseCaseCategory.AUTOMATION,
            priority=UseCasePriority.MEDIUM,
            platforms=["azure"],
            patterns=["automation", "scheduled"],
            technologies=["Automation", "PowerShell", "Hybrid Runbook Worker"],
            requirements={"schedule": True},
        ),
        UseCase(
            id="uc-azure-synapse-analytics",
            name="Azure Synapse Analytics Pipeline",
            description="Build analytics pipelines with Synapse Analytics and Data Lake",
            category=UseCaseCategory.ANALYTICS,
            priority=UseCasePriority.HIGH,
            platforms=["azure"],
            patterns=["data-pipeline", "etl"],
            technologies=["Synapse Analytics", "Data Lake Gen2", "Power BI"],
            requirements={"spark_pool": True},
        ),
        UseCase(
            id="uc-azure-defender-security",
            name="Azure Defender Security Center",
            description="Implement security monitoring with Azure Defender and Sentinel",
            category=UseCaseCategory.SECURITY,
            priority=UseCasePriority.CRITICAL,
            platforms=["azure"],
            patterns=["security", "siem"],
            technologies=["Defender", "Sentinel", "Key Vault"],
            requirements={"threat_detection": True},
        ),
        UseCase(
            id="uc-azure-policy-compliance",
            name="Azure Policy Compliance",
            description="Enforce compliance standards with Azure Policy definitions",
            category=UseCaseCategory.COMPLIANCE,
            priority=UseCasePriority.HIGH,
            platforms=["azure"],
            patterns=["compliance", "governance"],
            technologies=["Policy", "Blueprint", "Compliance"],
            requirements={"initiative_definitions": True},
        ),
        UseCase(
            id="uc-azure-aks-operations",
            name="Azure AKS Kubernetes Operations",
            description="Operate AKS clusters with monitoring and auto-scaling",
            category=UseCaseCategory.OPERATIONS,
            priority=UseCasePriority.HIGH,
            platforms=["azure"],
            patterns=["container", "kubernetes"],
            technologies=["AKS", "Container Registry", "Monitor"],
            requirements={"cluster_autoscaler": True},
        ),

        # === GCP (7 use cases across 7 categories) ===
        UseCase(
            id="uc-gcp-cloud-run",
            name="GCP Cloud Run Deployment",
            description="Deploy containerized application on GCP Cloud Run with auto-scaling",
            category=UseCaseCategory.OPERATIONS,
            priority=UseCasePriority.HIGH,
            platforms=["gcp"],
            patterns=["container", "serverless"],
            technologies=["Cloud Run", "Cloud Build"],
            requirements={"auto_scaling": True},
        ),
        UseCase(
            id="uc-gcp-pubsub-integration",
            name="GCP Pub/Sub Integration",
            description="Integrate services via Pub/Sub messaging for asynchronous communication",
            category=UseCaseCategory.INTEGRATION,
            priority=UseCasePriority.HIGH,
            platforms=["gcp"],
            patterns=["event-driven", "pub-sub"],
            technologies=["Pub/Sub", "Cloud Functions"],
            requirements={"ordering": True},
        ),
        UseCase(
            id="uc-gcp-workflows-automation",
            name="GCP Workflows Automation",
            description="Automate multi-step processes with GCP Workflows orchestration",
            category=UseCaseCategory.AUTOMATION,
            priority=UseCasePriority.MEDIUM,
            platforms=["gcp"],
            patterns=["workflow", "orchestration"],
            technologies=["Workflows", "Cloud Functions"],
            requirements={"error_handling": True},
        ),
        UseCase(
            id="uc-gcp-bigquery-analytics",
            name="GCP BigQuery Analytics",
            description="Run large-scale analytics queries on BigQuery with Data Studio visualization",
            category=UseCaseCategory.ANALYTICS,
            priority=UseCasePriority.HIGH,
            platforms=["gcp"],
            patterns=["data-warehouse", "analytics"],
            technologies=["BigQuery", "Data Studio", "Dataflow"],
            requirements={"partitioning": True},
        ),
        UseCase(
            id="uc-gcp-iam-security",
            name="GCP IAM Security Controls",
            description="Implement security controls with IAM, IAP, and Cloud Armor",
            category=UseCaseCategory.SECURITY,
            priority=UseCasePriority.CRITICAL,
            platforms=["gcp"],
            patterns=["security", "iam"],
            technologies=["IAM", "IAP", "Cloud Armor", "KMS"],
            requirements={"zero_trust": True},
        ),
        UseCase(
            id="uc-gcp-forgovernance-compliance",
            name="GCP Organization Policy Compliance",
            description="Enforce compliance with Organization Policies and Audit Logs",
            category=UseCaseCategory.COMPLIANCE,
            priority=UseCasePriority.HIGH,
            platforms=["gcp"],
            patterns=["compliance", "governance"],
            technologies=["Organization Policy", "Audit Logs", "Forseti"],
            requirements={"constraint_templates": True},
        ),
        UseCase(
            id="uc-gcp-gke-development",
            name="GCP GKE Development Workflow",
            description="Develop and deploy applications on GKE with Cloud Build CI/CD",
            category=UseCaseCategory.DEVELOPMENT,
            priority=UseCasePriority.MEDIUM,
            platforms=["gcp"],
            patterns=["kubernetes", "ci-cd"],
            technologies=["GKE", "Cloud Build", "Artifact Registry"],
            requirements={"skaffold": True},
        ),

        # === VMware Tanzu (7 use cases across 7 categories) ===
        UseCase(
            id="uc-k8s-microservices",
            name="Kubernetes Microservices Deployment",
            description="Deploy microservices on VMware Tanzu Kubernetes cluster with service mesh",
            category=UseCaseCategory.OPERATIONS,
            priority=UseCasePriority.CRITICAL,
            platforms=["tanzu"],
            patterns=["microservices", "container"],
            technologies=["Kubernetes", "Helm", "Istio"],
            requirements={"ingress": True, "monitoring": True},
        ),
        UseCase(
            id="uc-tanzu-spring-integration",
            name="Tanzu Spring Service Integration",
            description="Integrate microservices with Spring Cloud on Tanzu Application Service",
            category=UseCaseCategory.INTEGRATION,
            priority=UseCasePriority.HIGH,
            platforms=["tanzu"],
            patterns=["microservices", "service-mesh"],
            technologies=["Spring Cloud", "Tanzu", "Service Registry"],
            requirements={"service_discovery": True},
        ),
        UseCase(
            id="uc-tanzu-pipeline-automation",
            name="Tanzu Concourse CI/CD Automation",
            description="Automate build and deployment pipelines with Tanzu Concourse",
            category=UseCaseCategory.AUTOMATION,
            priority=UseCasePriority.MEDIUM,
            platforms=["tanzu"],
            patterns=["ci-cd", "automation"],
            technologies=["Concourse", "BOSH", "Tanzu Build Service"],
            requirements={"resource_types": True},
        ),
        UseCase(
            id="uc-tanzu-wavefront-analytics",
            name="Tanzu Wavefront Metrics Analytics",
            description="Collect and analyze application metrics with Wavefront monitoring",
            category=UseCaseCategory.ANALYTICS,
            priority=UseCasePriority.MEDIUM,
            platforms=["tanzu"],
            patterns=["monitoring", "metrics"],
            technologies=["Wavefront", "Micrometer", "Prometheus"],
            requirements={"dashboards": True},
        ),
        UseCase(
            id="uc-tanzu-security-policies",
            name="Tanzu Security Policies",
            description="Implement pod security policies and network policies on Tanzu Kubernetes",
            category=UseCaseCategory.SECURITY,
            priority=UseCasePriority.HIGH,
            platforms=["tanzu"],
            patterns=["security", "kubernetes"],
            technologies=["Pod Security Policies", "Network Policies", "Calico"],
            requirements={"rbac": True},
        ),
        UseCase(
            id="uc-tanzu-compliance-scanning",
            name="Tanzu Container Compliance Scanning",
            description="Scan container images for vulnerabilities and compliance with Tanzu Observability",
            category=UseCaseCategory.COMPLIANCE,
            priority=UseCasePriority.HIGH,
            platforms=["tanzu"],
            patterns=["compliance", "scanning"],
            technologies=["Tanzu Observability", "Clair", "Nessus"],
            requirements={"scan_on_push": True},
        ),
        UseCase(
            id="uc-tanzu-spring-development",
            name="Tanzu Spring Boot Development",
            description="Develop Spring Boot microservices with Tanzu Developer Tools",
            category=UseCaseCategory.DEVELOPMENT,
            priority=UseCasePriority.MEDIUM,
            platforms=["tanzu"],
            patterns=["microservices", "spring"],
            technologies=["Spring Boot", "Tanzu Developer Tools", "Live Update"],
            requirements={"hot_reload": True},
        ),

        # === Power Platform (7 use cases across 7 categories) ===
        UseCase(
            id="uc-powerapps-crm",
            name="Power Apps CRM Integration",
            description="Build Power Apps application with Dataverse backend for CRM",
            category=UseCaseCategory.AUTOMATION,
            priority=UseCasePriority.MEDIUM,
            platforms=["powerplatform"],
            patterns=["low-code"],
            technologies=["Power Apps", "Dataverse"],
            requirements={"dataverse": True},
        ),
        UseCase(
            id="uc-powerautomate-flow-integration",
            name="Power Automate Flow Integration",
            description="Integrate external systems via Power Automate flows and connectors",
            category=UseCaseCategory.INTEGRATION,
            priority=UseCasePriority.HIGH,
            platforms=["powerplatform"],
            patterns=["workflow", "integration"],
            technologies=["Power Automate", "Connectors", "HTTP"],
            requirements={"connector_count": 400},
        ),
        UseCase(
            id="uc-powerautomate-rpa",
            name="Power Automate RPA Automation",
            description="Automate legacy UI interactions with Power Automate Desktop RPA",
            category=UseCaseCategory.AUTOMATION,
            priority=UseCasePriority.MEDIUM,
            platforms=["powerplatform"],
            patterns=["rpa", "automation"],
            technologies=["Power Automate Desktop", "UI Flows"],
            requirements={"unattended_mode": True},
        ),
        UseCase(
            id="uc-powerbi-analytics",
            name="Power BI Analytics Dashboard",
            description="Build interactive analytics dashboards with Power BI on Dataverse data",
            category=UseCaseCategory.ANALYTICS,
            priority=UseCasePriority.HIGH,
            platforms=["powerplatform"],
            patterns=["dashboard", "analytics"],
            technologies=["Power BI", "Dataverse", "Dataflows"],
            requirements={"real_time": True},
        ),
        UseCase(
            id="uc-powerplatform-dlp-security",
            name="Power Platform DLP Security",
            description="Implement Data Loss Prevention policies across Power Platform environments",
            category=UseCaseCategory.SECURITY,
            priority=UseCasePriority.CRITICAL,
            platforms=["powerplatform"],
            patterns=["security", "dlp"],
            technologies=["DLP Policies", "Environment Admin"],
            requirements={"classification": True},
        ),
        UseCase(
            id="uc-powerplatform-audit-compliance",
            name="Power Platform Audit Log Compliance",
            description="Maintain audit logs for Power Platform activities and compliance reporting",
            category=UseCaseCategory.COMPLIANCE,
            priority=UseCasePriority.HIGH,
            platforms=["powerplatform"],
            patterns=["audit", "compliance"],
            technologies=["Microsoft Purview", "Audit Logs"],
            requirements={"retention_days": 90},
        ),
        UseCase(
            id="uc-powerapps-development",
            name="Power Apps Canvas Development",
            description="Develop canvas apps with custom connectors and formulas",
            category=UseCaseCategory.DEVELOPMENT,
            priority=UseCasePriority.MEDIUM,
            platforms=["powerplatform"],
            patterns=["low-code", "canvas"],
            technologies=["Power Apps Canvas", "Power Fx", "Custom Connectors"],
            requirements={"alm": True},
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


# Alias for test/API compatibility — "library" is a common alias for "repository"
def get_use_case_library() -> UseCaseRepository:
    return get_use_case_repository()