"""Data models for UI sketch understanding."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class UISketch:
    """Represents a UI artifact (sketch, wireframe, screenshot)."""

    sketch_id: str
    title: str
    source_url: str
    format_type: str  # sketch, screenshot, wireframe, diagram
    ingestion_timestamp: datetime
    page_type: Optional[str] = None  # object-page, list-report, worklist, overview, custom
    graph_node_id: Optional[str] = None
    visual_embedding_id: Optional[str] = None


@dataclass
class UIElement:
    """Individual extracted UI component."""

    element_id: str
    element_type: str  # table, form, button, input, select, chart, navigation, tab, card
    label: Optional[str] = None
    position: Dict[str, Any] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)
    interactions: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class UILayout:
    """Structural container for UI elements."""

    layout_id: str
    layout_type: str  # single-column, two-column, header-content-footer, free-form
    hierarchy: List[str] = field(default_factory=list)
    responsive: bool = False


@dataclass
class UIPattern:
    """Recognized UI pattern (e.g., master-detail, list-report)."""

    pattern_id: str
    pattern_name: str
    description: str
    complexity: str = "medium"  # low, medium, high
    required_elements: List[str] = field(default_factory=list)


@dataclass
class SAPComponent:
    """SAPUI5/Fiori/BTP component from catalog."""

    component_id: str
    name: str
    library: str  # sap.m, sap.ui.table, sap.f, sap.ui.comp, etc.
    component_type: str = "control"  # control, service, library
    supported_element_types: List[str] = field(default_factory=list)
    properties: List[str] = field(default_factory=list)
    events: List[str] = field(default_factory=list)
    documentation_url: Optional[str] = None
    complexity: int = 1  # 1-5
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SAPService:
    """Backend BTP service."""

    service_id: str
    name: str
    service_type: str  # security, destination, database, messaging, etc.
    capabilities: List[str] = field(default_factory=list)
    documentation_url: Optional[str] = None


@dataclass
class UserAction:
    """User interaction extracted from sketch."""

    action_id: str
    trigger: str  # "click Save", "enter text in filter"
    expected_result: str  # "form-submitted", "table-refreshed"


@dataclass
class UIExtractionResult:
    """Unified result of multimodal UI extraction."""

    sketch: UISketch
    layout: UILayout
    elements: List[UIElement]
    actions: List[UserAction] = field(default_factory=list)
    visual_embedding: Optional[List[float]] = None
    ocr_text: Optional[str] = None
    source_type_confidence: float = 0.0
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)
