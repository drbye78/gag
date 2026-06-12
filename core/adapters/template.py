"""Platform adapter template - copy to core/adapters/ to create new platform adapter."""

from typing import Any, Dict, List

from core.adapters.base import AdapterInput, AdapterOutput, PlatformAdapter
from core.adapters.mixins import RecommendationMixin
from core.adapters.models import ServiceEdition, ServiceSpec, summarize_portfolios
from core.constraints.engine import get_constraint_engine
from core.patterns.schema import Pattern, get_pattern_library


class MyPlatformAdapter(RecommendationMixin, PlatformAdapter):
    """Platform adapter for MyPlatform - provides reasoning and generation capabilities."""

    def __init__(self) -> None:
        super().__init__()

    @property
    def platform_id(self) -> str:
        return "myplatform"

    @property
    def supported_services(self) -> List[str]:
        return ["service1", "service2", "service3"]

    @property
    def service_catalog(self) -> List[ServiceSpec]:
        return [
            ServiceSpec(name="service1", portfolio="compute", edition=ServiceEdition.STANDARD, sla="99.9%", tags=["tag1"], description="Service 1 description"),
            ServiceSpec(name="service2", portfolio="data", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["tag2"], description="Service 2 description"),
            ServiceSpec(name="service3", portfolio="security", edition=ServiceEdition.ENTERPRISE, sla="99.95%", tags=["tag3"], description="Service 3 description"),
        ]

    @property
    def patterns(self) -> List[Pattern]:
        library = get_pattern_library()
        patterns = [
            Pattern(
                id="myplatform_pattern1",
                name="MyPlatform Pattern 1",
                domain="architecture",
                triggers=["trigger1", "trigger2"],
                conditions=[],
                components=["component1", "component2"],
                benefits=["Benefit 1", "Benefit 2"],
                tradeoffs=["Tradeoff 1"],
                priority=8,
                confidence=0.85,
            ),
        ]
        for p in patterns:
            library.register(p)
        return patterns

    @property
    def constraints(self) -> Any:
        return get_constraint_engine()._constraint_sets.get("myplatform")

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
        return {}

    def generate_code(self, features=None) -> Dict[str, str]:
        return {}
