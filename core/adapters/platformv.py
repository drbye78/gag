"""Platform V (Платформа V) adapter — SberTech's on-premises enterprise platform.

Platform V is SberTech's FSTEC-certified on-premises/private-cloud platform for
Russian critical infrastructure. Not Cloud.ru Evolution — this is the bare-metal
private-cloud suite with products like SberLinux, DropApp, Kintsugi, Pangolin DB,
IAM SE, IDM, SOWA, and IAM Proxy.
"""

from typing import Any, Dict, List

from core.adapters.base import AdapterInput, AdapterOutput, AdapterRegistry, PlatformAdapter
from core.adapters.mixins import RecommendationMixin
from core.constraints.engine import ConstraintViolation, get_constraint_engine
from core.patterns.schema import Pattern, get_pattern_library
from models.ir import IRFeature


class PlatformVAdapter(RecommendationMixin, PlatformAdapter):
    """SberTech Platform V — on-premises enterprise platform for Russian critical infrastructure.

    All products are FSTEC-certified. Deployment is on-premises/private cloud only.
    This is NOT Cloud.ru Evolution — it is the bare-metal private cloud product suite:

    - SberLinux OS Server: RPM-based Linux OS (FSTEC #4884)
    - DropApp: Kubernetes-based container orchestration, Go operators (FSTEC #4883)
    - Kintsugi: Istio-based service mesh (mTLS, Egress Gateway)
    - Pangolin DB: Secure DBMS with Oracle/PostgreSQL/MS SQL/DB2 migration (FSTEC #4704)
    - IAM SE: Auth/AuthZ, SSO, OpenID Connect, JWT (FSTEC #4999)
    - IDM: Centralized identity lifecycle management, SCIM protocol
    - SOWA: API gateway, WAF, AI-Guardrails for LLM prompt injection prevention
    - IAM Proxy: OpenID Connect-based per-service authentication proxy
    """

    # ── adapter identity ────────────────────────────────────────────────

    @property
    def platform_id(self) -> str:
        return "platformv"

    @property
    def supported_services(self) -> list[str]:
        """Load services from YAML config if available, else use defaults."""
        from core.adapters.config_loader import get_config_loader

        loader = get_config_loader()
        services = loader.load_services("platformv")
        if services:
            result: list[str] = []
            for category_services in services.values():
                result.extend(category_services)
            return sorted(set(result))
        # Fallback — 8 certified on-premises products
        return [
            "sberlinux",
            "dropapp",
            "kintsugi",
            "pangolindb",
            "iam-se",
            "idm",
            "sowa",
            "iam-proxy",
        ]

    # ── patterns ────────────────────────────────────────────────────────

    @property
    def patterns(self) -> list[Pattern]:
        library = get_pattern_library()

        platformv_patterns = [
            Pattern(
                id="platformv_microservice_mesh",
                name="Microservices with Service Mesh",
                domain="microservices",
                triggers=["has_microservices", "has_container"],
                components=["dropapp", "kintsugi", "iam-se", "iam-proxy"],
                benefits=[
                    "Istio mTLS between all DropApp services",
                    "Centralized IAM authentication via IAM SE",
                    "Per-service auth proxy via IAM Proxy",
                    "FSTEC-certified Kubernetes operators",
                ],
                tradeoffs=[
                    "Requires SberLinux OS hosts",
                    "On-premises hardware required — no SaaS option",
                ],
                priority=9,
                confidence=0.95,
            ),
            Pattern(
                id="platformv_secure_api_gateway",
                name="Secure API Gateway Pattern",
                domain="api",
                triggers=["has_api"],
                components=["sowa", "iam-se", "iam-proxy"],
                benefits=[
                    "WAF protection for all API endpoints",
                    "AI-Guardrails for LLM prompt injection prevention",
                    "OpenID Connect authentication via IAM SE",
                    "Per-service IAM Proxy for defense in depth",
                ],
                tradeoffs=[
                    "Additional hop for auth proxy per service",
                    "On-premises deployment only",
                ],
                priority=9,
                confidence=0.93,
            ),
            Pattern(
                id="platformv_database_migration",
                name="Database Migration to Pangolin DB",
                domain="data",
                triggers=["has_database"],
                components=["pangolindb"],
                benefits=[
                    "FSTEC-certified secure DBMS",
                    "Migration from Oracle, PostgreSQL, MS SQL, DB2",
                    "ANSI SQL standard compliance",
                    "Suitable for КИИ (critical infrastructure)",
                ],
                tradeoffs=[
                    "Migration effort depends on source DBMS",
                    "FSTEC-certification workflow adds process overhead",
                ],
                priority=9,
                confidence=0.91,
            ),
            Pattern(
                id="platformv_os_migration",
                name="OS Migration to SberLinux",
                domain="platform",
                triggers=["has_container"],
                components=["sberlinux"],
                benefits=[
                    "RPM-compatible with RHEL migration paths",
                    "Proven at scale — 43,000+ servers migrated from RHEL",
                    "FSTEC certified operating system",
                ],
                tradeoffs=[
                    "Requires RPM-based packaging",
                    "Hardware compatibility audit needed",
                ],
                priority=9,
                confidence=0.94,
            ),
        ]

        for p in platformv_patterns:
            library.register(p)

        return platformv_patterns

    # ── constraints ─────────────────────────────────────────────────────

    @property
    def constraints(self) -> Any:
        return get_constraint_engine()._constraint_sets.get("platformv")

    # ── main transform ──────────────────────────────────────────────────

    def transform_ir_to_platform(self, input: AdapterInput) -> AdapterOutput:
        features = input.ir_features
        pattern_results = input.pattern_matches
        violations = input.constraint_violations

        config_templates = self.generate_config(features)
        code_snippets = self.generate_code(features)

        recommendations = self._build_recommendations(
            pattern_results,
            features,
            violations,
        )

        # Append platform-specific migration/deployment hints
        if features.has_container or features.has_microservices:
            recommendations.append({
                "name": "DropApp + Kintsugi Deployment",
                "reason": "Kubernetes-based orchestration with Istio mTLS service mesh (Go operators)",
                "services": ["dropapp", "kintsugi"],
                "fstec_certified": ["4883", "4884"],
            })

        if features.has_database:
            recommendations.append({
                "name": "Pangolin DB Migration",
                "reason": "FSTEC-certified DBMS — migrate from Oracle/PostgreSQL/MS SQL/DB2",
                "services": ["pangolindb"],
                "fstec_certified": "4704",
            })

        if features.has_api:
            recommendations.append({
                "name": "SOWA API Security",
                "reason": "API Gateway + WAF with AI-Guardrails for LLM prompt injection prevention",
                "services": ["sowa"],
            })

        # IAM SE is required for every Platform V deployment
        recommendations.append({
            "name": "IAM SE Centralized Auth",
            "reason": "Platform V requires centralized IAM (OpenID Connect, JWT, SSO)",
            "services": ["iam-se", "idm"],
            "fstec_certified": "4999",
        })

        can_deploy = not any(v.severity == "error" for v in violations)
        confidence = sum(p.match_score for p in pattern_results) / max(1, len(pattern_results))

        return AdapterOutput(
            recommendations=recommendations,
            config_templates=config_templates,
            code_snippets=code_snippets,
            explanation=self._explain(recommendations, violations),
            confidence=confidence,
            can_deploy=can_deploy,
            platform="platformv",
            metadata={
                "deployment_model": "on-premises",
                "fstec_certified": True,
                "os": "sberlinux-os-server",
                "orchestrator": "dropapp (kubernetes)",
                "service_mesh": "kintsugi (istio)",
                "sanctions_notice": "SberTech is under US/EU sanctions since 2022",
                "documentation": "auth-gated at platformv.sbertech.ru",
                "note": "Platform V (Платформа V) — NOT Cloud.ru Evolution",
            },
        )

    # ── generate config / code ──────────────────────────────────────────

    def generate_config(self, features: IRFeature) -> dict[str, str]:
        configs: dict[str, str] = {}

        if features.has_container or features.has_microservices:
            configs["deployment.yaml"] = _DEPLOYMENT_YAML
            configs["virtualservice.yaml"] = _VIRTUAL_SERVICE_YAML

        if features.has_api:
            configs["sowa-gateway.yaml"] = _SOWA_GATEWAY_YAML

        if features.has_database:
            configs["pangolindb-binding.yaml"] = _PANGOLINDB_BINDING_YAML

        configs["README.md"] = _README_MD

        return configs

    def generate_code(self, features: IRFeature) -> dict[str, str]:
        code: dict[str, str] = {}

        if features.has_api or features.has_container:
            code["main.go"] = _GO_MAIN
            code["go.mod"] = _GO_MOD

        return code


# ── Config & code templates ─────────────────────────────────────────────

_DEPLOYMENT_YAML = """# Platform V — DropApp Kubernetes Deployment
# FSTEC-certified on-premises container orchestration (FSTEC #4883)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  labels:
    app: platform-v-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: platform-v-app
  template:
    metadata:
      labels:
        app: platform-v-app
      annotations:
        sidecar.istio.io/inject: "true"
    spec:
      containers:
      - name: app
        image: registry.platformv.local/app:latest
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: "250m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
"""

_VIRTUAL_SERVICE_YAML = """# Platform V — Kintsugi VirtualService (Istio-based service mesh)
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: app-vs
spec:
  hosts:
  - app.platformv.local
  gateways:
  - kintsugi-gateway
  http:
  - route:
    - destination:
        host: app
        port:
          number: 8080
"""

_SOWA_GATEWAY_YAML = """# Platform V — SOWA API Gateway + WAF configuration
# AI-Guardrails enabled for LLM prompt injection prevention
apiVersion: platformv.sbertech.ru/v1
kind: SOWAGateway
metadata:
  name: app-gateway
spec:
  routes:
    - path: /api/
      backend: app
      waf: enabled
      aiGuardrails:
        enabled: true
        injectionPrevention: strict
  auth:
    provider: iam-se
    protocol: openid-connect
"""

_PANGOLINDB_BINDING_YAML = """# Platform V — Pangolin DB binding (FSTEC #4704)
# Supports migration from: Oracle, PostgreSQL, MS SQL Server, DB2
apiVersion: platformv.sbertech.ru/v1
kind: DatabaseBinding
metadata:
  name: app-db
spec:
  service: pangolindb
  instance:
    cpu: 2
    memory: 4Gi
    disk: 50Gi
  database: appdb
  extensions:
    - ansi-sql
"""

_README_MD = '''# Platform V Deployment Guide

## Products Used
- **SberLinux OS Server** — RPM-based Linux OS (FSTEC #4884)
- **DropApp** — Kubernetes container orchestration (FSTEC #4883)
- **Kintsugi** — Istio-based service mesh (mTLS, Egress Gateway)
- **Pangolin DB** — FSTEC-certified DBMS (FSTEC #4704)
- **IAM SE** — Centralized auth (OpenID Connect, JWT, SSO) (FSTEC #4999)
- **SOWA** — API Gateway + WAF with AI-Guardrails

## Prerequisites
- SberLinux OS Server installed (RPM-based, see migration guide for RHEL → SberLinux)
- DropApp Kubernetes cluster provisioned
- Kintsugi service mesh enabled
- IAM SE configured for the organization
- Pangolin DB instance created (migrate from existing DBMS if needed)

## Deployment
```bash
kubectl apply -f deployment.yaml
kubectl apply -f virtualservice.yaml
```

## Security
- All service-to-service traffic encrypted via Istio mTLS (Kintsugi)
- Authentication via IAM SE (OpenID Connect / JWT)
- API security via SOWA WAF with AI-Guardrails
- All products FSTEC-certified for КИИ/ГИС workloads
'''

_GO_MAIN = '''// Platform V Application — Go service for DropApp / Kintsugi deployment
package main

import (
    "fmt"
    "net/http"
)

func handler(w http.ResponseWriter, r *http.Request) {
    fmt.Fprintf(w, "Platform V Application")
}

func main() {
    http.HandleFunc("/", handler)
    http.ListenAndServe(":8080", nil)
}
'''

_GO_MOD = """module platformv.example.com/app

go 1.21
"""


# ── registration helper ─────────────────────────────────────────────────

def register_platformv_adapter(registry: AdapterRegistry | None = None) -> None:
    """Register Platform V adapter in the given or global registry."""
    if registry:
        registry.register(PlatformVAdapter())
