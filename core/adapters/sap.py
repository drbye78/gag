from typing import Any, Dict, List, Optional
from core.adapters.base import AdapterInput, AdapterOutput, PlatformAdapter, AdapterRegistry, get_adapter_registry
from core.patterns.schema import Pattern, get_pattern_library
from core.constraints.engine import get_constraint_engine
from models.ir import IRFeature, PlatformContext


class SAPBTPAdapter(PlatformAdapter):
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
        
        recommendations = self._build_recommendations(
            pattern_results,
            features,
            violations
        )
        
        can_deploy = not any(
            v.severity == "error" for v in violations
        )
        
        confidence = sum(p.match_score for p in pattern_results) / max(1, len(pattern_results))
        
        return AdapterOutput(
            recommendations=recommendations,
            config_templates=config_templates,
            code_snippets=code_snippets,
            explanation=self._explain(recommendations, violations),
            confidence=confidence,
            can_deploy=can_deploy,
        )
    
    def generate_config(self, features: IRFeature) -> Dict[str, str]:
        configs = {}
        
        if features.has_auth:
            configs["xsuaa.json"] = self._generate_xsuaa_config()
        
        configs["mta.yaml"] = self._generate_mta_yaml(features)
        
        configs["package.json"] = self._generate_package_json()
        
        if features.has_serverless:
            configs["kyma-function.yaml"] = self._generate_kyma_config()
        
        return configs
    
    def generate_code(self, features: IRFeature) -> Dict[str, str]:
        code = {}
        
        code["package.json"] = self._generate_package_json()
        
        if features.has_api:
            code["srv/cat-service.cds"] = self._generate_cds_definition()
        
        return code
    
    def _generate_xsuaa_config(self) -> str:
        return '''{
  "xsappname": "my-app",
  "tenant-mode": "dedicated",
  "scopes": [
    {
      "name": "$XSAPPNAME.Admin",
      "description": "Admin scope"
    }
  ],
  "role-templates": [
    {
      "name": "Admin",
      "scope-references": ["$XSAPPNAME.Admin"]
    }
  ]
}'''
    
    def _generate_mta_yaml(self, features: IRFeature) -> str:
        return f'''_schema-version: "3.1"
ID: my-app
version: 1.0.0

parameters:
  enable-parallel-deployments: true

resources:
  - name: my-app-destination
    type: destination
    parameters:
      service-instance-name: my-destination
  - name: my-app-xsuaa
    type: xsuaa
    parameters:
      service-instance-name: my-xsuaa

modules:
  - name: my-app-srv
    type: nodejs
    path: srv
    requires:
      - name: my-app-destination
      - name: my-app-xsuaa
    provides:
      - name: srv-api
        properties:
          url: "{{{{ mfUrl }}}}"

  - name: my-app-app
    type: html5
    path: app
    requires:
      - name: srv-api
        properties:
          app-endpoints: "{{{{ srv-api.url }}}}"
'''
    
    def _generate_package_json(self) -> str:
        return '''{
  "name": "my-sap-cap-app",
  "version": "1.0.0",
  "scripts": {
    "start": "cds-serve"
  },
  "dependencies": {
    "@sap/cds": "^7"
  },
  "cds": {
    "requires": {
      "db": {
        "kind": "hana"
      }
    }
  }
}'''
    
    def _generate_cds_definition(self) -> str:
        return '''using { managed } from '@sap/cds-common';

entity MyEntity {
  key ID : UUID;
  name : String;
  description : String;
  createdAt : Timestamp;
  createdBy : String;
}
using MyEntity as service;'''
    
    def _generate_kyma_config(self) -> str:
        return '''apiVersion: serverless.kyma-project.io/v1alpha1
kind: Function
metadata:
  name: my-function
spec:
  runtime: nodejs18
  source: |
    module.exports = { main: async function (event, context) {
      return { message: 'Hello SAP Kyma!' };
    }}
'''
    
    def _build_recommendations(
        self,
        pattern_results: List[Any],
        features: IRFeature,
        violations: List[Any]
    ) -> List[Dict[str, Any]]:
        recommendations = []
        
        for pattern_result in pattern_results[:3]:
            pattern = getattr(pattern_result, "pattern", None)
            if pattern:
                recommendations.append({
                    "name": pattern.name,
                    "reason": f"Matched {len(pattern_result.matched_conditions)} conditions",
                    "score": pattern_result.match_score,
                })
        
        for violation in violations:
            recommendations.append({
                "name": "Fix Required",
                "reason": violation.message,
                "severity": violation.severity,
                "fix": violation.fix_hint,
            })
        
        return recommendations
    
    def _explain(
        self,
        recommendations: List[Dict[str, Any]],
        violations: List[Any]
    ) -> str:
        parts = []
        
        if recommendations:
            best = recommendations[0]
            parts.append(f"Recommended: {best.get('name', 'Unknown')}")
        
        if violations:
            errors = [v for v in violations if v.severity == "error"]
            if errors:
                parts.append(f"Blocking issues: {len(errors)}")
        
        return " | ".join(parts) if parts else "Analysis complete"


_adapter_registry: Optional[AdapterRegistry] = None


def get_adapter_registry() -> AdapterRegistry:
    global _adapter_registry
    if _adapter_registry is None:
        _adapter_registry = AdapterRegistry()
        _adapter_registry.register(SAPBTPAdapter())
    return _adapter_registry