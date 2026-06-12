"""Tests for UI Component Knowledge Registry."""

from ui.knowledge import (
    ComponentType,
    UIComponent,
    UIService,
    get_ui_knowledge_registry,
)


class TestKnowledgeRegistry:
    def test_registry_has_domains(self):
        registry = get_ui_knowledge_registry()
        assert len(registry.all_domains()) == 3

    def test_sap_domain_registered(self):
        registry = get_ui_knowledge_registry()
        sap = registry.get("sap")
        assert sap is not None

    def test_aws_domain_registered(self):
        registry = get_ui_knowledge_registry()
        aws = registry.get("aws")
        assert aws is not None

    def test_azure_domain_registered(self):
        registry = get_ui_knowledge_registry()
        azure = registry.get("azure")
        assert azure is not None


class TestSAPKnowledge:
    def setup_method(self):
        self.registry = get_ui_knowledge_registry()
        self.sap = self.registry.get("sap")

    def test_sap_components_loaded(self):
        assert len(self.sap.components) == 12

    def test_sap_services_loaded(self):
        assert len(self.sap.services) == 3

    def test_sap_table_mapping(self):
        table_comps = self.sap.map_element_to_components("table")
        assert len(table_comps) == 2

    def test_sap_button_mapping(self):
        button_comps = self.sap.map_element_to_components("button")
        assert len(button_comps) == 1
        assert button_comps[0].name == "sap.m.Button"

    def test_sap_xsuaa_service(self):
        xsuaa = self.sap.get_service("XSUAA")
        assert xsuaa is not None
        assert "authentication" in xsuaa.capabilities


class TestCrossDomainLookup:
    def test_find_table_across_domains(self):
        registry = get_ui_knowledge_registry()
        results = registry.find_components("table")
        assert len(results) == 4

    def test_find_button_across_domains(self):
        registry = get_ui_knowledge_registry()
        results = registry.find_components("button")
        assert len(results) == 3


class TestComponentModel:
    def test_ui_component_fields(self):
        comp = UIComponent(
            component_id="test",
            name="TestComponent",
            library="test.lib",
            component_type=ComponentType.CONTROL,
            supported_element_types=["button"],
            properties=["onClick"],
            events=["click"],
        )
        assert comp.name == "TestComponent"
        assert ComponentType.CONTROL == comp.component_type

    def test_ui_service_fields(self):
        svc = UIService(
            service_id="test",
            name="TestService",
            service_type="database",
            capabilities=["CRUD"],
        )
        assert svc.name == "TestService"
        assert "CRUD" in svc.capabilities
