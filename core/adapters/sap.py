from typing import Any, Dict, List

from core.adapters.base import (
    AdapterInput,
    AdapterOutput,
    PlatformAdapter,
)
from core.adapters.mixins import RecommendationMixin
from core.adapters.models import ServiceEdition, ServiceSpec, summarize_portfolios
from core.constraints.engine import get_constraint_engine
from core.patterns.schema import Pattern, get_pattern_library
from models.ir import IRFeature


class SAPBTPAdapter(RecommendationMixin, PlatformAdapter):
    @property
    def platform_id(self) -> str:
        return "sap"

    @property
    def supported_services(self) -> List[str]:
        return [
            "xsuaa",
            "identity",
            "hana",
            "hdi-container",
            "destination",
            "connectivity",
            "workflow",
            "mta",
            "approuter",
            "business-logic",
            "destination",
            "object-store",
            "auditlog",
        ]

    @property
    def service_catalog(self) -> List[ServiceSpec]:
        return [
            ServiceSpec(name="xsuaa", portfolio="security", edition=ServiceEdition.ENTERPRISE, sla="99.99%", certifications=["SOC2", "ISO 27001"], tags=["auth", "oauth", "jwt"], description="SAP XSUAA authentication service"),
            ServiceSpec(name="identity", portfolio="security", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["iam", "sso", "identity"], description="SAP Identity Authentication"),
            ServiceSpec(name="hana", portfolio="data", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["database", "in-memory", "sql"], description="SAP HANA in-memory database"),
            ServiceSpec(name="hdi-container", portfolio="data", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["database", "hdi", "containers"], description="SAP HANA Deployment Infrastructure"),
            ServiceSpec(name="destination", portfolio="integration", edition=ServiceEdition.ENTERPRISE, sla="99.95%", tags=["destination", "connectivity", "proxy"], description="SAP Destination service"),
            ServiceSpec(name="connectivity", portfolio="integration", edition=ServiceEdition.ENTERPRISE, sla="99.95%", tags=["connectivity", "proxy", "on-premise"], description="SAP Connectivity service"),
            ServiceSpec(name="workflow", portfolio="process", edition=ServiceEdition.ENTERPRISE, sla="99.95%", tags=["workflow", "bpm", "automation"], description="SAP Workflow service"),
            ServiceSpec(name="mta", portfolio="deployment", edition=ServiceEdition.ENTERPRISE, sla="99.9%", tags=["deployment", "multi-target", "archive"], description="SAP Multi-Target Application"),
            ServiceSpec(name="approuter", portfolio="runtime", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["router", "proxy", "gateway"], description="SAP AppRouter"),
            ServiceSpec(name="business-logic", portfolio="runtime", edition=ServiceEdition.ENTERPRISE, sla="99.95%", tags=["business", "rules", "logic"], description="SAP Business Logic service"),
            ServiceSpec(name="object-store", portfolio="data", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["storage", "object", "blob"], description="SAP Object Store"),
            ServiceSpec(name="auditlog", portfolio="security", edition=ServiceEdition.ENTERPRISE, sla="99.95%", certifications=["SOC2"], tags=["audit", "logging"], description="SAP Audit Log service"),
        ]

    @property
    def patterns(self) -> List[Pattern]:
        library = get_pattern_library()

        sap_patterns = [
            Pattern(
                id="sap_cap_mta",
                name="SAP CAP (Cloud Application Programming)",
                domain="architecture",
                triggers=["cap", "cds", "mta"],
                conditions=[],
                components=["db", "srv", "app"],
                benefits=["OData", "Type-safe", "Multi-target", "CDS"],
                tradeoffs=["CAP learning curve"],
                priority=9,
                confidence=0.85,
            ),
            Pattern(
                id="sap_cf_app",
                name="Cloud Foundry Application",
                domain="architecture",
                triggers=["cf", "cloudfoundry"],
                conditions=[],
                components=["manifest.yml", "approuter"],
                benefits=["Managed runtime", "Auto-scaling", "Services"],
                tradeoffs=["Vendor lock-in"],
                priority=8,
                confidence=0.8,
            ),
            Pattern(
                id="sap_kyma",
                name="SAP Kyma Runtime",
                domain="architecture",
                triggers=["kyma", "lambda", "eventing", "serverless"],
                conditions=[],
                components=["function", "eventing"],
                benefits=["Serverless", "Event-driven", "SAP integration"],
                tradeoffs=["Kyma complexity"],
                priority=8,
                confidence=0.75,
            ),
            Pattern(
                id="sap_approuter",
                name="SAP AppRouter",
                domain="architecture",
                triggers=["approuter", "xsuaa"],
                conditions=[],
                components=["approuter", "xsuaa"],
                benefits=["Authentication", "Multi-tenant"],
                tradeoffs=["Configuration complexity"],
                priority=9,
                confidence=0.9,
            ),
        ]

        for p in sap_patterns:
            library.register(p)

        return sap_patterns

    @property
    def constraints(self) -> Any:
        return get_constraint_engine()._constraint_sets.get("sap_btp")

    def transform_ir_to_platform(self, input: AdapterInput) -> AdapterOutput:
        features = input.ir_features
        pattern_results = input.pattern_matches
        violations = input.constraint_violations

        config_templates = self.generate_config(features)
        code_snippets = self.generate_code(features)

        recommendations = self._build_recommendations(pattern_results, features, violations)

        can_deploy = not any(v.severity == "error" for v in violations)
        confidence = sum(p.match_score for p in pattern_results) / max(1, len(pattern_results))

        selected = [r.get("name", "") for r in recommendations if r.get("name")]
        catalog_map = {s.name: s for s in self.service_catalog}
        service_specs = [catalog_map[name] for name in selected if name in catalog_map]
        compliance_matrix = self.compute_compliance(features, selected)
        cost_estimate = self.estimate_cost(features, selected)
        required_dependencies = self.resolve_dependencies(selected)

        return AdapterOutput(
            recommendations=recommendations,
            config_templates=config_templates,
            code_snippets=code_snippets,
            explanation=self._explain(recommendations, violations),
            confidence=confidence,
            can_deploy=can_deploy,
            platform=self.platform_id,
            service_specs=service_specs,
            compliance_matrix=compliance_matrix,
            cost_estimate=cost_estimate,
            required_dependencies=required_dependencies,
            portfolio_summary=summarize_portfolios(service_specs),
        )

    def generate_config(self, features=None) -> Dict[str, str]:
        configs = {}

        if features and features.has_auth:
            configs["xsuaa.json"] = self._generate_xsuaa_config(features)

        configs["mta.yaml"] = self._generate_mta_yaml(features)

        configs["package.json"] = self._generate_package_json(features)

        if features and features.has_serverless:
            configs["kyma-function.yaml"] = self._generate_kyma_config(features)

        return configs

    def generate_code(self, features: IRFeature) -> Dict[str, str]:
        code = {}

        code["package.json"] = self._generate_package_json()

        if features.has_api:
            code["srv/cat-service.cds"] = self._generate_cds_definition()

        return code

    def _generate_xsuaa_config(self, features=None) -> str:
        app_name = features.app_name if features and features.app_name else "my-app"
        return f'''{{
  "xsappname": "{app_name}",
  "tenant-mode": "dedicated",
  "scopes": [
    {{
      "name": "$XSAPPNAME.Admin",
      "description": "Admin scope"
    }}
  ],
  "role-templates": [
    {{
      "name": "Admin",
      "scope-references": ["$XSAPPNAME.Admin"]
    }}
  ]
}}'''

    def _generate_mta_yaml(self, features=None) -> str:
        app_name = features.app_name if features and features.app_name else "my-app"
        return f"""_schema-version: "3.1"
ID: {app_name}
version: 1.0.0

parameters:
  enable-parallel-deployments: true

resources:
  - name: {app_name}-destination
    type: destination
    parameters:
      service-instance-name: my-destination
  - name: {app_name}-xsuaa
    type: xsuaa
    parameters:
      service-instance-name: my-xsuaa

modules:
  - name: {app_name}-srv
    type: nodejs
    path: srv
    requires:
      - name: {app_name}-destination
      - name: {app_name}-xsuaa
    provides:
      - name: srv-api
        properties:
          url: "{{{{ mfUrl }}}}"

  - name: {app_name}-app
    type: html5
    path: app
    requires:
      - name: srv-api
        properties:
          app-endpoints: "{{{{ srv-api.url }}}}"
"""

    def _generate_package_json(self, features=None) -> str:
        app_name = features.app_name if features and features.app_name else "my-sap-cap-app"
        return f'''{{
  "name": "{app_name}",
  "version": "1.0.0",
  "scripts": {{
    "start": "cds-serve"
  }},
  "dependencies": {{
    "@sap/cds": "^7"
  }},
  "cds": {{
    "requires": {{
      "db": {{
        "kind": "hana"
      }}
    }}
  }}
}}'''

    def _generate_kyma_config(self, features=None) -> str:
        app_name = features.app_name if features and features.app_name else "my-function"
        return f"""apiVersion: serverless.kyma-project.io/v1alpha1
kind: Function
metadata:
  name: {app_name}
spec:
  runtime: nodejs18
  source: |
    module.exports = {{ main: async function (event, context) {{
      return {{ message: 'Hello SAP Kyma!' }};
    }}}}
"""
