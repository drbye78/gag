"""Platform V adapter — SberTech Russian enterprise PaaS platform.

Provides architecture recommendations, config generation, and API client
stubs for Platform V's 55+ products across 7 portfolios:

    - Data Management   (Pangolin, DataGrid, Dictionaries, DataSpace...)
    - Integration       (Synapse Service Mesh, API Mesh, App Mesh...)
    - Development       (Works: TaskTracker, Pipeliner, CodeScanner...)
    - Security          (IAM SE, SOWA, CryptoService, Audit SE)
    - Low-Code / Apps   (Flow, Studio, Functions, API Mock...)
    - Infrastructure    (SberLinux OS, Container Platform, Monitor...)
    - Management Tools  (Product 360, Cost Calculator...)

Auth flows: OAuth2 client credentials via IAM SE (Keycloak).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

from core.adapters.base import AdapterInput, AdapterOutput, PlatformAdapter
from core.adapters.mixins import RecommendationMixin
from core.adapters.models import (
    ComplianceFramework,
    ComplianceMatrix,
    CostEstimate,
    FSTECLevel,
    ServiceEdition,
    ServiceSpec,
    summarize_portfolios,
)
from core.constraints.engine import Constraint, ConstraintSet, get_constraint_engine
from core.knowledge.adrs import ADR, ADRStatus, get_adr_repository
from core.knowledge.graph import (
    EdgeType,
    KnowledgeEdge,
    KnowledgeNode,
    NodeType,
    get_knowledge_graph,
)
from core.knowledge.reference import (
    ReferenceArchitecture,
    ReferenceArchitectureType,
    get_reference_architecture_repository,
)
from core.knowledge.usecases import (
    UseCase,
    UseCaseCategory,
    UseCasePriority,
    get_use_case_repository,
)
from core.patterns.schema import Pattern
from models.ir import IRFeature

# ---------------------------------------------------------------------------
# Product catalogue — organised by portfolio
# ---------------------------------------------------------------------------

PLATFORM_V_SERVICES = [
    # ---- Data Management (10) ----
    "Platform V Pangolin",
    "Platform V Pangolin SE",
    "Platform V DataGrid",
    "Platform V Dictionaries",
    "Platform V DataSpace",
    "Platform V DataSpace CE",
    "Platform V Application Sharding",
    "Platform V Multi Data Clusters",
    "Platform V Index Search",
    "Platform V Grid Center",
    "Platform V Kintsugi",
    "Platform V Corax",
    "Platform V Batch",
    # ---- Integration / Synapse (8) ----
    "Platform V Synapse Service Mesh",
    "Platform V Synapse API Mesh",
    "Platform V Synapse App Mesh",
    "Platform V Synapse API Management",
    "Platform V Synapse Event Replication",
    "Platform V Synapse Messaging",
    "Platform V Synapse AI",
    "Platform V Synapse File Exchange",
    # ---- Development / Works (13) ----
    "Platform V Works::Projects",
    "Platform V Works::TaskTracker",
    "Platform V Works::SourceControl",
    "Platform V Works::GigaIDE Cloud",
    "Platform V Works::Architect",
    "Platform V Works::Pipeliner",
    "Platform V Works::Orchestra R",
    "Platform V Works::CodeScanner",
    "Platform V Works::Artifactory",
    "Platform V Works::TestCulture",
    "Platform V Works::Test Data Management",
    "Platform V Works::Autotest",
    "Platform V Works::Developer Portal",
    "Platform V GigaCode",
    # ---- Security (6) ----
    "Platform V IAM SE",
    "Platform V IDM",
    "Platform V SOWA",
    "Platform V CryptoService",
    "Platform V One Time Tokens",
    "Platform V Audit SE",
    # ---- Low-Code / Application Platform (7) ----
    "Platform V Flow",
    "Platform V Studio",
    "Platform V UI Workflow",
    "Platform V Functions",
    "Platform V API Mock & Contract Testing",
    "Platform V Frontend High Load",
    "Platform V Backend",
    # ---- Infrastructure & Runtime (7) ----
    "Platform V SberLinux OS Server",
    "Platform V Container Platform",
    "Platform V Starting Manager",
    "Platform V Monitor",
    "Platform V Configuration",
    "Platform V DataTools",
    "Platform V Model Execution Framework",
    # ---- Management Tools (2) ----
    "Platform V Product 360",
    "Platform V Cost Calculator",
]

# Map product names to their portfolio for UI grouping
PRODUCT_PORTFOLIO: Dict[str, str] = {
    # Data Management
    "Platform V Pangolin": "data_management",
    "Platform V Pangolin SE": "data_management",
    "Platform V DataGrid": "data_management",
    "Platform V Dictionaries": "data_management",
    "Platform V DataSpace": "data_management",
    "Platform V DataSpace CE": "data_management",
    "Platform V Application Sharding": "data_management",
    "Platform V Multi Data Clusters": "data_management",
    "Platform V Index Search": "data_management",
    "Platform V Grid Center": "data_management",
    "Platform V Kintsugi": "data_management",
    "Platform V Corax": "data_management",
    "Platform V Batch": "data_management",
    # Integration
    "Platform V Synapse Service Mesh": "integration",
    "Platform V Synapse API Mesh": "integration",
    "Platform V Synapse App Mesh": "integration",
    "Platform V Synapse API Management": "integration",
    "Platform V Synapse Event Replication": "integration",
    "Platform V Synapse Messaging": "integration",
    "Platform V Synapse AI": "integration",
    "Platform V Synapse File Exchange": "integration",
    "Platform V SOWA": "integration",
    # Development
    "Platform V Works::Projects": "development",
    "Platform V Works::TaskTracker": "development",
    "Platform V Works::SourceControl": "development",
    "Platform V Works::GigaIDE Cloud": "development",
    "Platform V Works::Architect": "development",
    "Platform V Works::Pipeliner": "development",
    "Platform V Works::Orchestra R": "development",
    "Platform V Works::CodeScanner": "development",
    "Platform V Works::Artifactory": "development",
    "Platform V Works::TestCulture": "development",
    "Platform V Works::Test Data Management": "development",
    "Platform V Works::Autotest": "development",
    "Platform V Works::Developer Portal": "development",
    "Platform V GigaCode": "development",
    # Security
    "Platform V IAM SE": "security",
    "Platform V IDM": "security",
    "Platform V CryptoService": "security",
    "Platform V One Time Tokens": "security",
    "Platform V Audit SE": "security",
    # Low-Code
    "Platform V Flow": "low_code",
    "Platform V Studio": "low_code",
    "Platform V UI Workflow": "low_code",
    "Platform V Functions": "low_code",
    "Platform V API Mock & Contract Testing": "low_code",
    "Platform V Frontend High Load": "low_code",
    "Platform V Backend": "low_code",
    # Infrastructure
    "Platform V SberLinux OS Server": "infrastructure",
    "Platform V Container Platform": "infrastructure",
    "Platform V Starting Manager": "infrastructure",
    "Platform V Monitor": "infrastructure",
    "Platform V Configuration": "infrastructure",
    "Platform V DataTools": "infrastructure",
    "Platform V Model Execution Framework": "infrastructure",
    # Management
    "Platform V Product 360": "management",
    "Platform V Cost Calculator": "management",
}

# ---------------------------------------------------------------------------
# ServiceSpec catalog — rich service descriptors
# ---------------------------------------------------------------------------

PLATFORM_V_SERVICE_CATALOG: List[ServiceSpec] = [
    # -- Data Management (13) --
    ServiceSpec(
        name="Platform V Pangolin",
        portfolio="data_management",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L4", "RRPO"],
        dependencies=["Platform V SberLinux OS Server"],
        tags=["postgresql", "rdbms", "sql", "oracle-migration", "1c", "database"],
        cost_model={"monthly_min": 500, "monthly_max": 5000, "pricing_tier": "per-core"},
        regions=["ru-central1", "ru-north", "ru-east"],
        description="Enterprise PostgreSQL RDBMS with 80+ security patches, FSTEC-certified",
    ),
    ServiceSpec(
        name="Platform V Pangolin SE",
        portfolio="data_management",
        edition=ServiceEdition.SE,
        sla="99.99%",
        certifications=["FSTEC L4", "RRPO", "GOST"],
        dependencies=["Platform V SberLinux OS Server"],
        tags=["postgresql", "rdbms", "sql", "special-edition", "security"],
        cost_model={"monthly_min": 1500, "monthly_max": 12000, "pricing_tier": "per-core"},
        regions=["ru-central1"],
        description="Special Edition Pangolin with enhanced FSTEC/GOST security features",
    ),
    ServiceSpec(
        name="Platform V DataGrid",
        portfolio="data_management",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V SberLinux OS Server"],
        tags=["in-memory", "cache", "grid", "apache-ignite", "key-value"],
        cost_model={"monthly_min": 300, "monthly_max": 3000, "pricing_tier": "per-node"},
        regions=["ru-central1", "ru-north"],
        description="In-memory distributed data grid (Apache Ignite SE)",
    ),
    ServiceSpec(
        name="Platform V Dictionaries",
        portfolio="data_management",
        edition=ServiceEdition.STANDARD,
        sla="99.9%",
        certifications=["RRPO"],
        dependencies=[],
        tags=["mdm", "reference-data", "dictionary"],
        cost_model={"monthly_min": 200, "monthly_max": 1500, "pricing_tier": "per-request"},
        regions=["ru-central1"],
        description="MDM reference data management",
    ),
    ServiceSpec(
        name="Platform V DataSpace",
        portfolio="data_management",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.95%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V IAM SE", "Platform V SberLinux OS Server"],
        tags=["low-code", "baas", "graphql", "ddd", "crud", "backend"],
        cost_model={"monthly_min": 1000, "monthly_max": 8000, "pricing_tier": "per-project"},
        regions=["ru-central1", "ru-north"],
        description="Low-code DDD-driven BaaS with auto-generated GraphQL API",
    ),
    ServiceSpec(
        name="Platform V DataSpace CE",
        portfolio="data_management",
        edition=ServiceEdition.COMMUNITY,
        sla="99.0%",
        certifications=[],
        dependencies=["Platform V IAM SE"],
        tags=["open-source", "baas", "graphql", "ddd", "community"],
        cost_model={"monthly_min": 0, "monthly_max": 500, "pricing_tier": "free"},
        regions=["any"],
        description="Open-source Community Edition of DataSpace",
    ),
    ServiceSpec(
        name="Platform V Application Sharding",
        portfolio="data_management",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V Pangolin"],
        tags=["sharding", "scaling", "distributed", "database"],
        cost_model={"monthly_min": 800, "monthly_max": 5000, "pricing_tier": "per-shard"},
        regions=["ru-central1"],
        description="Horizontal database sharding for Pangolin",
    ),
    ServiceSpec(
        name="Platform V Multi Data Clusters",
        portfolio="data_management",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V Application Sharding"],
        tags=["multi-cluster", "geo-distributed", "replication"],
        cost_model={"monthly_min": 2000, "monthly_max": 10000, "pricing_tier": "per-cluster"},
        regions=["ru-central1", "ru-north", "ru-east"],
        description="Multi-region and multi-cluster database deployment",
    ),
    ServiceSpec(
        name="Platform V Index Search",
        portfolio="data_management",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.95%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V SberLinux OS Server"],
        tags=["search", "indexing", "full-text", "elasticsearch"],
        cost_model={"monthly_min": 400, "monthly_max": 3000, "pricing_tier": "per-node"},
        regions=["ru-central1"],
        description="Distributed search and indexing service",
    ),
    ServiceSpec(
        name="Platform V Grid Center",
        portfolio="data_management",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V SberLinux OS Server"],
        tags=["grid-computing", "hpc", "distributed-computing"],
        cost_model={"monthly_min": 1000, "monthly_max": 8000, "pricing_tier": "per-node"},
        regions=["ru-central1"],
        description="High-performance grid computing platform",
    ),
    ServiceSpec(
        name="Platform V Kintsugi",
        portfolio="data_management",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.95%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V SberLinux OS Server"],
        tags=["data-fabric", "virtualization", "integration"],
        cost_model={"monthly_min": 600, "monthly_max": 4000, "pricing_tier": "per-connection"},
        regions=["ru-central1"],
        description="Data fabric and virtualization layer",
    ),
    ServiceSpec(
        name="Platform V Corax",
        portfolio="data_management",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V Pangolin"],
        tags=["analytics", "olap", "columnar", "read-heavy", "warehouse"],
        cost_model={"monthly_min": 800, "monthly_max": 6000, "pricing_tier": "per-node"},
        regions=["ru-central1", "ru-north"],
        description="Columnar analytics database for read-heavy workloads",
    ),
    ServiceSpec(
        name="Platform V Batch",
        portfolio="data_management",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.95%",
        certifications=[],
        dependencies=["Platform V Container Platform"],
        tags=["batch", "etl", "scheduling", "job"],
        cost_model={"monthly_min": 300, "monthly_max": 2000, "pricing_tier": "per-job"},
        regions=["ru-central1"],
        description="Enterprise batch job scheduling and execution",
    ),
    # -- Integration / Synapse (8) --
    ServiceSpec(
        name="Platform V Synapse Service Mesh",
        portfolio="integration",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=[
            "Platform V Container Platform",
            "Platform V IAM SE",
        ],
        tags=["istio", "service-mesh", "microservices", "traffic-management"],
        cost_model={"monthly_min": 2000, "monthly_max": 15000, "pricing_tier": "per-cluster"},
        regions=["ru-central1", "ru-north", "ru-east"],
        description="Istio-based enterprise service mesh",
    ),
    ServiceSpec(
        name="Platform V Synapse API Mesh",
        portfolio="integration",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V IAM SE"],
        tags=["api-gateway", "api-management", "gateway"],
        cost_model={"monthly_min": 1000, "monthly_max": 8000, "pricing_tier": "per-request"},
        regions=["ru-central1", "ru-north"],
        description="Centralized API management gateway",
    ),
    ServiceSpec(
        name="Platform V Synapse App Mesh",
        portfolio="integration",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V IAM SE"],
        tags=["esb", "integration", "soa", "app-mesh"],
        cost_model={"monthly_min": 1500, "monthly_max": 10000, "pricing_tier": "per-message"},
        regions=["ru-central1"],
        description="Distributed ESB for enterprise integration",
    ),
    ServiceSpec(
        name="Platform V Synapse API Management",
        portfolio="integration",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.95%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V Synapse API Mesh"],
        tags=["api-management", "developer-portal", "analytics"],
        cost_model={"monthly_min": 800, "monthly_max": 5000, "pricing_tier": "per-api"},
        regions=["ru-central1"],
        description="Full API lifecycle management and developer portal",
    ),
    ServiceSpec(
        name="Platform V Synapse Event Replication",
        portfolio="integration",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V Container Platform"],
        tags=["event-streaming", "kafka", "replication", "async"],
        cost_model={"monthly_min": 1200, "monthly_max": 7000, "pricing_tier": "per-stream"},
        regions=["ru-central1", "ru-north"],
        description="Event streaming and cross-region replication",
    ),
    ServiceSpec(
        name="Platform V Synapse Messaging",
        portfolio="integration",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V Container Platform"],
        tags=["message-broker", "queue", "rabbitmq", "amqp"],
        cost_model={"monthly_min": 500, "monthly_max": 3000, "pricing_tier": "per-node"},
        regions=["ru-central1"],
        description="Enterprise message broker",
    ),
    ServiceSpec(
        name="Platform V Synapse AI",
        portfolio="integration",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.95%",
        certifications=[],
        dependencies=["Platform V Synapse API Mesh"],
        tags=["ai", "ml", "inference", "ai-gateway"],
        cost_model={"monthly_min": 1000, "monthly_max": 10000, "pricing_tier": "per-request"},
        regions=["ru-central1"],
        description="AI/ML integration gateway for model inference and orchestration",
    ),
    ServiceSpec(
        name="Platform V Synapse File Exchange",
        portfolio="integration",
        edition=ServiceEdition.STANDARD,
        sla="99.9%",
        certifications=["FSTEC L2"],
        dependencies=[],
        tags=["file-transfer", "sftp", "edi", "b2b"],
        cost_model={"monthly_min": 200, "monthly_max": 1500, "pricing_tier": "per-transfer"},
        regions=["ru-central1"],
        description="Managed B2B file exchange and EDI gateway",
    ),
    # -- Development / Works (13) --
    ServiceSpec(
        name="Platform V Works::Projects",
        portfolio="development",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.95%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V IAM SE"],
        tags=["project-management", "portfolio", "planning"],
        cost_model={"monthly_min": 300, "monthly_max": 2000, "pricing_tier": "per-user"},
        regions=["ru-central1"],
        description="Portfolio and project management",
    ),
    ServiceSpec(
        name="Platform V Works::TaskTracker",
        portfolio="development",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.95%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V IAM SE"],
        tags=["agile", "scrum", "kanban", "task-management", "jira"],
        cost_model={"monthly_min": 200, "monthly_max": 1500, "pricing_tier": "per-user"},
        regions=["ru-central1"],
        description="Agile task and backlog management (Jira-compatible)",
    ),
    ServiceSpec(
        name="Platform V Works::SourceControl",
        portfolio="development",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V IAM SE"],
        tags=["git", "source-control", "gitlab", "version-control"],
        cost_model={"monthly_min": 200, "monthly_max": 1000, "pricing_tier": "per-user"},
        regions=["ru-central1"],
        description="Enterprise source control (GitLab-compatible)",
    ),
    ServiceSpec(
        name="Platform V Works::GigaIDE Cloud",
        portfolio="development",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.9%",
        certifications=[],
        dependencies=["Platform V IAM SE"],
        tags=["ide", "cloud-ide", "vs-code", "development"],
        cost_model={"monthly_min": 100, "monthly_max": 500, "pricing_tier": "per-user"},
        regions=["ru-central1"],
        description="Cloud-based IDE with AI-assisted development",
    ),
    ServiceSpec(
        name="Platform V Works::Architect",
        portfolio="development",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.9%",
        certifications=[],
        dependencies=["Platform V IAM SE"],
        tags=["architecture", "modeling", "uml", "c4"],
        cost_model={"monthly_min": 150, "monthly_max": 800, "pricing_tier": "per-user"},
        regions=["ru-central1"],
        description="Architecture modeling and documentation tool",
    ),
    ServiceSpec(
        name="Platform V Works::Pipeliner",
        portfolio="development",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=[
            "Platform V Works::SourceControl",
            "Platform V Container Platform",
        ],
        tags=["ci-cd", "pipeline", "devops", "gitlab-ci", "jenkins"],
        cost_model={"monthly_min": 500, "monthly_max": 3000, "pricing_tier": "per-pipeline"},
        regions=["ru-central1"],
        description="CI/CD pipeline orchestration (GitLab CI-compatible)",
    ),
    ServiceSpec(
        name="Platform V Works::Orchestra R",
        portfolio="development",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V Works::Pipeliner"],
        tags=["release", "orchestration", "deployment", "automation"],
        cost_model={"monthly_min": 400, "monthly_max": 2500, "pricing_tier": "per-release"},
        regions=["ru-central1"],
        description="Release orchestration and deployment automation",
    ),
    ServiceSpec(
        name="Platform V Works::CodeScanner",
        portfolio="development",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.9%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V Works::SourceControl"],
        tags=["code-scan", "static-analysis", "sonarqube", "license", "sbom"],
        cost_model={"monthly_min": 300, "monthly_max": 2000, "pricing_tier": "per-project"},
        regions=["ru-central1"],
        description="Static code analysis, SAST, and license compliance (SonarQube-compatible)",
    ),
    ServiceSpec(
        name="Platform V Works::Artifactory",
        portfolio="development",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V Works::SourceControl"],
        tags=["artifact", "registry", "docker", "npm", "maven"],
        cost_model={"monthly_min": 200, "monthly_max": 1000, "pricing_tier": "per-storage-gb"},
        regions=["ru-central1"],
        description="Binary and container image artifact registry",
    ),
    ServiceSpec(
        name="Platform V Works::TestCulture",
        portfolio="development",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.9%",
        certifications=[],
        dependencies=["Platform V Works::Pipeliner"],
        tags=["testing", "quality", "test-management"],
        cost_model={"monthly_min": 200, "monthly_max": 1000, "pricing_tier": "per-user"},
        regions=["ru-central1"],
        description="Test management and quality metrics platform",
    ),
    ServiceSpec(
        name="Platform V Works::Test Data Management",
        portfolio="development",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.9%",
        certifications=[],
        dependencies=["Platform V Pangolin"],
        tags=["test-data", "data-generation", "masking", "subset"],
        cost_model={"monthly_min": 300, "monthly_max": 1500, "pricing_tier": "per-database"},
        regions=["ru-central1"],
        description="Test data generation, masking and subsetting",
    ),
    ServiceSpec(
        name="Platform V Works::Autotest",
        portfolio="development",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.9%",
        certifications=[],
        dependencies=["Platform V Works::Pipeliner"],
        tags=["automated-testing", "regression", "ui-test", "api-test"],
        cost_model={"monthly_min": 400, "monthly_max": 2000, "pricing_tier": "per-test-run"},
        regions=["ru-central1"],
        description="Automated regression testing framework",
    ),
    ServiceSpec(
        name="Platform V Works::Developer Portal",
        portfolio="development",
        edition=ServiceEdition.STANDARD,
        sla="99.9%",
        certifications=[],
        dependencies=["Platform V Works::Pipeliner"],
        tags=["developer-portal", "backstage", "documentation", "catalog"],
        cost_model={"monthly_min": 150, "monthly_max": 800, "pricing_tier": "per-user"},
        regions=["ru-central1"],
        description="Internal developer portal and service catalog",
    ),
    ServiceSpec(
        name="Platform V GigaCode",
        portfolio="development",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.9%",
        certifications=[],
        dependencies=["Platform V Works::GigaIDE Cloud"],
        tags=["ai", "assistant", "code-completion", "code-generation", "copilot"],
        cost_model={"monthly_min": 50, "monthly_max": 500, "pricing_tier": "per-user"},
        regions=["ru-central1", "ru-north"],
        description="AI-powered developer assistant for code completion and generation",
    ),
    # -- Security (6) --
    ServiceSpec(
        name="Platform V One Time Tokens",
        portfolio="security",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.95%",
        certifications=["FSTEC L3", "GOST"],
        dependencies=["Platform V IAM SE"],
        tags=["tokens", "ott", "service-auth", "authentication", "api-keys"],
        cost_model={"monthly_min": 200, "monthly_max": 1500, "pricing_tier": "per-request"},
        regions=["ru-central1", "ru-north"],
        description="Service-to-service authentication via one-time tokens (OTT)",
    ),
    ServiceSpec(
        name="Platform V IAM SE",
        portfolio="security",
        edition=ServiceEdition.SE,
        sla="99.99%",
        certifications=["FSTEC L4", "GOST", "RRPO"],
        dependencies=["Platform V SberLinux OS Server"],
        tags=["iam", "oauth", "oidc", "keycloak", "sso", "esia", "rbac"],
        cost_model={"monthly_min": 1000, "monthly_max": 8000, "pricing_tier": "per-user"},
        regions=["ru-central1", "ru-north", "ru-east"],
        description="Identity & access management (Keycloak-based, OAuth2/OIDC/SCIM)",
    ),
    ServiceSpec(
        name="Platform V IDM",
        portfolio="security",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.95%",
        certifications=["FSTEC L3", "GOST"],
        dependencies=["Platform V IAM SE"],
        tags=["identity-management", "provisioning", "governance"],
        cost_model={"monthly_min": 500, "monthly_max": 4000, "pricing_tier": "per-user"},
        regions=["ru-central1"],
        description="Identity lifecycle management and governance",
    ),
    ServiceSpec(
        name="Platform V SOWA",
        portfolio="security",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L4", "GOST", "SOX"],
        dependencies=["Platform V IAM SE"],
        tags=["waf", "api-gateway", "security", "ddos", "rate-limit"],
        cost_model={"monthly_min": 1500, "monthly_max": 10000, "pricing_tier": "per-request"},
        regions=["ru-central1", "ru-north"],
        description="API security gateway with WAF, DDoS protection, and rate limiting",
    ),
    ServiceSpec(
        name="Platform V CryptoService",
        portfolio="security",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L4", "GOST", "HSM"],
        dependencies=["Platform V SberLinux OS Server"],
        tags=["crypto", "encryption", "hsm", "gost", "digital-signature"],
        cost_model={"monthly_min": 800, "monthly_max": 6000, "pricing_tier": "per-operation"},
        regions=["ru-central1"],
        description="Cryptographic operations, key management, and HSM integration (GOST-compliant)",
    ),
    ServiceSpec(
        name="Platform V Audit SE",
        portfolio="security",
        edition=ServiceEdition.SE,
        sla="99.99%",
        certifications=["FSTEC L4", "GOST", "SOX"],
        dependencies=["Platform V IAM SE"],
        tags=["audit", "logging", "compliance", "sox", "monitoring"],
        cost_model={"monthly_min": 400, "monthly_max": 3000, "pricing_tier": "per-event"},
        regions=["ru-central1"],
        description="Centralized audit logging and compliance monitoring",
    ),
    # -- Low-Code / Application Platform (7) --
    ServiceSpec(
        name="Platform V Flow",
        portfolio="low_code",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V IAM SE", "Platform V Container Platform"],
        tags=["bpm", "workflow", "bpmn", "orchestration", "flowable", "camunda"],
        cost_model={"monthly_min": 1000, "monthly_max": 8000, "pricing_tier": "per-process"},
        regions=["ru-central1", "ru-north"],
        description="BPMN 2.0 process orchestration engine (Flowable/Camunda-compatible)",
    ),
    ServiceSpec(
        name="Platform V Studio",
        portfolio="low_code",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.95%",
        certifications=[],
        dependencies=["Platform V IAM SE"],
        tags=["low-code", "ide", "visual", "drag-drop"],
        cost_model={"monthly_min": 300, "monthly_max": 2000, "pricing_tier": "per-user"},
        regions=["ru-central1"],
        description="Visual low-code application designer",
    ),
    ServiceSpec(
        name="Platform V UI Workflow",
        portfolio="low_code",
        edition=ServiceEdition.STANDARD,
        sla="99.9%",
        certifications=[],
        dependencies=["Platform V IAM SE"],
        tags=["ui", "workflow", "forms", "approval"],
        cost_model={"monthly_min": 200, "monthly_max": 1000, "pricing_tier": "per-workflow"},
        regions=["ru-central1"],
        description="UI workflow designer with forms and approval flows",
    ),
    ServiceSpec(
        name="Platform V Functions",
        portfolio="low_code",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.95%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V Container Platform"],
        tags=["faas", "serverless", "functions", "event-driven"],
        cost_model={"monthly_min": 100, "monthly_max": 2000, "pricing_tier": "per-invocation"},
        regions=["ru-central1", "ru-north"],
        description="Serverless FaaS platform (event-driven compute)",
    ),
    ServiceSpec(
        name="Platform V API Mock & Contract Testing",
        portfolio="low_code",
        edition=ServiceEdition.STANDARD,
        sla="99.9%",
        certifications=[],
        dependencies=[],
        tags=["api-mock", "contract-test", "openapi", "stub"],
        cost_model={"monthly_min": 100, "monthly_max": 500, "pricing_tier": "per-api"},
        regions=["ru-central1"],
        description="API mock server and contract testing tool",
    ),
    ServiceSpec(
        name="Platform V Frontend High Load",
        portfolio="low_code",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=[],
        tags=["frontend", "cdn", "high-load", "spa", "ssr"],
        cost_model={"monthly_min": 500, "monthly_max": 4000, "pricing_tier": "per-request"},
        regions=["ru-central1", "ru-north"],
        description="High-load frontend delivery platform with CDN",
    ),
    ServiceSpec(
        name="Platform V Backend",
        portfolio="low_code",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V Container Platform", "Platform V IAM SE"],
        tags=["backend", "runtime", "java", "kotlin", "spring"],
        cost_model={"monthly_min": 500, "monthly_max": 5000, "pricing_tier": "per-instance"},
        regions=["ru-central1"],
        description="Enterprise backend runtime for Java/Kotlin applications",
    ),
    # -- Infrastructure & Runtime (7) --
    ServiceSpec(
        name="Platform V SberLinux OS Server",
        portfolio="infrastructure",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L4", "GOST", "RRPO"],
        dependencies=[],
        tags=["linux", "os", "rhel", "centos", "rpm", "fstec"],
        cost_model={"monthly_min": 100, "monthly_max": 500, "pricing_tier": "per-core"},
        regions=["ru-central1", "ru-north", "ru-east"],
        description="FSTEC-certified enterprise Linux OS (RHEL-compatible)",
    ),
    ServiceSpec(
        name="Platform V Container Platform",
        portfolio="infrastructure",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V SberLinux OS Server"],
        tags=["kubernetes", "k8s", "container", "docker", "openshift"],
        cost_model={"monthly_min": 2000, "monthly_max": 15000, "pricing_tier": "per-cluster"},
        regions=["ru-central1", "ru-north", "ru-east"],
        description="Enterprise Kubernetes container platform",
    ),
    ServiceSpec(
        name="Platform V Starting Manager",
        portfolio="infrastructure",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.95%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V SberLinux OS Server"],
        tags=["orchestration", "deployment", "iaas", "vm"],
        cost_model={"monthly_min": 500, "monthly_max": 3000, "pricing_tier": "per-vm"},
        regions=["ru-central1"],
        description="VM and infrastructure orchestration and deployment",
    ),
    ServiceSpec(
        name="Platform V Monitor",
        portfolio="infrastructure",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V Container Platform"],
        tags=["monitoring", "observability", "prometheus", "grafana", "alerting"],
        cost_model={"monthly_min": 400, "monthly_max": 3000, "pricing_tier": "per-metric"},
        regions=["ru-central1", "ru-north"],
        description="Enterprise observability platform (Prometheus/Grafana-based)",
    ),
    ServiceSpec(
        name="Platform V Configuration",
        portfolio="infrastructure",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.99%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V IAM SE"],
        tags=["config-management", "secrets", "consul", "vault"],
        cost_model={"monthly_min": 300, "monthly_max": 2000, "pricing_tier": "per-config"},
        regions=["ru-central1"],
        description="Centralized configuration and secrets management",
    ),
    ServiceSpec(
        name="Platform V DataTools",
        portfolio="infrastructure",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.95%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V SberLinux OS Server"],
        tags=["data-tools", "migration", "etl", "backup", "restore"],
        cost_model={"monthly_min": 300, "monthly_max": 2000, "pricing_tier": "per-task"},
        regions=["ru-central1"],
        description="Data migration, ETL, and backup/restore toolkit",
    ),
    ServiceSpec(
        name="Platform V Model Execution Framework",
        portfolio="infrastructure",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.95%",
        certifications=["FSTEC L3"],
        dependencies=["Platform V Container Platform"],
        tags=["ml", "model-serving", "inference", "onnx", "triton"],
        cost_model={"monthly_min": 800, "monthly_max": 6000, "pricing_tier": "per-model"},
        regions=["ru-central1"],
        description="ML model serving and inference execution framework",
    ),
    # -- Management Tools (2) --
    ServiceSpec(
        name="Platform V Product 360",
        portfolio="management",
        edition=ServiceEdition.ENTERPRISE,
        sla="99.9%",
        certifications=[],
        dependencies=["Platform V IAM SE"],
        tags=["product-management", "roadmap", "analytics"],
        cost_model={"monthly_min": 500, "monthly_max": 3000, "pricing_tier": "per-user"},
        regions=["ru-central1"],
        description="Product portfolio management and analytics",
    ),
    ServiceSpec(
        name="Platform V Cost Calculator",
        portfolio="management",
        edition=ServiceEdition.STANDARD,
        sla="99.9%",
        certifications=[],
        dependencies=[],
        tags=["cost", "tco", "calculator", "budget"],
        cost_model={"monthly_min": 0, "monthly_max": 200, "pricing_tier": "free"},
        regions=["any"],
        description="TCO and cost estimation calculator for Platform V services",
    ),
]

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

PLATFORM_V_PATTERNS: List[Pattern] = [
    Pattern(
        id="pv_microservices_k8s",
        name="Platform V Microservices on Kubernetes",
        domain="architecture",
        triggers=["microservices", "kubernetes", "k8s", "container", "istio"],
        conditions=[],
        components=["synapse-service-mesh", "container-platform"],
        benefits=["Service mesh (Istio)", "99.99% SLA", "Horizontal scaling"],
        tradeoffs=["K8s ops complexity", "Vendor lock-in risk"],
        priority=9,
        confidence=0.9,
    ),
    Pattern(
        id="pv_low_code_dataspace",
        name="DataSpace Low-Code Backend",
        domain="architecture",
        triggers=["low-code", "nocode", "rapid", "prototype", "ddd", "crud"],
        conditions=[],
        components=["dataspace"],
        benefits=["DDD-driven code gen", "GraphQL API", "RBAC out of box"],
        tradeoffs=["Limited customisation", "Requires Keycloak"],
        priority=8,
        confidence=0.85,
    ),
    Pattern(
        id="pv_bpm_flow",
        name="Flow BPMN 2.0 Orchestration",
        domain="architecture",
        triggers=["bpm", "workflow", "process", "orchestration", "bpmn"],
        conditions=[],
        components=["flow"],
        benefits=["BPMN 2.0 standard", "SLA monitoring", "High throughput"],
        tradeoffs=["BPM modelling skills needed"],
        priority=8,
        confidence=0.85,
    ),
    Pattern(
        id="pv_pangolin_db",
        name="Pangolin Enterprise PostgreSQL",
        domain="data",
        triggers=["postgresql", "rdbms", "sql", "oracle-migration", "1c"],
        conditions=[],
        components=["pangolin"],
        benefits=["PostgreSQL compatible", "FSTEC certified", "80+ enterprise patches"],
        tradeoffs=["PostgreSQL ecosystem only"],
        priority=9,
        confidence=0.95,
    ),
    Pattern(
        id="pv_synapse_esb",
        name="Synapse Integration Platform",
        domain="integration",
        triggers=["esb", "integration", "soa", "ibm-bus", "oracle-esb", "message-broker"],
        conditions=[],
        components=["synapse-app-mesh", "synapse-api-mesh"],
        benefits=["Replaces IBM/Oracle ESB", "Low-code flows", "HTTP/gRPC/Kafka"],
        tradeoffs=["Migration effort from legacy ESB"],
        priority=8,
        confidence=0.85,
    ),
    Pattern(
        id="pv_iam_security",
        name="IAM SE Identity & Access",
        domain="security",
        triggers=["oauth", "oidc", "keycloak", "sso", "scim", "rbac"],
        conditions=[],
        components=["iam-se", "idm"],
        benefits=["OAuth2/OIDC/SCIM", "Keycloak battle-tested", "ESIA integration"],
        tradeoffs=["Keycloak operational cost"],
        priority=9,
        confidence=0.9,
    ),
    Pattern(
        id="pv_import_substitution",
        name="Import Substitution Stack",
        domain="compliance",
        triggers=["import-substitution", "fstec", "gosuslugi", "esia", "реестр"],
        conditions=[],
        components=["sberlinux", "pangolin", "iam-se", "sowa"],
        benefits=["FSTEC certified", "Russian software registry", "Regulatory compliance"],
        tradeoffs=["Ecosystem maturity"],
        priority=10,
        confidence=0.95,
    ),
    Pattern(
        id="pv_works_devops",
        name="Works DevOps Pipeline",
        domain="devops",
        triggers=["devops", "ci-cd", "cicd", "gitlab", "jenkins", "sonarqube"],
        conditions=[],
        components=["works-pipeliner", "works-orchestra-r", "works-codescanner"],
        benefits=["Complete toolchain", "AI-assisted (GigaIDE)", "SBOM/license check"],
        tradeoffs=["Migration from existing CI/CD"],
        priority=7,
        confidence=0.8,
    ),
]

# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------

PLATFORM_V_CONSTRAINTS: Dict[str, List[Constraint]] = {
    "hard": [
        Constraint(
            id="pv_dbms_required",
            name="DBMS Required",
            domain="data_management",
            type="required",
            feature="data_storage",
            operator="exists",
            threshold=True,
            message="Application requires a DBMS — use Platform V Pangolin or Corax",
            fix_hint="Configure a Pangolin or Corax database connection",
            severity="error",
            platforms=["platformv"],
        ),
        Constraint(
            id="pv_os_required",
            name="SberLinux for Production",
            domain="infrastructure",
            type="required",
            feature="operating_system",
            operator="eq",
            threshold="sberlinux",
            message="Production deployments must use SberLinux OS Server for FSTEC certification",
            fix_hint="Set OS to Platform V SberLinux OS Server in deployment config",
            severity="error",
            platforms=["platformv"],
        ),
        Constraint(
            id="pv_iam_required",
            name="IAM Required",
            domain="security",
            type="required",
            feature="authentication",
            operator="exists",
            threshold=True,
            message="All services must authenticate via Platform V IAM SE",
            fix_hint="Integrate IAM SE OAuth2/OIDC client credentials flow",
            severity="error",
            platforms=["platformv"],
        ),
        Constraint(
            id="pv_sowa_api_gateway",
            name="API Gateway Required",
            domain="security",
            type="required",
            feature="api_exposure",
            operator="eq",
            threshold="public",
            message="Public-facing APIs must be behind SOWA gateway",
            fix_hint="Configure SOWA as API gateway with WAF policies",
            severity="error",
            platforms=["platformv"],
        ),
    ],
    "soft": [
        Constraint(
            id="pv_prefer_synapse",
            name="Prefer Synapse for Integration",
            domain="integration",
            type="recommended",
            feature="integration_style",
            operator="exists",
            threshold=True,
            message="Use Synapse over custom integration solutions",
            fix_hint="Migrate integration to Synapse API Mesh or App Mesh",
            severity="warning",
            platforms=["platformv"],
            min_confidence=0.6,
        ),
        Constraint(
            id="pv_prefer_functions",
            name="Prefer Functions for Event-Driven",
            domain="compute",
            type="recommended",
            feature="compute_type",
            operator="eq",
            threshold="event-driven",
            message="Use Platform V Functions for serverless event-driven workloads",
            fix_hint="Refactor to use Platform V Functions (FaaS)",
            severity="warning",
            platforms=["platformv"],
            min_confidence=0.6,
        ),
        Constraint(
            id="pv_prefer_dataspace",
            name="Prefer DataSpace for CRUD Backends",
            domain="development",
            type="recommended",
            feature="development_methodology",
            operator="eq",
            threshold="low-code",
            message="Use DataSpace for rapid DDD-driven backend development",
            fix_hint="Model domain with DataSpace visual DDD designer",
            severity="warning",
            platforms=["platformv"],
            min_confidence=0.6,
        ),
        Constraint(
            id="pv_prefer_flow",
            name="Prefer Flow for BPM",
            domain="process_automation",
            type="recommended",
            feature="development_methodology",
            operator="eq",
            threshold="bpm",
            message="Use Flow for BPMN 2.0 process orchestration",
            fix_hint="Model business processes with Flow BPMN 2.0 designer",
            severity="warning",
            platforms=["platformv"],
            min_confidence=0.6,
        ),
    ],
}

# ---------------------------------------------------------------------------
# Use cases
# ---------------------------------------------------------------------------

PLATFORM_V_USE_CASES: List[UseCase] = [
    UseCase(
        id="uc-pv-application-modernization",
        name="Legacy Application Modernization to Platform V",
        description="Migrate monolithic enterprise applications to Platform V microservices on Container Platform with Synapse service mesh",
        category=UseCaseCategory.OPERATIONS,
        priority=UseCasePriority.CRITICAL,
        platforms=["platformv"],
        patterns=["pv_microservices_k8s", "pv_synapse_esb"],
        technologies=["Kubernetes", "Istio", "Docker"],
        requirements={"orchestration": "synapse-service-mesh", "runtime": "container-platform"},
    ),
    UseCase(
        id="uc-pv-import-substitution",
        name="Import Substitution (Импортозамещение) Stack",
        description="Replace foreign enterprise software with FSTEC-certified Platform V products: Pangolin (DB), SberLinux (OS), IAM SE (auth), CryptoService (crypto)",
        category=UseCaseCategory.COMPLIANCE,
        priority=UseCasePriority.CRITICAL,
        platforms=["platformv"],
        patterns=["pv_import_substitution"],
        technologies=["PostgreSQL", "Linux", "OAuth 2.0", "GOST"],
        requirements={"compliance": "fstec", "os": "sberlinux", "db": "pangolin"},
    ),
    UseCase(
        id="uc-pv-digital-transformation",
        name="Enterprise Digital Transformation on Platform V",
        description="End-to-end digital transformation using Platform V low-code (DataSpace), BPM (Flow), and integration (Synapse) for rapid application delivery",
        category=UseCaseCategory.DEVELOPMENT,
        priority=UseCasePriority.HIGH,
        platforms=["platformv"],
        patterns=["pv_low_code_dataspace", "pv_bpm_flow"],
        technologies=["GraphQL", "BPMN 2.0", "DDD"],
        requirements={"methodology": "low-code", "bpm": True},
    ),
    UseCase(
        id="uc-pv-microservices-migration",
        name="Microservices Migration to Synapse Mesh",
        description="Decompose monolith into microservices connected via Synapse Service Mesh (Istio) with API gateway, observability, and circuit breakers",
        category=UseCaseCategory.OPERATIONS,
        priority=UseCasePriority.HIGH,
        platforms=["platformv"],
        patterns=["pv_microservices_k8s", "pv_synapse_esb"],
        technologies=["Kubernetes", "Istio", "gRPC", "Prometheus"],
        requirements={"service_mesh": True, "observability": True},
    ),
    UseCase(
        id="uc-pv-gosuslugi-integration",
        name="Gosuslugi / ESIA Integration via IAM SE",
        description="Integrate with Russian state services (Госуслуги) and Unified Identification System (ЕСИА) through Platform V IAM SE OAuth2/OIDC bridge",
        category=UseCaseCategory.SECURITY,
        priority=UseCasePriority.HIGH,
        platforms=["platformv"],
        patterns=["pv_iam_security"],
        technologies=["OAuth 2.0", "OIDC", "SAML", "ESIA"],
        requirements={"auth": "esia", "identity_federation": True},
    ),
    UseCase(
        id="uc-pv-1c-migration",
        name="1C Enterprise Migration to Pangolin",
        description="Migrate 1C:Enterprise database workloads to Platform V Pangolin (PostgreSQL-compatible, FSTEC-certified, 1C-optimized)",
        category=UseCaseCategory.INTEGRATION,
        priority=UseCasePriority.MEDIUM,
        platforms=["platformv"],
        patterns=["pv_pangolin_db"],
        technologies=["PostgreSQL", "1C Enterprise"],
        requirements={"db": "pangolin", "compatibility": "1c"},
    ),
    UseCase(
        id="uc-pv-esb-replacement",
        name="Legacy ESB Replacement with Synapse",
        description="Replace IBM WebSphere / Oracle ESB / SAP PI with Platform V Synapse integration platform (API Mesh + App Mesh + Event Replication)",
        category=UseCaseCategory.INTEGRATION,
        priority=UseCasePriority.HIGH,
        platforms=["platformv"],
        patterns=["pv_synapse_esb"],
        technologies=["REST", "gRPC", "Kafka", "SOAP"],
        requirements={"integration_style": "esb", "protocols": ["http", "grpc", "kafka"]},
    ),
    UseCase(
        id="uc-pv-devops-pipeline",
        name="Platform V DevOps Pipeline with Works",
        description="Implement end-to-end CI/CD pipeline using Platform V Works (Pipeliner + CodeScanner + Artifactory + Autotest) with GigaIDE AI-assisted development",
        category=UseCaseCategory.DEVELOPMENT,
        priority=UseCasePriority.MEDIUM,
        platforms=["platformv"],
        patterns=["pv_works_devops"],
        technologies=["GitLab", "Docker", "SonarQube", "Kubernetes"],
        requirements={"cicd": True, "code_scanning": True, "artifact_registry": True},
    ),
]

# ---------------------------------------------------------------------------
# ADRs (Architecture Decision Records)
# ---------------------------------------------------------------------------

PLATFORM_V_ADRS: List[ADR] = [
    ADR(
        id="adr-pv-001",
        title="Use Pangolin as Default RDBMS",
        status=ADRStatus.ACCEPTED,
        context="All new applications on Platform V require a relational database. Must be FSTEC-certified for regulated environments.",
        decision="Use Platform V Pangolin (PostgreSQL-compatible) as the default RDBMS for all applications. Use Corax for read-heavy workloads requiring horizontal scaling.",
        consequences="PostgreSQL ecosystem compatibility, FSTEC certification, but limited to relational workloads. No native NoSQL support.",
        related_patterns=["pv_pangolin_db"],
        related_platforms=["platformv"],
    ),
    ADR(
        id="adr-pv-002",
        title="Use Synapse for All Integration Patterns",
        status=ADRStatus.ACCEPTED,
        context="Enterprise requires a unified integration platform to replace existing IBM WebSphere, Oracle ESB, and SAP PI middleware.",
        decision="Use Platform V Synapse as the single integration platform. Synapse API Mesh for sync APIs, Synapse App Mesh for ESB patterns, Synapse Event Replication for async/event-driven.",
        consequences="Replaces multiple legacy ESBs with one platform, but requires significant migration effort and integration contract renegotiation.",
        related_patterns=["pv_synapse_esb"],
        related_platforms=["platformv"],
    ),
    ADR(
        id="adr-pv-003",
        title="Deploy on SberLinux OS Server for FSTEC",
        status=ADRStatus.ACCEPTED,
        context="Production environments must comply with FSTEC requirements for regulated data (ГосSOP, AS, personal data).",
        decision="All production workloads must run on Platform V SberLinux OS Server. Dev/staging may use alternatives but prod requires SberLinux for FSTEC certification chain.",
        consequences="FSTEC-compliant OS with enterprise support, but limited to RPM-based ecosystem and smaller community compared to Ubuntu/Debian.",
        related_patterns=["pv_import_substitution"],
        related_platforms=["platformv"],
    ),
    ADR(
        id="adr-pv-004",
        title="Use IAM SE for All Authentication",
        status=ADRStatus.ACCEPTED,
        context="Every service needs authentication and authorization. Must support federal standards (GOST, ESIA) and enterprise SSO.",
        decision="Use Platform V IAM SE (Keycloak-based) as the central identity provider. OAuth2/OIDC for service-to-service, ESIA integration for citizen-facing services.",
        consequences="Battle-tested Keycloak with Russian federation support, but Keycloak operational overhead and potential performance bottleneck under high TPS.",
        related_patterns=["pv_iam_security"],
        related_platforms=["platformv"],
    ),
    ADR(
        id="adr-pv-005",
        title="Use DataSpace for DDD-Driven Backend Generation",
        status=ADRStatus.ACCEPTED,
        context="Rapid application development requires a low-code BaaS approach with DDD support and auto-generated GraphQL APIs.",
        decision="Use Platform V DataSpace for new CRUD backends. Model domain via visual DDD designer, generate Kotlin/Java services with auto GraphQL, RBAC, and Swagger.",
        consequences="Fast time-to-market for CRUD services, but limited customization for complex business logic and Kotlin ecosystem dependency.",
        related_patterns=["pv_low_code_dataspace"],
        related_platforms=["platformv"],
    ),
    ADR(
        id="adr-pv-006",
        title="Use Flow for BPMN 2.0 Process Orchestration",
        status=ADRStatus.ACCEPTED,
        context="Enterprise requires BPMN 2.0 standard process orchestration with SLA monitoring, human task management, and integration with Synapse.",
        decision="Use Platform V Flow for all business process orchestration. Design processes in BPMN 2.0, integrate with Synapse for service calls, monitor via Flow's SLA dashboard.",
        consequences="BPMN 2.0 standard compliance with high throughput, but requires BPMN modelling skills and process governance.",
        related_patterns=["pv_bpm_flow"],
        related_platforms=["platformv"],
    ),
    ADR(
        id="adr-pv-007",
        title="Place All Public APIs Behind SOWA Gateway",
        status=ADRStatus.ACCEPTED,
        context="Public-facing APIs need WAF protection, rate limiting, DDoS protection, and integration with federal monitoring systems.",
        decision="All public-facing APIs must be deployed behind Platform V SOWA (Safe Operation Web Application) gateway for WAF, rate limiting, and security monitoring.",
        consequences="Enterprise-grade API security with WAF/SOX compliance, but adds latency and operational overhead for API management.",
        related_patterns=["pv_iam_security", "pv_import_substitution"],
        related_platforms=["platformv"],
    ),
    ADR(
        id="adr-pv-008",
        title="Use CryptoService for All Cryptographic Operations",
        status=ADRStatus.ACCEPTED,
        context="Applications need GOST-compliant cryptographic operations, key management, and HSM integration for regulated environments.",
        decision="Use Platform V CryptoService for all cryptographic operations including key generation, encryption, digital signatures, and HSM integration. GOST R 34.10-2012 and 34.11-2012 supported.",
        consequences="GOST-compliant cryptography with HSM support, but adds network dependency on CryptoService and potential latency for crypto operations.",
        related_patterns=["pv_import_substitution"],
        related_platforms=["platformv"],
    ),
]

# ---------------------------------------------------------------------------
# Reference Architectures
# ---------------------------------------------------------------------------

PLATFORM_V_REF_ARCHS: List[ReferenceArchitecture] = [
    ReferenceArchitecture(
        id="ref-pv-microservices-synapse",
        name="Microservices on Synapse Service Mesh",
        type=ReferenceArchitectureType.MICROSERVICES,
        description="Containerized microservices on Platform V Container Platform with Synapse Service Mesh (Istio), API gateway, and observability stack",
        platforms=["platformv"],
        components=[
            "Platform V Container Platform",
            "Platform V Synapse Service Mesh",
            "Platform V Synapse API Mesh",
            "Platform V Monitor",
            "Platform V IAM SE",
            "Platform V Works::Pipeliner",
        ],
        data_flow=[
            "Client → SOWA → Synapse API Mesh → Synapse Service Mesh → Microservice → Pangolin",
        ],
        quality_attributes={
            "scalability": "Horizontal (HPA via K8s)",
            "availability": "99.99%",
            "security": "FSTEC-certified, IAM SE auth",
            "latency": "<10ms mesh overhead",
        },
    ),
    ReferenceArchitecture(
        id="ref-pv-import-substitution",
        name="Import Substitution Stack (Импортозамещение)",
        type=ReferenceArchitectureType.API_GATEWAY,
        description="Complete FSTEC-certified stack replacing foreign enterprise software with Platform V products",
        platforms=["platformv"],
        components=[
            "Platform V SberLinux OS Server",
            "Platform V Pangolin",
            "Platform V IAM SE",
            "Platform V CryptoService",
            "Platform V SOWA",
            "Platform V Audit SE",
        ],
        data_flow=[
            "Client → SOWA (WAF) → Application → Pangolin (DB), IAM SE (Auth), CryptoService (Crypto)",
        ],
        quality_attributes={
            "compliance": "FSTEC, РРПО, 152-ФЗ",
            "security": "GOST crypto, ESIA-ready",
            "availability": "99.99%",
            "support": "SberTech enterprise support",
        },
    ),
    ReferenceArchitecture(
        id="ref-pv-goscloud",
        name="GosCloud-Compliant Deployment (ГосОблако)",
        type=ReferenceArchitectureType.HYBRID_INTEGRATION,
        description="Deployment architecture compliant with Russian government cloud (ГосОблако) requirements, integrating Platform V with Gosuslugi and federal systems",
        platforms=["platformv"],
        components=[
            "Platform V IAM SE (ESIA integration)",
            "Platform V SOWA",
            "Platform V Audit SE",
            "Platform V SberLinux OS Server",
            "Platform V CryptoService",
        ],
        data_flow=[
            "Citizen → Gosuslugi → ESIA → IAM SE → Application → Pangolin / CryptoService",
        ],
        quality_attributes={
            "compliance": "ГосСОПКА, 152-ФЗ, ФЗ-63",
            "integration": "ESIA, SMEV, SEDO",
            "audit": "Full audit trail",
            "certification": "FSTEC/FSSK certified",
        },
    ),
    ReferenceArchitecture(
        id="ref-pv-1c-enterprise",
        name="1C Enterprise on Pangolin",
        type=ReferenceArchitectureType.DATA_PIPELINE,
        description="Migration and operation of 1C:Enterprise workloads on Platform V Pangolin with performance tuning for 1C query patterns",
        platforms=["platformv"],
        components=[
            "Platform V Pangolin",
            "Platform V SberLinux OS Server",
            "Platform V Monitor",
            "Platform V Batch",
            "Platform V DataTools",
        ],
        data_flow=[
            "1C Client → 1C Server → Pangolin (1C-optimized queries) → Backup / DataTools",
        ],
        quality_attributes={
            "compatibility": "Full 1C 8.3 support",
            "performance": "1C-optimized query planner",
            "availability": "99.99% (Pangolin HA)",
            "migration": "Built-in 1C migration toolkit",
        },
    ),
]

# ---------------------------------------------------------------------------
# Platform knowledge registration
# ---------------------------------------------------------------------------

_KNOwLEDGE_REGISTERED = False


def register_platform_knowledge() -> None:
    """Register Platform V knowledge entities (use cases, ADRs, ref archs)
    into the global repositories and knowledge graph.

    Idempotent — safe to call multiple times.
    """
    global _KNOwLEDGE_REGISTERED
    if _KNOwLEDGE_REGISTERED:
        return
    _KNOwLEDGE_REGISTERED = True

    graph = get_knowledge_graph()
    use_case_repo = get_use_case_repository()
    adr_repo = get_adr_repository()
    ref_arch_repo = get_reference_architecture_repository()

    # Add Platform V platform node if not already present (registry adds it
    # too but we need it now for edge creation before registration).
    if not graph.get_node("platformv"):
        graph.add_node(
            KnowledgeNode(
                id="platformv",
                name="Platform V",
                type=NodeType.PLATFORM,
                properties={
                    "keywords": [
                        "sbertech", "sber", "platform v", "gosuslugi", "esia",
                        "fstec", "import substitution", "1c",
                    ],
                },
            )
        )

    # Register use cases
    for uc in PLATFORM_V_USE_CASES:
        use_case_repo.add(uc)
        graph.add_node(
            KnowledgeNode(
                id=uc.id,
                name=uc.name,
                type=NodeType.USE_CASE,
                properties={
                    "category": uc.category.value,
                    "priority": uc.priority.value,
                },
            )
        )
        graph.add_edge(
            KnowledgeEdge(source_id="platformv", target_id=uc.id, type=EdgeType.IMPLEMENTS)
        )

    # Register ADRs
    for adr in PLATFORM_V_ADRS:
        adr_repo.add(adr)
        graph.add_node(
            KnowledgeNode(
                id=adr.id,
                name=adr.title,
                type=NodeType.DECISION,
                properties={"status": adr.status.value},
            )
        )
        graph.add_edge(
            KnowledgeEdge(source_id="platformv", target_id=adr.id, type=EdgeType.IMPLEMENTS)
        )

    # Register reference architectures
    for ref in PLATFORM_V_REF_ARCHS:
        ref_arch_repo.add(ref)
        graph.add_node(
            KnowledgeNode(
                id=ref.id,
                name=ref.name,
                type=NodeType.REFERENCE_ARCH,
                properties={"type": ref.type.value},
            )
        )
        graph.add_edge(
            KnowledgeEdge(source_id="platformv", target_id=ref.id, type=EdgeType.COMPOSED_OF)
        )

    # Register constraint set with the constraint engine
    constraint_engine = get_constraint_engine()
    all_constraints = PLATFORM_V_CONSTRAINTS["hard"] + PLATFORM_V_CONSTRAINTS["soft"]
    constraint_engine.register_constraint_set(
        ConstraintSet(
            id="platformv",
            name="Platform V Constraints",
            description="Hard and soft constraints for Platform V deployments",
            constraints=all_constraints,
        )
    )

    # Register patterns
    from core.patterns.schema import get_pattern_library

    library = get_pattern_library()
    for p in PLATFORM_V_PATTERNS:
        library.register(p)

    # Register DEPENDS_ON edges between services from the catalog
    for spec in PLATFORM_V_SERVICE_CATALOG:
        for dep_name in spec.dependencies:
            # Both nodes should exist by this point (registered in AdapterRegistry)
            if graph.get_node(spec.name) and graph.get_node(dep_name):
                graph.add_edge(
                    KnowledgeEdge(
                        source_id=spec.name,
                        target_id=dep_name,
                        type=EdgeType.DEPENDS_ON,
                        weight=1.0,
                    )
                )

# ---------------------------------------------------------------------------
# IR feature → Platform V product mapping
# ---------------------------------------------------------------------------

_IR_TO_PRODUCT: Dict[str, List[Dict[str, Any]]] = {
    "data_storage": [
        {"value": "relational", "product": "Platform V Pangolin", "config": "pangolin", "confidence": 0.95},
        {"value": "document", "product": "Platform V Pangolin", "config": "pangolin", "confidence": 0.85},
        {"value": "key-value", "product": "Platform V DataGrid", "config": "datagrid", "confidence": 0.9},
        {"value": "in-memory", "product": "Platform V DataGrid", "config": "datagrid", "confidence": 0.95},
        {"value": "search", "product": "Platform V Index Search", "config": None, "confidence": 0.9},
        {"value": "mdm", "product": "Platform V Dictionaries", "config": "dictionaries", "confidence": 0.9},
        {"value": "message-broker", "product": "Platform V Corax", "config": None, "confidence": 0.9},
        {"value": "streaming", "product": "Platform V Corax", "config": None, "confidence": 0.85},
        {"value": "cluster", "product": "Platform V Grid Center", "config": None, "confidence": 0.85},
        {"value": "db-admin", "product": "Platform V Kintsugi", "config": None, "confidence": 0.8},
    ],
    "compute_type": [
        {"value": "serverless", "product": "Platform V Functions", "config": "functions", "confidence": 0.9},
        {"value": "container", "product": "Platform V Container Platform", "config": "k8s", "confidence": 0.95},
        {"value": "batch", "product": "Platform V Batch", "config": None, "confidence": 0.9},
        {"value": "stateful", "product": "Platform V Backend", "config": None, "confidence": 0.75},
        {"value": "provisioning", "product": "Platform V Starting Manager", "config": None, "confidence": 0.8},
    ],
    "integration_style": [
        {"value": "async", "product": "Platform V Synapse Event Replication", "config": "synapse", "confidence": 0.9},
        {"value": "event-driven", "product": "Platform V Synapse Event Replication", "config": "synapse", "confidence": 0.95},
        {"value": "sync", "product": "Platform V Synapse API Mesh", "config": "synapse", "confidence": 0.85},
        {"value": "message-broker", "product": "Platform V Synapse Messaging", "config": None, "confidence": 0.9},
        {"value": "esb", "product": "Platform V Synapse App Mesh", "config": "synapse", "confidence": 0.95},
        {"value": "service-mesh", "product": "Platform V Synapse Service Mesh", "config": "synapse", "confidence": 0.95},
        {"value": "file-exchange", "product": "Platform V Synapse File Exchange", "config": None, "confidence": 0.85},
        {"value": "sftp", "product": "Platform V Synapse File Exchange", "config": None, "confidence": 0.9},
        {"value": "webhook", "product": "Platform V Synapse API Mesh", "config": "synapse", "confidence": 0.8},
    ],
    "development_methodology": [
        {"value": "low-code", "product": "Platform V DataSpace", "config": None, "confidence": 0.9},
        {"value": "bpm", "product": "Platform V Flow", "config": None, "confidence": 0.95},
        {"value": "agile", "product": "Platform V Works::TaskTracker", "config": None, "confidence": 0.85},
        {"value": "devops", "product": "Platform V Works::Pipeliner", "config": None, "confidence": 0.85},
        {"value": "low-code, studio", "product": "Platform V Studio", "config": None, "confidence": 0.8},
        {"value": "low-code, frontend", "product": "Platform V UI Workflow", "config": None, "confidence": 0.85},
        {"value": "frontend", "product": "Platform V Frontend High Load", "config": None, "confidence": 0.8},
        {"value": "api-testing", "product": "Platform V API Mock", "config": None, "confidence": 0.85},
        {"value": "contract", "product": "Platform V API Mock", "config": None, "confidence": 0.8},
    ],
    "security_level": [
        {"value": "high", "product": "Platform V IAM SE", "config": "iam", "confidence": 0.95},
        {"value": "high", "product": "Platform V SOWA", "config": None, "confidence": 0.9},
        {"value": "high", "product": "Platform V CryptoService", "config": None, "confidence": 0.9},
        {"value": "standard", "product": "Platform V IAM SE", "config": "iam", "confidence": 0.85},
        {"value": "standard", "product": "Platform V One Time Tokens", "config": None, "confidence": 0.8},
        {"value": "service-auth", "product": "Platform V One Time Tokens", "config": None, "confidence": 0.9},
    ],
    "compliance": [
        {"value": "fstec", "product": "Platform V SberLinux OS Server", "config": None, "confidence": 0.95},
        {"value": "fstec", "product": "Platform V Pangolin", "config": "pangolin", "confidence": 0.95},
        {"value": "gosuslugi", "product": "Platform V IAM SE", "config": "iam", "confidence": 0.95},
        {"value": "import-substitution", "product": "Platform V SberLinux OS Server", "config": None, "confidence": 0.95},
        {"value": "audit", "product": "Platform V Audit SE", "config": None, "confidence": 0.9},
        {"value": "soc2", "product": "Platform V Audit SE", "config": None, "confidence": 0.7},
    ],
    "analytics": [
        {"value": "streaming", "product": "Platform V DataGrid", "config": "datagrid", "confidence": 0.85},
        {"value": "ml", "product": "Platform V Model Execution Framework", "config": None, "confidence": 0.8},
        {"value": "monitoring", "product": "Platform V Monitor", "config": None, "confidence": 0.9},
        {"value": "ai", "product": "Platform V Synapse AI", "config": None, "confidence": 0.85},
        {"value": "ml", "product": "Platform V Synapse AI", "config": None, "confidence": 0.8},
        {"value": "nlp", "product": "Platform V Synapse AI", "config": None, "confidence": 0.75},
    ],
    "workload_language": [
        {"value": "java", "product": "Platform V Works::GigaIDE Cloud", "config": None, "confidence": 0.7},
        {"value": "kotlin", "product": "Platform V DataSpace", "config": None, "confidence": 0.8},
        {"value": "1c", "product": "Platform V Pangolin", "config": "pangolin", "confidence": 0.9},
        {"value": "python", "product": "Platform V GigaCode", "config": None, "confidence": 0.75},
        {"value": "javascript", "product": "Platform V GigaCode", "config": None, "confidence": 0.75},
        {"value": "typescript", "product": "Platform V GigaCode", "config": None, "confidence": 0.75},
    ],
}


def _irfeature_to_feature_dict(features: Any) -> Dict[str, str]:
    """Translate structured IRFeature fields into the dict keys _IR_TO_PRODUCT expects.

    This bridge function preserves the existing product-mapping table without
    requiring it to be rewritten for the IRFeature model.
    """
    fd: Dict[str, str] = {}

    if getattr(features, "has_database", None):
        fd["data_storage"] = "relational"
    if getattr(features, "has_async", None) or getattr(features, "has_event_driven", None):
        fd["integration_style"] = "async, event-driven"
    if getattr(features, "has_auth", None):
        fd["security_level"] = "high"
    if getattr(features, "has_microservices", None):
        fd["integration_style"] = "service-mesh, microservice"
    if getattr(features, "has_serverless", None):
        fd["compute_type"] = "serverless"
    if getattr(features, "has_container", None):
        fd["compute_type"] = "container"
    if getattr(features, "has_batch", None):
        fd["compute_type"] = "batch"
    if getattr(features, "has_ui", None):
        fd["development_methodology"] = "low-code"
    if getattr(features, "has_api", None):
        fd["integration_style"] = "sync, api"
    if getattr(features, "has_ui", None):
        fd["development_methodology"] = (fd.get("development_methodology", "") + ", frontend, low-code, ui").strip(", ")
    if getattr(features, "has_audit", None):
        fd["compliance"] = (fd.get("compliance", "") + ", audit").strip(", ")
    if getattr(features, "has_ai", None) or getattr(features, "has_ml", None):
        fd["analytics"] = (fd.get("analytics", "") + ", ai, ml").strip(", ")
    if getattr(features, "has_message_queue", None):
        fd["data_storage"] = (fd.get("data_storage", "") + ", message-broker, streaming").strip(", ")

    # Map compliance requirements and data classification into the
    # compliance / security_level feature keys.
    compliance_reqs = getattr(features, "compliance_requirements", None) or []
    if compliance_reqs:
        fd["compliance"] = ", ".join(compliance_reqs)

    data_class = getattr(features, "data_classification", "")
    if data_class and data_class != "internal":
        fd["security_level"] = fd.get("security_level", "") + ", " + data_class

    # Map the explicit fstec_level into the compliance feature key.
    if getattr(features, "fstec_level", None):
        fd["compliance"] = (fd.get("compliance", "") + ", fstec").strip(", ")

    return fd


def _find_product_by_ir(features: Any) -> List[Dict[str, Any]]:
    """Match IR features against the product mapping.

    Accepts both ``IRFeature`` instances (preferred) and plain dicts for
    backward compatibility.  When an ``IRFeature`` is passed the translation
    is handled by :func:`_irfeature_to_feature_dict`.
    """
    if hasattr(features, "model_dump") and not isinstance(features, dict):
        feature_dict = _irfeature_to_feature_dict(features)
    else:
        feature_dict = features if isinstance(features, dict) else {}

    matched: List[Dict[str, Any]] = []
    seen_products: set = set()

    for feature_key, mappings in _IR_TO_PRODUCT.items():
        feature_value = feature_dict.get(feature_key)
        if feature_value is None:
            continue
        feature_str = str(feature_value).lower()

        for mapping in mappings:
            if mapping["value"] in feature_str and mapping["product"] not in seen_products:
                matched.append(mapping)
                seen_products.add(mapping["product"])

    return matched


# ---------------------------------------------------------------------------
# IAM SE Auth Client
# ---------------------------------------------------------------------------


@dataclass
class IAMToken:
    """Cached OAuth2 token from IAM SE."""

    access_token: str
    refresh_token: str = ""
    expires_at: float = 0.0

    @property
    def expired(self) -> bool:
        return time.monotonic() >= self.expires_at

    @property
    def valid(self) -> bool:
        return bool(self.access_token) and not self.expired


class IAMAuthClient:
    """OAuth2 client credentials flow against Platform V IAM SE (Keycloak).

    Caches tokens and auto-refreshes on expiry.

    Usage::

        auth = IAMAuthClient(
            token_url="https://iam.platformv.internal/auth/realms/myrealm/protocol/openid-connect/token",
            client_id="my-service",
            client_secret="...",
        )
        headers = auth.get_headers()  # {"Authorization": "Bearer <token>"}
    """

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scopes: str = "",
        timeout: float = 10.0,
    ) -> None:
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes
        self.timeout = timeout
        self._token: Optional[IAMToken] = None

    def _fetch_token(self) -> IAMToken:
        """Call the Keycloak token endpoint with client_credentials grant."""
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        if self.scopes:
            data["scope"] = self.scopes

        resp = requests.post(
            self.token_url,
            data=data,
            timeout=self.timeout,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        body = resp.json()

        expires_in = body.get("expires_in", 300)
        return IAMToken(
            access_token=body["access_token"],
            refresh_token=body.get("refresh_token", ""),
            expires_at=time.monotonic() + expires_in - 30,  # 30s safety buffer
        )

    def get_token(self) -> IAMToken:
        """Return a valid token, fetching or refreshing as needed."""
        if self._token is None or self._token.expired:
            self._token = self._fetch_token()
        return self._token

    def get_headers(self) -> Dict[str, str]:
        """Return HTTP headers with a valid Bearer token."""
        token = self.get_token()
        return {"Authorization": f"Bearer {token.access_token}"}


# ---------------------------------------------------------------------------
# API Client stubs
# ---------------------------------------------------------------------------


class PlatformVClient:
    """Base HTTP client for Platform V product APIs.

    All products authenticate through the same IAM SE token.
    Override ``base_url`` in subclasses for specific product endpoints.
    """

    def __init__(self, auth: IAMAuthClient, base_url: str = "", timeout: float = 10.0) -> None:
        self.auth = auth
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> requests.Response:
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {})
        headers.update(self.auth.get_headers())
        return self._session.request(method, url, headers=headers, timeout=self.timeout, **kwargs)

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("DELETE", path, **kwargs)


class DataSpaceClient(PlatformVClient):
    """GraphQL client for DataSpace CE (open-source BaaS).

    API docs: https://gitverse.ru/sbertech/dataspace-ce
    """

    def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GraphQL query against DataSpace."""
        payload: Dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables
        resp = self.post("/graphql", json=payload)
        resp.raise_for_status()
        return resp.json()

    def introspect_schema(self) -> Dict[str, Any]:
        """Retrieve the auto-generated GraphQL schema from the DDD model."""
        query = """
        query Introspect {
            __schema {
                types { name fields { name type { name } } }
            }
        }
        """
        return self.execute_query(query)


class FlowClient(PlatformVClient):
    """REST client for Platform V Flow BPMN 2.0 engine.

    Follows standard BPM engine REST API (Flowable / Camunda compatible).
    """

    def deploy_process(self, bpmn_xml: str, deployment_name: str = "") -> Dict[str, Any]:
        """Deploy a BPMN 2.0 process definition."""
        files = {"file": ("process.bpmn20.xml", bpmn_xml, "text/xml")}
        resp = self.post("/repository/deployments", files=files)
        resp.raise_for_status()
        return resp.json()

    def start_process_instance(self, process_definition_key: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Start a new process instance by definition key."""
        resp = self.post("/runtime/process-instances", json={
            "processDefinitionKey": process_definition_key,
            "variables": variables,
        })
        resp.raise_for_status()
        return resp.json()

    def query_tasks(self, **filters: Any) -> List[Dict[str, Any]]:
        """Query active tasks with optional filters."""
        resp = self.get("/runtime/tasks", params=filters)
        resp.raise_for_status()
        return resp.json().get("data", [])

    def get_process_history(self, process_instance_id: str) -> Dict[str, Any]:
        """Get historic details for a process instance."""
        resp = self.get(f"/history/historic-process-instances/{process_instance_id}")
        resp.raise_for_status()
        return resp.json()


class SynapseMeshClient(PlatformVClient):
    """Client for Synapse Service Mesh (enterprise Istio).

    Exposes Istio APIs for traffic management, security, and observability.
    """

    def get_virtual_services(self, namespace: str = "") -> List[Dict[str, Any]]:
        """List Istio VirtualServices."""
        params = {"namespace": namespace} if namespace else {}
        resp = self.get("/apis/networking.istio.io/v1/virtualservices", params=params)
        resp.raise_for_status()
        return resp.json().get("items", [])

    def get_service_graph(self, namespace: str = "") -> Dict[str, Any]:
        """Retrieve the service dependency graph from the mesh."""
        params = {"namespace": namespace} if namespace else {}
        resp = self.get("/api/v1/servicegraph", params=params)
        resp.raise_for_status()
        return resp.json()


class WorksClient(PlatformVClient):
    """Client for Platform V Works development platform.

    Covers the full DevOps toolchain: source control, CI/CD pipelines,
    code scanning, artifact management, and test automation.

    API compatible with GitLab and Jira REST APIs where applicable.
    """

    def list_projects(self, search: str = "") -> List[Dict[str, Any]]:
        """List Works projects (analogous to GitLab groups/projects)."""
        params = {"search": search} if search else {}
        resp = self.get("/api/v4/projects", params=params)
        resp.raise_for_status()
        return resp.json()

    def trigger_pipeline(self, project_id: str, ref: str = "main") -> Dict[str, Any]:
        """Trigger a CI/CD pipeline in a Works project."""
        resp = self.post(f"/api/v4/projects/{project_id}/pipeline", json={"ref": ref})
        resp.raise_for_status()
        return resp.json()

    def run_code_scan(self, project_id: str, branch: str = "") -> Dict[str, Any]:
        """Run static code analysis via Works CodeScanner (SonarQube-compatible)."""
        params = {"branch": branch} if branch else {}
        resp = self.post(f"/api/v4/projects/{project_id}/scan", params=params)
        resp.raise_for_status()
        return resp.json()

    def list_artifacts(self, project_id: str) -> List[Dict[str, Any]]:
        """List binary artifacts in Works Artifactory."""
        resp = self.get(f"/api/v4/projects/{project_id}/packages")
        resp.raise_for_status()
        return resp.json()

    def get_pipeline_status(self, project_id: str, pipeline_id: str) -> Dict[str, Any]:
        """Get the status of a specific pipeline."""
        resp = self.get(f"/api/v4/projects/{project_id}/pipelines/{pipeline_id}")
        resp.raise_for_status()
        return resp.json()


class SOWAClient(PlatformVClient):
    """Client for Platform V SOWA (Safe Operation Web Application) gateway.

    Provides WAF, rate limiting, DDoS protection, and API security monitoring.
    """

    def list_policies(self) -> List[Dict[str, Any]]:
        """List WAF and security policies."""
        resp = self.get("/api/v1/policies")
        resp.raise_for_status()
        return resp.json()

    def create_waf_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Create a WAF rule for request filtering."""
        resp = self.post("/api/v1/waf/rules", json=rule)
        resp.raise_for_status()
        return resp.json()

    def get_traffic_stats(self, since: str = "1h") -> Dict[str, Any]:
        """Get traffic statistics (requests, blocked, top sources)."""
        resp = self.get("/api/v1/stats/traffic", params={"since": since})
        resp.raise_for_status()
        return resp.json()

    def list_rate_limits(self) -> List[Dict[str, Any]]:
        """List configured rate limiting rules."""
        resp = self.get("/api/v1/rate-limits")
        resp.raise_for_status()
        return resp.json()


class MonitorClient(PlatformVClient):
    """Client for Platform V Monitor observability platform.

    Metrics, alerting, log aggregation, and dashboards.
    """

    def query_metrics(self, query: str, time_range: str = "1h") -> Dict[str, Any]:
        """Query metrics (PromQL-compatible)."""
        resp = self.get("/api/v1/query", params={"query": query, "time_range": time_range})
        resp.raise_for_status()
        return resp.json()

    def list_alerts(self, status: str = "") -> List[Dict[str, Any]]:
        """List active alerts, optionally filtered by status."""
        params = {"status": status} if status else {}
        resp = self.get("/api/v1/alerts", params=params)
        resp.raise_for_status()
        return resp.json()

    def create_dashboard(self, name: str, panels: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a monitoring dashboard with specified panels."""
        resp = self.post("/api/v1/dashboards", json={"name": name, "panels": panels})
        resp.raise_for_status()
        return resp.json()

    def get_logs(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Search logs (Lucene query syntax)."""
        resp = self.get("/api/v1/logs", params={"query": query, "limit": limit})
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

RECOMMENDATION_THRESHOLD = 0.5


class PlatformVAdapter(RecommendationMixin, PlatformAdapter):
    """Platform V adapter for SberTech enterprise PaaS.

    Follows the same interface as SAP BTP, AWS, Azure, GCP, Tanzu, and Power
    Platform adapters.  Provides IR-to-platform mapping, config template
    generation, and code snippet generation.
    """

    def __init__(self) -> None:
        super().__init__()
        self._auth: Optional[IAMAuthClient] = None
        register_platform_knowledge()

    # -- Auth lifecycle (injected post-construction) ------------------------

    def configure_auth(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scopes: str = "",
    ) -> None:
        """Configure the IAM SE OAuth2 client credentials flow."""
        self._auth = IAMAuthClient(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
        )

    @property
    def auth(self) -> IAMAuthClient:
        if self._auth is None:
            raise RuntimeError(
                "IAM auth not configured. Call configure_auth() first."
            )
        return self._auth

    def get_client(self, base_url: str) -> PlatformVClient:
        """Return a generic authenticated client."""
        return PlatformVClient(auth=self.auth, base_url=base_url)

    def get_dataspace_client(self, base_url: str) -> DataSpaceClient:
        """Return an authenticated DataSpace GraphQL client."""
        return DataSpaceClient(auth=self.auth, base_url=base_url)

    def get_flow_client(self, base_url: str) -> FlowClient:
        """Return an authenticated Flow BPM client."""
        return FlowClient(auth=self.auth, base_url=base_url)

    def get_synapse_client(self, base_url: str) -> SynapseMeshClient:
        """Return an authenticated Synapse client."""
        return SynapseMeshClient(auth=self.auth, base_url=base_url)

    def get_works_client(self, base_url: str) -> WorksClient:
        """Return an authenticated Works DevOps client."""
        return WorksClient(auth=self.auth, base_url=base_url)

    def get_sowa_client(self, base_url: str) -> SOWAClient:
        """Return an authenticated SOWA security gateway client."""
        return SOWAClient(auth=self.auth, base_url=base_url)

    def get_monitor_client(self, base_url: str) -> MonitorClient:
        """Return an authenticated Monitor observability client."""
        return MonitorClient(auth=self.auth, base_url=base_url)

    # -- PlatformAdapter interface ------------------------------------------

    @property
    def platform_id(self) -> str:
        return "platformv"

    @property
    def supported_services(self) -> List[str]:
        return PLATFORM_V_SERVICES

    @property
    def service_catalog(self) -> List[ServiceSpec]:
        return PLATFORM_V_SERVICE_CATALOG

    @property
    def patterns(self) -> List[Pattern]:
        return PLATFORM_V_PATTERNS

    @property
    def constraints(self) -> Dict[str, List[Constraint]]:
        return PLATFORM_V_CONSTRAINTS

    @property
    def use_cases(self) -> List[UseCase]:
        return get_use_case_repository().find_by_platform("platformv")

    @property
    def architecture_decision_records(self) -> List[ADR]:
        return get_adr_repository().find_by_platform("platformv")

    @property
    def reference_architectures(self) -> List[ReferenceArchitecture]:
        return get_reference_architecture_repository().find_by_platform("platformv")

    def transform_ir_to_platform(self, input: AdapterInput) -> AdapterOutput:
        features = input.ir_features
        pattern_results = input.pattern_matches
        violations = input.constraint_violations

        # -- 1. Config & code generation (template-standard) ----------------
        config_templates = self.generate_config(features)
        code_snippets = self.generate_code(features)
        deployment_manifests: Dict[str, str] = {}

        # -- 2. Build recommendations ---------------------------------------
        recommendations: List[Dict[str, Any]] = []
        selected_service_names: List[str] = []

        # 2a. IR-feature-to-product matching (Platform V specific)
        matched_products = _find_product_by_ir(features)
        for m in matched_products:
            product = m["product"]
            recommendations.append({
                "name": product,
                "reason": self._product_purpose(product),
                "confidence": m["confidence"],
                "score": m["confidence"],
                "portfolio": PRODUCT_PORTFOLIO.get(product, "other"),
            })
            selected_service_names.append(product)

            # Associate config/code/manifest with specific matched products
            if m["config"] == "pangolin":
                config_templates["pangolin"] = self._generate_pangolin_config()
            elif m["config"] == "synapse":
                config_templates["synapse"] = self._generate_synapse_config()
            elif m["config"] == "iam":
                config_templates["iam"] = self._generate_iam_config()
            elif m["config"] == "functions":
                code_snippets["function.py"] = self._generate_functions_example()
            elif m["config"] == "k8s":
                deployment_manifests["deployment.yaml"] = self._generate_k8s_manifest()

        # 2b. Pattern-based recommendations (template-standard, via mixin)
        pattern_recs = self._build_recommendations(pattern_results, features, violations)
        for pr in pattern_recs:
            pr_name = pr.get("name", "")
            if pr_name and pr_name not in selected_service_names:
                selected_service_names.append(pr_name)
            if pr not in recommendations:
                recommendations.append(pr)

        # 2c. Fallback defaults when nothing matched
        if not recommendations:
            default_services = [
                "Platform V Pangolin",
                "Platform V Synapse Service Mesh",
                "Platform V IAM SE",
            ]
            for svc in default_services:
                recommendations.append({
                    "name": svc,
                    "reason": self._product_purpose(svc),
                    "confidence": 0.7,
                    "score": 0.7,
                    "portfolio": PRODUCT_PORTFOLIO.get(svc, "other"),
                })
                selected_service_names.append(svc)

        # -- 3. Confidence & deployability (template-standard) ----------------
        can_deploy = not any(getattr(v, "severity", "") == "error" for v in violations)
        confidences = [
            r.get("score") or r.get("confidence", 0.0)
            for r in recommendations
            if r.get("score") or r.get("confidence")
        ]
        confidence = sum(confidences) / max(1, len(confidences)) if confidences else 0.7

        # -- 4. Enhanced structured output (template-standard) --------------
        required_dependencies = self.resolve_dependencies(selected_service_names)
        catalog_map = {s.name: s for s in self.service_catalog}
        all_service_names = list(dict.fromkeys(selected_service_names + required_dependencies))
        service_specs = [catalog_map[name] for name in all_service_names if name in catalog_map]
        compliance_matrix = self.compute_compliance(features, all_service_names)
        cost_estimate = self.estimate_cost(features, all_service_names)
        portfolio_summary = summarize_portfolios(service_specs)

        # -- 5. Explanation (template-standard _explain + Platform V detail)
        explanation = self._generate_explanation(
            features, recommendations, pattern_results, violations
        )

        return AdapterOutput(
            recommendations=recommendations[:10],
            config_templates=config_templates,
            code_snippets=code_snippets,
            deployment_manifests=deployment_manifests,
            explanation=explanation,
            confidence=round(confidence, 2),
            can_deploy=can_deploy,
            platform=self.platform_id,
            service_specs=service_specs,
            compliance_matrix=compliance_matrix,
            cost_estimate=cost_estimate,
            required_dependencies=required_dependencies,
            portfolio_summary=portfolio_summary,
        )

    def generate_config(self, features: Any) -> Dict[str, str]:
        return {
            "pangolin.yaml": self._generate_pangolin_config(),
            "synapse.yaml": self._generate_synapse_config(),
            "iam.yaml": self._generate_iam_config(),
        }

    def generate_code(self, features: Any) -> Dict[str, str]:
        return {
            "function.py": self._generate_functions_example(),
            "deployment.yaml": self._generate_k8s_manifest(),
        }

    # -- Internal helpers ---------------------------------------------------

    @staticmethod
    def _product_purpose(product: str) -> str:
        purposes: Dict[str, str] = {
            "Platform V Pangolin": "Enterprise PostgreSQL RDBMS with 80+ security patches",
            "Platform V DataGrid": "In-memory distributed data grid (Apache Ignite SE)",
            "Platform V Dictionaries": "MDM reference data management",
            "Platform V DataSpace": "Low-code DDD-driven BaaS (GraphQL)",
            "Platform V Functions": "FaaS serverless computing",
            "Platform V Synapse Service Mesh": "Istio-based microservice mesh",
            "Platform V Synapse API Mesh": "Centralized API management gateway",
            "Platform V Synapse App Mesh": "Distributed ESB for enterprise integration",
            "Platform V Synapse Event Replication": "Event streaming and replication",
            "Platform V Synapse Messaging": "Message broker",
            "Platform V Flow": "BPMN 2.0 process orchestration",
            "Platform V IAM SE": "Identity & access management (OAuth2/OIDC)",
            "Platform V SOWA": "API security gateway and WAF",
            "Platform V CryptoService": "Cryptographic operations and key management",
            "Platform V SberLinux OS Server": "FSTEC-certified enterprise Linux",
            "Platform V Works::TaskTracker": "Agile task and backlog management",
            "Platform V Works::Pipeliner": "CI/CD pipeline orchestration",
            "Platform V Works::CodeScanner": "Static code analysis and license compliance",
            "Platform V Works::Artifactory": "Binary and container image registry",
        }
        return purposes.get(product, f"Platform V service: {product}")

    # -- Template generators (existing, kept as-is) -------------------------

    @staticmethod
    def _generate_pangolin_config() -> str:
        return """# Platform V Pangolin configuration
# PostgreSQL-compatible enterprise database (FSTEC certified)

DATABASE_CONFIG:
  host: pangolin.platformv.internal
  port: 5432
  database: app_db
  user: ${DB_USER}
  password: ${DB_PASSWORD}

  ssl_mode: require
  encryption: transparent
  audit_enabled: true

  replication:
    mode: async
    replicas: 2

  pool:
    min_connections: 10
    max_connections: 100
    idle_timeout: 300
"""

    @staticmethod
    def _generate_synapse_config() -> str:
        return """# Platform V Synapse integration configuration

SYNAPSE_CONFIG:
  api_gateway:
    host: synapse.platformv.internal
    port: 8080
    tls_enabled: true

  event_processing:
    enabled: true
    streams:
      - name: appEvents
        partitions: 3
        retention: 7d

  service_mesh:
    enabled: true
    load_balancing: round_robin
    circuit_breaker:
      enabled: true
      threshold: 5
"""

    @staticmethod
    def _generate_iam_config() -> str:
        return """# Platform V IAM SE configuration
# OAuth2/OIDC identity provider (Keycloak-based)

IAM_CONFIG:
  idp:
    url: https://iam.platformv.internal/auth
    realm: myrealm
    oidc_enabled: true
    oauth2_enabled: true

  users:
    password_policy:
      min_length: 12
      require_uppercase: true
      require_lowercase: true
      require_numbers: true
      require_special: true
      two_factor_required: true

  rbac:
    roles:
      - admin
      - developer
      - operator
      - viewer

  audit:
    enabled: true
    log_all_actions: true
    retention_days: 365
"""

    @staticmethod
    def _generate_functions_example() -> str:
        return '''# Platform V Functions example (FaaS)

from platformv.functions import handler, Event


@handler(event_type="http")
def process_http_request(event: Event) -> dict:
    """HTTP-triggered function."""
    return {
        "status": 200,
        "body": {"message": "Hello from Platform V!"}
    }


@handler(event_type="timer")
def scheduled_task(event: Event) -> None:
    """Timer-triggered function (cron)."""
    print("Scheduled task executed")
'''

    @staticmethod
    def _generate_k8s_manifest() -> str:
        return """# Platform V Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: platformv
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: registry.platformv.internal/myapp:v1
        ports:
        - containerPort: 8080
        resources:
          limits:
            cpu: "2"
            memory: 4Gi
          requests:
            cpu: "500m"
            memory: 1Gi
        env:
        - name: ENVIRONMENT
          value: production
        - name: PLATFORMV_ENDPOINT
          value: https://platformv.internal
---
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
"""

    def _generate_explanation(
        self,
        features: Any,
        recommendations: List[Dict[str, Any]],
        pattern_results: Any = None,
        violations: Any = None,
    ) -> str:
        # Start with the mixin's standard _explain summary
        parts: List[str] = [self._explain(recommendations, violations)]

        parts.append(
            "Platform V (SberTech) is a Russian enterprise PaaS platform with 55+ products."
            " FSTEC-certified, registered in РРПО, 99.99% fault tolerance."
        )

        if recommendations:
            rec_names = [r.get("name", "Unknown") for r in recommendations[:3]]
            parts.append(f"Recommended: {', '.join(rec_names)}.")

        portfolios = sorted({r.get("portfolio", "other") for r in recommendations if r.get("name")})
        if portfolios:
            parts.append("Portfolios: " + ", ".join(portfolios) + ".")

        if violations:
            errors = [v for v in violations if getattr(v, "severity", "") == "error"]
            if errors:
                parts.append(f"Blocking issues: {len(errors)} — fix before deploy.")
            warnings = [v for v in violations if getattr(v, "severity", "") == "warning"]
            if warnings:
                parts.append(f"Recommendations: {len(warnings)}.")

        if pattern_results:
            parts.append(f"Pattern matches: {len(pattern_results)}.")
            top_pattern = max(pattern_results, key=lambda p: getattr(p, "match_score", 0))
            pattern_name = getattr(getattr(top_pattern, "pattern", None), "name", "")
            if pattern_name:
                parts.append(f"Best pattern: {pattern_name}.")

        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def get_platform_v_adapter() -> PlatformVAdapter:
    """Return a standalone Platform V adapter instance."""
    return PlatformVAdapter()


def register_platform_v_adapter(registry: Any) -> None:
    """Register Platform V adapter with an AdapterRegistry."""
    registry.register(PlatformVAdapter())
