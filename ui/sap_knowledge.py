"""SAP Component Catalog for UI sketch understanding.

Provides a seeded catalog of SAPUI5/Fiori controls and BTP services
with lookup by element type, name, and service type.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from ui.models import SAPComponent, SAPService


class SAPComponentCatalog:
    """Catalog of SAPUI5/Fiori components and BTP services."""

    def __init__(self):
        self._components: Dict[str, SAPComponent] = {}
        self._services: Dict[str, SAPService] = {}
        self._last_updated = datetime.now(timezone.utc)
        self._seed_data()

    def _seed_data(self):
        """Populate catalog with seed SAPUI5/Fiori components."""
        components = [
            SAPComponent(
                component_id="comp-sap-m-table",
                name="sap.m.Table",
                library="sap.m",
                component_type="control",
                supported_element_types=["table"],
                properties=["items", "columns", "growing", "mode", "fixedLayout", "busy", "swipeContent"],
                events=["itemPress", "selectionChange", "growing", "updateFinished", "beforeRendering"],
                documentation_url="https://ui5.sap.com/#/api/sap.m.Table",
                complexity=2,
                metadata={"deprecated": False, "responsive": True},
            ),
            SAPComponent(
                component_id="comp-sap-ui-table",
                name="sap.ui.table.Table",
                library="sap.ui.table",
                component_type="control",
                supported_element_types=["table"],
                properties=["rows", "columns", "visibleRowCount", "selectionMode", "enableColumnFreeze", "threshold"],
                events=["rowSelectionChange", "columnResize", "cellClick", "rowsUpdated"],
                documentation_url="https://ui5.sap.com/#/api/sap.ui.table.Table",
                complexity=3,
                metadata={"deprecated": False, "responsive": False},
            ),
            SAPComponent(
                component_id="comp-sap-m-button",
                name="sap.m.Button",
                library="sap.m",
                component_type="control",
                supported_element_types=["button"],
                properties=["text", "icon", "type", "enabled", "width", "tooltip"],
                events=["press", "tap"],
                documentation_url="https://ui5.sap.com/#/api/sap.m.Button",
                complexity=1,
                metadata={"deprecated": False, "responsive": True},
            ),
            SAPComponent(
                component_id="comp-sap-m-input",
                name="sap.m.Input",
                library="sap.m",
                component_type="control",
                supported_element_types=["input"],
                properties=["value", "placeholder", "type", "enabled", "editable", "required", "maxLength"],
                events=["change", "liveChange", "submit", "valueHelpRequest"],
                documentation_url="https://ui5.sap.com/#/api/sap.m.Input",
                complexity=1,
                metadata={"deprecated": False, "responsive": True},
            ),
            SAPComponent(
                component_id="comp-sap-m-select",
                name="sap.m.Select",
                library="sap.m",
                component_type="control",
                supported_element_types=["select", "dropdown"],
                properties=["items", "selectedKey", "enabled", "editable", "forceSelection"],
                events=["change", "selectionChange"],
                documentation_url="https://ui5.sap.com/#/api/sap.m.Select",
                complexity=1,
                metadata={"deprecated": False, "responsive": True},
            ),
            SAPComponent(
                component_id="comp-sap-ui-layout-form",
                name="sap.ui.layout.form.SimpleForm",
                library="sap.ui.layout",
                component_type="control",
                supported_element_types=["form"],
                properties=["title", "layout", "editable", "maxContainerCols", "emptySpan", "labelSpan"],
                events=[],
                documentation_url="https://ui5.sap.com/#/api/sap.ui.layout.form.SimpleForm",
                complexity=2,
                metadata={"deprecated": False, "responsive": True},
            ),
            SAPComponent(
                component_id="comp-sap-m-page",
                name="sap.m.Page",
                library="sap.m",
                component_type="control",
                supported_element_types=["navigation", "header", "footer"],
                properties=["title", "showHeader", "showFooter", "showNavButton", "backgroundDesign"],
                events=["navButtonPress"],
                documentation_url="https://ui5.sap.com/#/api/sap.m.Page",
                complexity=1,
                metadata={"deprecated": False, "responsive": True},
            ),
            SAPComponent(
                component_id="comp-sap-f-dynamicpage",
                name="sap.f.DynamicPage",
                library="sap.f",
                component_type="control",
                supported_element_types=["navigation"],
                properties=["title", "headerContent", "showFooter", "preserveHeaderState", "backgroundDesign"],
                events=["toggleHeaderState"],
                documentation_url="https://ui5.sap.com/#/api/sap.f.DynamicPage",
                complexity=3,
                metadata={"deprecated": False, "responsive": True},
            ),
            SAPComponent(
                component_id="comp-sap-m-icontabbar",
                name="sap.m.IconTabBar",
                library="sap.m",
                component_type="control",
                supported_element_types=["tab"],
                properties=["items", "selectedKey", "headerMode", "expandable", "applyContentDensity"],
                events=["select", "tabSelect"],
                documentation_url="https://ui5.sap.com/#/api/sap.m.IconTabBar",
                complexity=2,
                metadata={"deprecated": False, "responsive": True},
            ),
            SAPComponent(
                component_id="comp-sap-makit-chart",
                name="sap.makit.Chart",
                library="sap.makit",
                component_type="control",
                supported_element_types=["chart"],
                properties=["category", "values", "rows", "type", "showTotalLabel", "dimensionColor"],
                events=["dataSelection", "tooltipDisplay"],
                documentation_url="https://ui5.sap.com/#/api/sap.makit.Chart",
                complexity=3,
                metadata={"deprecated": True, "responsive": False},
            ),
            SAPComponent(
                component_id="comp-sap-ui-comp-filterbar",
                name="sap.ui.comp.filterbar.FilterBar",
                library="sap.ui.comp",
                component_type="control",
                supported_element_types=["filter"],
                properties=["filterGroupItems", "search", "clear", "restore", "useToolbar"],
                events=["search", "clear", "afterVariantLoad"],
                documentation_url="https://ui5.sap.com/#/api/sap.ui.comp.filterbar.FilterBar",
                complexity=3,
                metadata={"deprecated": False, "responsive": True},
            ),
            SAPComponent(
                component_id="comp-sap-f-card",
                name="sap.f.Card",
                library="sap.f",
                component_type="control",
                supported_element_types=["card"],
                properties=["header", "content", "manifest", "subtitles"],
                events=["cardAction"],
                documentation_url="https://ui5.sap.com/#/api/sap.f.Card",
                complexity=2,
                metadata={"deprecated": False, "responsive": True},
            ),
        ]
        for comp in components:
            self._components[comp.name] = comp

        services = [
            SAPService(
                service_id="svc-xsuaa",
                name="XSUAA",
                service_type="security",
                capabilities=["authentication", "authorization", "token-validation"],
                documentation_url="https://help.sap.com/docs/xsuaa-service",
            ),
            SAPService(
                service_id="svc-destination",
                name="Destination",
                service_type="connectivity",
                capabilities=["destination-management", "proxy", "on-premise-connectivity"],
                documentation_url="https://help.sap.com/docs/destination-service",
            ),
            SAPService(
                service_id="svc-html5-repo",
                name="HTML5 Application Repository",
                service_type="storage",
                capabilities=["static-hosting", "ui-deployment", "version-management"],
                documentation_url="https://help.sap.com/docs/html5-application-repository-service",
            ),
        ]
        for svc in services:
            self._services[svc.name] = svc

    def get_all_components(self) -> List[SAPComponent]:
        return list(self._components.values())

    def get_all_services(self) -> List[SAPService]:
        return list(self._services.values())

    def add_component(self, component: SAPComponent) -> None:
        self._components[component.name] = component

    def add_service(self, service: SAPService) -> None:
        self._services[service.name] = service

    def get_by_name(self, name: str) -> Optional[SAPComponent]:
        return self._components.get(name)

    def find_for_element_type(self, element_type: str) -> List[SAPComponent]:
        return [
            comp for comp in self._components.values()
            if element_type in comp.supported_element_types
        ]

    def find_services_by_type(self, service_type: str) -> List[SAPService]:
        return [
            svc for svc in self._services.values()
            if svc.service_type == service_type
        ]

    @property
    def last_updated(self) -> datetime:
        return self._last_updated

    def is_stale(self, max_age_days: int = 30) -> bool:
        return datetime.now(timezone.utc) - self._last_updated > timedelta(days=max_age_days)


_catalog: Optional[SAPComponentCatalog] = None


def get_sap_catalog() -> SAPComponentCatalog:
    global _catalog
    if _catalog is None:
        _catalog = SAPComponentCatalog()
    return _catalog
