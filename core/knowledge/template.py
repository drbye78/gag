"""Platform knowledge template - copy to core/knowledge/myplatform.py for new platform."""

from typing import Any, Dict, List

from core.knowledge.adrs import ADR, ADRStatus
from core.knowledge.usecases import UseCase, UseCaseCategory, UseCasePriority

PLATFORM_USE_CASES: List[UseCase] = [
    UseCase(
        id="myplatform_integration",
        name="MyPlatform Integration",
        description="Integrate with MyPlatform services",
        category=UseCaseCategory.INTEGRATION,
        priority=UseCasePriority.HIGH,
        platforms=["myplatform"],
        patterns=["myplatform_pattern1"],
        technologies=["tech1"],
        acceptance_criteria=["Service connected"],
        effort_estimate="medium",
        risk_level="low",
        owner=None,
    ),
    UseCase(
        id="myplatform_automation",
        name="MyPlatform Automation",
        description="Automate workflows in MyPlatform",
        category=UseCaseCategory.AUTOMATION,
        priority=UseCasePriority.MEDIUM,
        platforms=["myplatform"],
        patterns=["myplatform_pattern2"],
        effort_estimate="low",
        risk_level="low",
        owner=None,
    ),
]


PLATFORM_ADRS: List[ADR] = [
    ADR(
        id="adr-001",
        title="Use MyPlatform for real-time processing",
        status=ADRStatus.ACCEPTED,
        context="Need real-time data processing",
        decision="Use MyPlatform streaming service",
        consequences="Benefits: Low latency, automatic scaling. Tradeoffs: Higher cost",
        related_platforms=["myplatform"],
        superseded_by=None,
        owner=None,
    ),
]


PLATFORM_UI_COMPONENTS: Dict[str, Any] = {
    "Button": {
        "id": "myplatform:button",
        "name": "Button",
        "type": "component",
        "library": "myplatform-ui",
        "properties": {"variant": "primary", "size": "medium"},
    },
    "DataTable": {
        "id": "myplatform:datatable",
        "name": "DataTable",
        "type": "component",
        "library": "myplatform-ui",
        "properties": {"columns": [], "sortable": True},
    },
    "Form": {
        "id": "myplatform:form",
        "name": "Form",
        "type": "component",
        "library": "myplatform-ui",
        "properties": {"layout": "vertical"},
    },
}


PLATFORM_SERVICES: Dict[str, Any] = {
    "Service1": {
        "name": "Service 1",
        "description": "Main service",
        "capabilities": ["api", "streaming"],
    },
    "Service2": {
        "name": "Service 2",
        "description": "Secondary service",
        "capabilities": ["storage", "analytics"],
    },
}


PLATFORM_ENTITIES: Dict[str, Any] = {
    "Service": {"type": "service", "properties": ["name", "endpoint"]},
    "Component": {"type": "component", "properties": ["name", "version"]},
    "API": {"type": "api", "properties": ["endpoint", "methods"]},
}


def register_myplatform_knowledge() -> None:
    from core.knowledge.adrs import ADRRepository
    from core.knowledge.usecases import UseCaseRepository

    repo = UseCaseRepository()
    for uc in PLATFORM_USE_CASES:
        repo.add(uc)

    adr_repo = ADRRepository()
    for adr in PLATFORM_ADRS:
        adr_repo.add(adr)


def get_ui_component(component_id: str) -> Dict[str, Any]:
    return PLATFORM_UI_COMPONENTS.get(component_id, {})


def get_service_definition(service_name: str) -> Dict[str, Any]:
    return PLATFORM_SERVICES.get(service_name, {})
