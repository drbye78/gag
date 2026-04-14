"""Tests for UI sketch understanding data models."""

from datetime import datetime

from ui.models import (
    UISketch,
    UIElement,
    UILayout,
    UIPattern,
    SAPComponent,
    SAPService,
    UIExtractionResult,
    UserAction,
)


class TestUIElement:
    def test_minimal_creation(self):
        elem = UIElement(element_id="e1", element_type="table")
        assert elem.element_type == "table"
        assert elem.label is None
        assert elem.confidence == 0.0
        assert elem.attributes == {}
        assert elem.interactions == []

    def test_full_creation(self):
        elem = UIElement(
            element_id="e1",
            element_type="table",
            label="Orders",
            position={"row": 1, "col": 0},
            attributes={"has_filter": True, "columns": 5},
            interactions=["click-row-navigates"],
            confidence=0.85,
        )
        assert elem.element_type == "table"
        assert elem.label == "Orders"
        assert elem.confidence == 0.85
        assert elem.attributes["has_filter"] is True


class TestUISketch:
    def test_minimal_creation(self):
        sketch = UISketch(
            sketch_id="sk_001",
            title="Test UI",
            source_url="https://example.com/ui.png",
            format_type="screenshot",
            ingestion_timestamp=datetime.utcnow(),
        )
        assert sketch.sketch_id == "sk_001"
        assert sketch.format_type == "screenshot"
        assert sketch.page_type is None
        assert sketch.graph_node_id is None

    def test_with_page_type(self):
        sketch = UISketch(
            sketch_id="sk_002",
            title="Order Management",
            source_url="",
            format_type="wireframe",
            page_type="list-report",
            ingestion_timestamp=datetime.utcnow(),
        )
        assert sketch.page_type == "list-report"
        assert sketch.format_type == "wireframe"


class TestUILayout:
    def test_minimal_creation(self):
        layout = UILayout(layout_id="l1", layout_type="single-column")
        assert layout.layout_type == "single-column"
        assert layout.hierarchy == []
        assert layout.responsive is False

    def test_full_creation(self):
        layout = UILayout(
            layout_id="l1",
            layout_type="header-content-footer",
            hierarchy=["header", "sidebar", "main"],
            responsive=True,
        )
        assert layout.layout_type == "header-content-footer"
        assert len(layout.hierarchy) == 3
        assert layout.responsive is True


class TestUIPattern:
    def test_minimal_creation(self):
        pattern = UIPattern(
            pattern_id="p1",
            pattern_name="list-report",
            description="Fiori List-Report pattern",
        )
        assert pattern.pattern_name == "list-report"
        assert pattern.complexity == "medium"
        assert pattern.required_elements == []

    def test_with_required_elements(self):
        pattern = UIPattern(
            pattern_id="p2",
            pattern_name="master-detail",
            description="Master-detail with navigation",
            required_elements=["table", "form", "button"],
        )
        assert "table" in pattern.required_elements


class TestSAPComponent:
    def test_minimal_creation(self):
        comp = SAPComponent(
            component_id="sc1",
            name="sap.m.Table",
            library="sap.m",
        )
        assert comp.name == "sap.m.Table"
        assert comp.library == "sap.m"
        assert comp.component_type == "control"
        assert comp.complexity == 1

    def test_with_element_types(self):
        comp = SAPComponent(
            component_id="sc2",
            name="sap.m.Table",
            library="sap.m",
            supported_element_types=["table"],
            properties=["items", "growing"],
            events=["selectionChange"],
            complexity=2,
        )
        assert "table" in comp.supported_element_types
        assert "items" in comp.properties


class TestSAPService:
    def test_creation(self):
        svc = SAPService(
            service_id="ss1",
            name="XSUAA",
            service_type="security",
            capabilities=["authentication", "authorization"],
        )
        assert svc.name == "XSUAA"
        assert svc.service_type == "security"
        assert "authentication" in svc.capabilities


class TestUserAction:
    def test_creation(self):
        action = UserAction(
            action_id="a1",
            trigger="click Save",
            expected_result="form-submitted",
        )
        assert action.trigger == "click Save"
        assert action.expected_result == "form-submitted"


class TestUIExtractionResult:
    def test_minimal_creation(self):
        sketch = UISketch(
            sketch_id="sk1",
            title="Test",
            source_url="",
            format_type="sketch",
            ingestion_timestamp=datetime.utcnow(),
        )
        layout = UILayout(layout_id="l1", layout_type="single-column")
        elem = UIElement(element_id="e1", element_type="button", confidence=0.9)

        result = UIExtractionResult(
            sketch=sketch,
            layout=layout,
            elements=[elem],
        )
        assert len(result.elements) == 1
        assert result.actions == []
        assert result.visual_embedding is None
        assert result.ocr_text is None
        assert result.source_type_confidence == 0.0

    def test_with_actions_and_confidence(self):
        sketch = UISketch(
            sketch_id="sk1",
            title="Test",
            source_url="",
            format_type="sketch",
            ingestion_timestamp=datetime.utcnow(),
        )
        layout = UILayout(layout_id="l1", layout_type="single-column")
        elem = UIElement(element_id="e1", element_type="button", confidence=0.9)
        action = UserAction(action_id="a1", trigger="click", expected_result="submit")

        result = UIExtractionResult(
            sketch=sketch,
            layout=layout,
            elements=[elem],
            actions=[action],
            source_type_confidence=0.85,
        )
        assert len(result.actions) == 1
        assert result.source_type_confidence == 0.85
