from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from core.knowledge.graph import EdgeType, NodeType, get_knowledge_graph

# ---------------------------------------------------------------------------
# Canonical platform detection keywords — single source of truth.
# Every consumer (retrieval, resolver, etc.) MUST import from here rather than
# maintaining its own copy.
# ---------------------------------------------------------------------------
PLATFORM_DETECT_KEYWORDS: Dict[str, List[str]] = {
    "sap": ["xsuaa", "hana", "btp", "cap", "cloudfoundry", "kyma", "cf"],
    "salesforce": ["sf", "salesforce", "lightning", "apex", "visualforce"],
    "powerplatform": ["powerapps", "powerautomate", "powerpages", "dataverse", "dax"],
    "tanzu": ["tanzu", "pivotal", "spring", "cf", "kubernetes"],
    "aws": ["lambda", "s3", "dynamodb", "iam", "ec2", "ecs"],
    "azure": ["azure", "function", "app service", "cosmos", "aks"],
    "gcp": ["gcp", "cloud", "gke", "firestore", "cloudfunctions"],
    "platformv": [
        "platform v", "sbertech", "sber", "pangolin",
        "dataspace", "synapse", "sberlinux", "gigacode",
        "gigaide", "datagrid", "sowa", "goway", "sowa",
        "1с", "1c", "гостех", "gosuslugi", "esia",
        "импортозамещение", "import substitution",
        "фстэк", "fstec", "fstek",
        "corax", "kintsugi", "audit se",
        "one-time", "ott", "one time token",
        "starting manager", "backend",
    ],
}

# Lazy imports to avoid circular deps at module load time
from core.adapters.models import (
    ComplianceFramework,
    ComplianceMatrix,
    CostEstimate,
    DependencyGraph,
    FSTECLevel,
    ServiceSpec,
    summarize_portfolios,
)


def _get_ir_feature_type():
    from models.ir import IRFeature

    return IRFeature


def _get_platform_context_type():
    from models.ir import PlatformContext

    return PlatformContext


def get_adapter_registry() -> "AdapterRegistry":
    from core.adapters import get_adapter_registry as _get_registry

    return _get_registry()


class AdapterInput(BaseModel):
    ir_features: Any  # IRFeature at runtime
    pattern_matches: List[Any] = []
    constraint_violations: List[Any] = []
    platform_context: Any  # PlatformContext at runtime


class AdapterOutput(BaseModel):
    """Universal adapter output with enhanced fields for modern platforms.

    In addition to the classic ``recommendations``, ``config_templates``,
    and ``code_snippets``, this output now includes structured data that
    enables cost-aware, compliance-aware, and dependency-aware decision
    making.
    """

    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    architecture_diagram: Optional[str] = None
    config_templates: Dict[str, str] = Field(default_factory=dict)
    code_snippets: Dict[str, str] = Field(default_factory=dict)
    deployment_manifests: Dict[str, str] = Field(default_factory=dict)
    explanation: str = ""
    confidence: float = 0.0
    can_deploy: bool = True
    platform: Optional[str] = None

    # -- New structured fields -------------------------------------------------
    service_specs: List[ServiceSpec] = Field(
        default_factory=list,
        description="Detailed service specs for every recommended service",
    )
    compliance_matrix: List[ComplianceMatrix] = Field(
        default_factory=list,
        description="Compliance framework mapping for this set of services",
    )
    cost_estimate: Optional[CostEstimate] = Field(
        default=None,
        description="Estimated monthly cost for the recommended service set",
    )
    required_dependencies: List[str] = Field(
        default_factory=list,
        description="Services needed to satisfy dependencies (transitive closure)",
    )
    portfolio_summary: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of recommended services per portfolio",
    )


class PlatformAdapter(ABC):
    @property
    @abstractmethod
    def platform_id(self) -> str:
        pass

    @property
    def supported_services(self) -> List[str]:
        """Flat service name list.

        Subclasses SHOULD override ``service_catalog`` instead.
        This property is derived from ``service_catalog`` by default.
        """
        return [s.name for s in self.service_catalog]

    @property
    def service_catalog(self) -> List[ServiceSpec]:
        """Rich catalog of all services this platform provides.

        Default returns a minimal catalog derived from ``supported_services``.
        Subclasses MUST override this (or ``supported_services``) to provide
        meaningful data.
        """
        return [
            ServiceSpec(name=name, portfolio="other", description=name)
            for name in self._legacy_services()
        ]

    def _legacy_services(self) -> List[str]:
        """Hook for adapters that only override ``supported_services``."""
        try:
            return self.supported_services
        except Exception:
            return []

    @property
    @abstractmethod
    def patterns(self) -> List[Any]:
        pass

    @property
    @abstractmethod
    def constraints(self) -> Any:
        pass

    @abstractmethod
    def transform_ir_to_platform(self, input: AdapterInput) -> AdapterOutput:
        pass

    @abstractmethod
    def generate_config(self, features: Any) -> Dict[str, str]:
        pass

    @abstractmethod
    def generate_code(self, features: Any) -> Dict[str, str]:
        pass

    # -- Enhanced capabilities -------------------------------------------------

    def resolve_dependencies(
        self, service_names: List[str], transitive: bool = True
    ) -> List[str]:
        """Resolve transitive service dependencies from the catalog.

        Returns an ordered list of all required services.
        """
        graph = DependencyGraph(self.service_catalog)
        return graph.resolve(service_names, transitive=transitive)

    @staticmethod
    def _fstec_number(spec_or_str: Any) -> int:
        """Extract FSTEC level number from an FSTECLevel, cert string, or IR value.

        Handles formats::
            FSTECLevel.FSTEC_L4  -> 4  (via .value = "fstec-l4")
            "FSTEC L4"          -> 4  (cert string)
            "fstec-l4"          -> 4  (IR feature value)
        """
        val = spec_or_str.value if isinstance(spec_or_str, FSTECLevel) else str(spec_or_str)
        # Strip "fstec-" or "fstec " prefix, then any remaining "l"
        cleaned = val.lower().replace("fstec-", "").replace("fstec ", "").replace("l", "").strip()
        return int(cleaned)

    def compute_compliance(
        self,
        features: Any,
        selected_service_names: List[str],
    ) -> List[ComplianceMatrix]:
        """Compute the compliance matrix for the selected services.

        Uses certifications declared in ``ServiceSpec.certifications``
        and IR feature compliance requirements to determine the
        achievable compliance level.
        """
        catalog = {s.name: s for s in self.service_catalog}
        certifications: set = set()
        fstec_level = None

        for name in selected_service_names:
            spec = catalog.get(name)
            if spec is None:
                continue
            for cert in spec.certifications:
                cert_lower = cert.lower()
                if "fstec" in cert_lower:
                    # Extract FSTEC level from cert string (e.g. "FSTEC L4" -> 4)
                    try:
                        level_num = cert_lower.split("l")[-1].strip()
                        level = FSTECLevel(f"fstec-l{level_num}")
                        if fstec_level is None or self._fstec_number(level) > self._fstec_number(cert):
                            fstec_level = level
                    except (IndexError, ValueError):
                        fstec_level = FSTECLevel.FSTEC_L1
                certifications.add(cert)

        # Fold in IR feature compliance requirements
        if hasattr(features, "fstec_level") and features.fstec_level:
            try:
                ir_level = FSTECLevel(features.fstec_level)
                if fstec_level is None or self._fstec_number(ir_level) > self._fstec_number(fstec_level):
                    fstec_level = ir_level
            except (ValueError, IndexError):
                pass

        matrix: List[ComplianceMatrix] = []
        if fstec_level:
            matrix.append(
                ComplianceMatrix(
                    framework=ComplianceFramework.FSTEC,
                    level=fstec_level,
                    certifications=sorted(certifications),
                    notes=f"FSTEC level {fstec_level.value} achieved",
                )
            )

        # Map common certifications to frameworks
        framework_map: Dict[str, ComplianceFramework] = {
            "gost": ComplianceFramework.GOST_CRYPTO,
            "152-fz": ComplianceFramework.PD_152_FZ,
            "152fz": ComplianceFramework.PD_152_FZ,
            "gos-sopka": ComplianceFramework.GOS_SOPKA,
            "gosсопка": ComplianceFramework.GOS_SOPKA,
            "rrpo": ComplianceFramework.RRPO,
            "ррпо": ComplianceFramework.RRPO,
        }

        seen = {m.framework for m in matrix}
        for cert in certifications:
            for key, framework in framework_map.items():
                if key in cert.lower() and framework not in seen:
                    matrix.append(
                        ComplianceMatrix(
                            framework=framework,
                            level=fstec_level or FSTECLevel.FSTEC_L1,
                            certifications=[cert],
                            notes=f"{framework.value} compliance via {cert}",
                        )
                    )
                    seen.add(framework)
                    break

        # Also check IR feature compliance_requirements
        if hasattr(features, "compliance_requirements"):
            for req in features.compliance_requirements:
                req_lower = req.lower()
                for key, framework in framework_map.items():
                    if key in req_lower and framework not in seen:
                        matrix.append(
                            ComplianceMatrix(
                                framework=framework,
                                level=fstec_level or FSTECLevel.FSTEC_L1,
                                certifications=[],
                                notes=f"Required: {req}",
                            )
                        )
                        seen.add(framework)
                        break

        return matrix

    def estimate_cost(
        self,
        features: Any,
        selected_service_names: List[str],
    ) -> CostEstimate:
        """Estimate monthly cost from selected services and IR budget.

        Uses ``ServiceSpec.cost_model`` data if available, otherwise
        applies heuristic estimates based on service category.
        """
        catalog = {s.name: s for s in self.service_catalog}
        monthly_min = 0.0
        monthly_max = 0.0
        breakdown: Dict[str, float] = {}

        for name in selected_service_names:
            spec = catalog.get(name)
            if spec is None:
                continue
            cm = spec.cost_model
            svc_min = cm.get("monthly_min", 0.0)
            svc_max = cm.get("monthly_max", 0.0)
            svc_mid = cm.get("monthly_mid", (svc_min + svc_max) / 2.0)
            monthly_min += svc_min
            monthly_max += svc_max
            breakdown[name] = svc_mid or 500.0  # default $500/mo if no data

        # Apply budget cap from IR features
        original_min = monthly_min
        original_max = monthly_max
        budget = getattr(features, "monthly_budget", None)
        notes = ""
        if budget is not None and (monthly_min > budget or monthly_max > budget):
            monthly_max = min(monthly_max, budget)
            monthly_min = min(monthly_min, budget)
            notes = f"Capped at ${budget:,.0f}/month budget (before: ${original_min:,.0f} – ${original_max:,.0f})"
        elif budget is not None:
            notes = f"Within ${budget:,.0f}/month budget"

        return CostEstimate(
            monthly_min=monthly_min,
            monthly_max=monthly_max,
            currency="USD",
            breakdown=breakdown,
            notes=notes,
        )

    def get_knowledge_node(self) -> Optional[Any]:
        graph = get_knowledge_graph()
        return graph.get_node(self.platform_id)

    def get_related_services(self) -> List[str]:
        graph = get_knowledge_graph()
        related = graph.find_related(self.platform_id, edge_types=[EdgeType.PROVIDES], depth=1)
        return [n.id for n in related]


class AdapterRegistry:
    def __init__(self):
        self._adapters: Dict[str, PlatformAdapter] = {}
        self._default: Optional[PlatformAdapter] = None

    def register(self, adapter: PlatformAdapter) -> None:
        self._adapters[adapter.platform_id] = adapter

        graph = get_knowledge_graph()
        from core.knowledge.graph import KnowledgeNode

        graph.add_node(
            KnowledgeNode(
                id=adapter.platform_id,
                name=adapter.platform_id.upper(),
                type=NodeType.PLATFORM,
                properties={"services": adapter.supported_services},
            )
        )

        for svc in adapter.supported_services:
            from core.knowledge.graph import KnowledgeEdge, KnowledgeNode

            graph.add_node(
                KnowledgeNode(
                    id=svc,
                    name=svc,
                    type=NodeType.SERVICE,
                    properties={"platform": adapter.platform_id},
                )
            )
            graph.add_edge(
                KnowledgeEdge(
                    source_id=adapter.platform_id,
                    target_id=svc,
                    type=EdgeType.PROVIDES,
                )
            )

    def get(self, platform_id: str) -> Optional[PlatformAdapter]:
        return self._adapters.get(platform_id)

    def get_default(self) -> PlatformAdapter:
        if self._default is None:
            if self._adapters:
                return next(iter(self._adapters.values()))
            raise RuntimeError(
                "No adapters registered. Call register() with at least one platform adapter."
            )
        return self._default

    def list_platforms(self) -> List[str]:
        return list(self._adapters.keys())

    def list_adapters(self) -> List[Dict[str, Any]]:
        return [
            {
                "platform_id": pid,
                "adapter": adapter,
                "supported_services": adapter.supported_services,
                "is_default": adapter is self._default,
            }
            for pid, adapter in self._adapters.items()
        ]

    def auto_detect(self, features: Any) -> "PlatformAdapter":
        feature_dict = features.model_dump()
        feature_str = str(feature_dict).lower()

        for platform_id, keywords in PLATFORM_DETECT_KEYWORDS.items():
            if any(kw in feature_str for kw in keywords):
                adapter = self._adapters.get(platform_id)
                if adapter:
                    return adapter

        return self.get_default()
