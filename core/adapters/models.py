"""
ServiceSpec model and supporting types for platform adapter catalog.

Replaces flat ``List[str]`` service lists with rich metadata that
enables dependency resolution, compliance matrix computation, cost
estimation, and portfolio-level reasoning.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field


class FSTECLevel(str, Enum):
    """FSTEC certification levels for information security (Russian Federation).

    Levels correspond to increasing data sensitivity:
        L1 – basic (organizational secrets)
        L2 – low (PD: personal data)
        L3 – medium (PD / state secrets)
        L4 – high (critical infrastructure)
        L5 – very high (state secrets)
        L6 – maximum (supreme state secrets)
    """

    FSTEC_L1 = "fstec-l1"
    FSTEC_L2 = "fstec-l2"
    FSTEC_L3 = "fstec-l3"
    FSTEC_L4 = "fstec-l4"
    FSTEC_L5 = "fstec-l5"
    FSTEC_L6 = "fstec-l6"


class ServiceEdition(str, Enum):
    """Common Platform V service editions."""

    COMMUNITY = "community"
    STANDARD = "standard"
    ENTERPRISE = "enterprise"
    SE = "special_edition"
    ULTIMATE = "ultimate"


class ServiceSpec(BaseModel):
    """Rich service descriptor — the heart of the new adapter architecture.

    Every platform adapter returns these instead of plain strings,
    enabling downstream consumers (orchestrator, UI, explainer) to
    reason about editions, SLAs, compliance, cost, and dependencies.
    """

    name: str = Field(..., description="Service product name (e.g. 'Platform V Pangolin')")
    portfolio: str = Field(
        ..., description="Portfolio grouping (data_management, integration, security, ...)"
    )
    edition: ServiceEdition = Field(
        default=ServiceEdition.ENTERPRISE, description="Service edition / tier"
    )
    sla: str = Field(default="99.9%", description="Guaranteed SLA")
    certifications: List[str] = Field(
        default_factory=list, description="Certifications (FSTEC, GOST, etc.)"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Other services this depends on (by name or spec id)",
    )
    tags: List[str] = Field(default_factory=list, description="Search / matching keywords")
    cost_model: Dict[str, Any] = Field(
        default_factory=dict,
        description="Cost model parameters (monthly_min, monthly_max, currency, pricing_tier)",
    )
    regions: List[str] = Field(default_factory=list, description="Available deployment regions")
    version: str = Field(default="1.0", description="Current product version")
    description: str = Field(default="", description="Short product summary")

    @property
    def id(self) -> str:
        """Stable identifier derived from the product name."""
        return self.name.lower().replace(" ", "-").replace("::", "-")


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""

    FSTEC = "fstec"
    GOST_CRYPTO = "gost_crypto"
    PD_152_FZ = "152-fz"
    GOS_SOPKA = "gos-sopka"
    FZ_63 = "fz-63"
    RRPO = "rrpo"
    PCI_DSS = "pci-dss"
    HIPAA = "hipaa"
    GDPR = "gdpr"
    SOC2 = "soc2"
    ISO_27001 = "iso-27001"
    SOX = "sox"


class ComplianceMatrix(BaseModel):
    """Structured compliance mapping for a selected set of services."""

    framework: ComplianceFramework = Field(..., description="The compliance framework")
    level: FSTECLevel = Field(default=FSTECLevel.FSTEC_L1, description="Achieved certification level")
    certifications: List[str] = Field(default_factory=list, description="Specific certificates")
    notes: str = Field(default="", description="Human-readable compliance notes")


class CostEstimate(BaseModel):
    """Structured monthly cost estimate for a selected set of services."""

    monthly_min: float = Field(default=0.0, description="Minimum expected monthly cost (USD)")
    monthly_max: float = Field(default=0.0, description="Maximum expected monthly cost (USD)")
    currency: str = Field(default="USD", description="Cost currency")
    breakdown: Dict[str, float] = Field(
        default_factory=dict, description="Per-service cost breakdown"
    )
    notes: str = Field(default="", description="Cost estimation notes / caveats")

    @property
    def mid_range(self) -> float:
        return (self.monthly_min + self.monthly_max) / 2.0


# ---------------------------------------------------------------------------
# Dependency resolution
# ---------------------------------------------------------------------------


class DependencyGraph:
    """Resolve transitive service dependencies.

    Services declare their dependencies via ``ServiceSpec.dependencies``.
    This graph computes the transitive closure of those declarations.
    """

    def __init__(self, catalog: List[ServiceSpec]) -> None:
        self._catalog_by_name: Dict[str, ServiceSpec] = {s.name: s for s in catalog}
        self._edges: Dict[str, Set[str]] = {}
        for spec in catalog:
            self._edges[spec.name] = set(spec.dependencies)

    def resolve(
        self, service_names: List[str], transitive: bool = True
    ) -> List[str]:
        """Return the transitive closure of required services.

        Args:
            service_names: Starting set of service names.
            transitive: If True (default), compute transitive closure.

        Returns:
            Ordered list of all required services (topological order).
        """
        resolved: List[str] = []
        visited: Set[str] = set()

        def _visit(name: str) -> None:
            if name in visited or name not in self._edges:
                return
            visited.add(name)
            for dep in self._edges.get(name, set()):
                _visit(dep)
            resolved.append(name)

        for name in service_names:
            _visit(name)

        if not transitive:
            # Only direct dependencies
            direct: Set[str] = set()
            for name in service_names:
                for dep in self._edges.get(name, set()):
                    direct.add(dep)
            return list(direct)

        return resolved

    def get_edges(self) -> List[tuple[str, str]]:
        """Return all dependency edges as (dependent, dependency) tuples."""
        edges: List[tuple[str, str]] = []
        for dependent, deps in self._edges.items():
            for dep in deps:
                edges.append((dependent, dep))
        return edges

    def validate(self) -> List[str]:
        """Check for missing or circular dependencies.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors: List[str] = []
        visited: Set[str] = set()
        in_stack: Set[str] = set()

        def _check_cycle(name: str, path: List[str]) -> None:
            if name in in_stack:
                cycle_start = path.index(name)
                cycle = path[cycle_start:] + [name]
                errors.append(f"Circular dependency: {' -> '.join(cycle)}")
                return
            if name in visited or name not in self._edges:
                return
            visited.add(name)
            in_stack.add(name)
            path.append(name)
            for dep in self._edges.get(name, set()):
                if dep not in self._edges and dep not in self._catalog_by_name:
                    errors.append(f"Missing dependency: '{name}' depends on '{dep}' not in catalog")
                else:
                    _check_cycle(dep, path)
            path.pop()
            in_stack.discard(name)

        for name in self._edges:
            _check_cycle(name, [])
        return errors


# ---------------------------------------------------------------------------
# Portfolio arithmetic
# ---------------------------------------------------------------------------


def summarize_portfolios(service_specs: List[ServiceSpec]) -> Dict[str, int]:
    """Count services per portfolio.

    Returns a dict mapping portfolio names to their service count.
    """
    counts: Dict[str, int] = {}
    for spec in service_specs:
        counts[spec.portfolio] = counts.get(spec.portfolio, 0) + 1
    return dict(sorted(counts.items()))


def filter_by_portfolio(
    service_specs: List[ServiceSpec], portfolio: str
) -> List[ServiceSpec]:
    """Return only services belonging to a specific portfolio."""
    return [s for s in service_specs if s.portfolio == portfolio]


def filter_by_certification(
    service_specs: List[ServiceSpec], certification: str
) -> List[ServiceSpec]:
    """Return only services with a specific certification."""
    return [s for s in service_specs if certification in s.certifications]


# ---------------------------------------------------------------------------
# FSTEC level helpers
# ---------------------------------------------------------------------------


def fstec_level_number(value: Any) -> int:
    """Extract the numeric FSTEC level from an enum member, cert string, or IR value.

    Handles three input formats:
    * ``FSTECLevel.FSTEC_L4``         → 4
    * ``"FSTEC L4"``                  → 4
    * ``"fstec-l4"``                  → 4

    Returns 0 when the level cannot be determined so that callers can safely
    use this function in ``max()`` / comparison contexts.
    """
    if isinstance(value, FSTECLevel):
        return int(value.value.split("-")[-1])
    if isinstance(value, str):
        cleaned = value.lower().replace(" ", "-").replace("_", "-")
        parts = cleaned.split("-")
        for part in parts:
            if part.startswith("l") and len(part) > 1 and part[1:].isdigit():
                return int(part[1:])
            if part.isdigit():
                return int(part)
    return 0


# ---------------------------------------------------------------------------
# Constraint-based filtering
# ---------------------------------------------------------------------------


def filter_by_max_budget(
    service_specs: List[ServiceSpec], max_monthly: float
) -> List[ServiceSpec]:
    """Keep only services whose minimum monthly cost is within *max_monthly*.

    Uses ``cost_model.monthly_min`` when available; services with no cost
    model are **excluded** so that explicit cost data is required for
    budget-aware filtering.
    """
    result: List[ServiceSpec] = []
    for spec in service_specs:
        if not spec.cost_model:
            continue
        monthly_min = spec.cost_model.get("monthly_min") or spec.cost_model.get("min", 0)
        if monthly_min <= max_monthly:
            result.append(spec)
    return result


def filter_by_min_fstec(
    service_specs: List[ServiceSpec], min_level: FSTECLevel | str
) -> List[ServiceSpec]:
    """Keep only services certified at or above *min_level*.

    A service qualifies if **any** of its certifications resolves to an
    FSTEC level >= the minimum.
    """
    min_num = fstec_level_number(min_level)
    result: List[ServiceSpec] = []
    for spec in service_specs:
        for cert in spec.certifications:
            if fstec_level_number(cert) >= min_num:
                result.append(spec)
                break
    return result


def filter_by_region(
    service_specs: List[ServiceSpec], region: str
) -> List[ServiceSpec]:
    """Keep only services deployable in the given *region*."""
    region_lower = region.lower()
    return [
        s for s in service_specs if any(r.lower() == region_lower for r in s.regions)
    ]


def filter_by_compliance_framework(
    service_specs: List[ServiceSpec], framework: ComplianceFramework | str
) -> List[ServiceSpec]:
    """Keep only services whose certifications satisfy a compliance framework.

    The match is case-insensitive: framework and certification values are
    compared after stripping whitespace and lower-casing.
    """
    framework_lower = (
        framework.value if isinstance(framework, ComplianceFramework) else framework.lower()
    )
    return [
        s
        for s in service_specs
        if any(framework_lower in cert.lower() for cert in s.certifications)
    ]


def apply_constraint_filters(
    service_specs: List[ServiceSpec],
    *,
    max_budget: Optional[float] = None,
    min_fstec_level: Optional[FSTECLevel | str] = None,
    required_region: Optional[str] = None,
    required_framework: Optional[ComplianceFramework | str] = None,
) -> List[ServiceSpec]:
    """Chain multiple constraint filters over a list of service specs.

    Every filter is optional — pass ``None`` (or omit) to skip it.
    Filters are applied in a fixed order (budget → FSTEC → region →
    framework) so the result is deterministic regardless of how many
    constraints are active.
    """
    result = list(service_specs)
    if max_budget is not None:
        result = filter_by_max_budget(result, max_budget)
    if min_fstec_level is not None:
        result = filter_by_min_fstec(result, min_fstec_level)
    if required_region is not None:
        result = filter_by_region(result, required_region)
    if required_framework is not None:
        result = filter_by_compliance_framework(result, required_framework)
    return result
