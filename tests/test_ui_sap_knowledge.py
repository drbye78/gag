"""Tests for SAP Component Catalog."""

import pytest

from ui.models import SAPComponent, SAPService
from ui.sap_knowledge import SAPComponentCatalog, get_sap_catalog


class TestCatalogInitialization:
    def test_catalog_has_components(self):
        catalog = SAPComponentCatalog()
        assert len(catalog.get_all_components()) > 0

    def test_catalog_has_services(self):
        catalog = SAPComponentCatalog()
        assert len(catalog.get_all_services()) > 0


class TestSeedDataComponents:
    def setup_method(self):
        self.catalog = SAPComponentCatalog()

    def test_seeds_sap_m_table(self):
        comp = self.catalog.get_by_name("sap.m.Table")
        assert comp is not None
        assert comp.library == "sap.m"
        assert comp.complexity == 2

    def test_seeds_sap_m_button(self):
        comp = self.catalog.get_by_name("sap.m.Button")
        assert comp is not None
        assert comp.library == "sap.m"
        assert comp.complexity == 1

    def test_seeds_sap_ui_layout_form_simpleform(self):
        comp = self.catalog.get_by_name("sap.ui.layout.form.SimpleForm")
        assert comp is not None
        assert comp.library == "sap.ui.layout"
        assert comp.complexity == 2


class TestFindForElementType:
    def setup_method(self):
        self.catalog = SAPComponentCatalog()

    def test_find_table_returns_sap_m_table(self):
        results = self.catalog.find_for_element_type("table")
        names = [c.name for c in results]
        assert "sap.m.Table" in names

    def test_find_button_returns_sap_m_button(self):
        results = self.catalog.find_for_element_type("button")
        names = [c.name for c in results]
        assert "sap.m.Button" in names

    def test_find_form_returns_non_empty(self):
        results = self.catalog.find_for_element_type("form")
        assert len(results) > 0

    def test_add_custom_component_found_by_element_type(self):
        custom = SAPComponent(
            component_id="comp-custom",
            name="CustomControl",
            library="custom.lib",
            component_type="control",
            supported_element_types=["custom-type"],
            complexity=1,
        )
        self.catalog.add_component(custom)
        results = self.catalog.find_for_element_type("custom-type")
        names = [c.name for c in results]
        assert "CustomControl" in names


class TestGetByName:
    def setup_method(self):
        self.catalog = SAPComponentCatalog()

    def test_get_existing_component(self):
        comp = self.catalog.get_by_name("sap.m.Table")
        assert comp is not None
        assert comp.name == "sap.m.Table"

    def test_get_nonexistent_returns_none(self):
        assert self.catalog.get_by_name("nonexistent") is None


class TestFreshness:
    def setup_method(self):
        self.catalog = SAPComponentCatalog()

    def test_last_updated_is_not_none(self):
        assert self.catalog.last_updated is not None

    def test_fresh_catalog_not_stale(self):
        assert self.catalog.is_stale() is False


class TestServices:
    def setup_method(self):
        self.catalog = SAPComponentCatalog()

    def test_find_services_by_type_security(self):
        results = self.catalog.find_services_by_type("security")
        assert len(results) > 0
        assert any(s.name == "XSUAA" for s in results)


class TestSingleton:
    def test_get_sap_catalog_returns_same_instance(self):
        cat1 = get_sap_catalog()
        cat2 = get_sap_catalog()
        assert cat1 is cat2
