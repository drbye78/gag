# UI Sketch Understanding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a graph-first UI sketch understanding system that ingests UI artifacts (sketches, wireframes, screenshots), extracts structured component data, indexes into FalkorDB/Qdrant, and retrieves SAP BTP implementation suggestions.

**Architecture:** Approach C — Graph-First with Multi-Modal Evidence. VLM extraction produces structured JSON, evidence aggregator merges VLM+ColPali+OCR, UIGraphBuilder constructs FalkorDB nodes/relationships, UIRetriever performs graph-first retrieval, UISuggestionTool produces adaptive SAP BTP suggestions.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, FalkorDB (Cypher), Qdrant (vectors), GPT-4o/Qwen-VL (VLM), ColPali (visual embeddings), pytest

---

## File Map

### New Files

| File | Responsibility |
|------|----------------|
| `ui/__init__.py` | Module exports |
| `ui/models.py` | Dataclasses: UISketch, UIElement, UILayout, UIPattern, SAPComponent, SAPService, UIExtractionResult, UserAction |
| `ui/vlm_extractor.py` | Structured VLM extraction with JSON enforcement, retry logic |
| `ui/evidence_aggregator.py` | Merges VLM, ColPali, OCR into UIExtractionResult |
| `ui/graph_builder.py` | UIGraphBuilder — FalkorDB nodes, relationships, queries |
| `ui/retriever.py` | UIRetriever — graph-first retrieval |
| `ui/suggestion_tool.py` | UISuggestionTool — MCP tool |
| `ui/sap_knowledge.py` | SAP component catalog with seed data |
| `ui/sap_doc_parser.py` | SAP doc ingestion (markdown stub) |
| `ui/api.py` | FastAPI router for /ui/analyze, /ui/suggest |
| `tests/test_ui_*.py` | Unit tests for all modules |
| `evaluation/test_ui_understanding.py` | Evaluation test suite |

### Modified Files

| File | Change |
|------|--------|
| `models/ir.py:125-137` | Extend UIIR with graph_node_id, element_count, pattern_matches, sap_candidates, visual_embedding_id |
| `multimodal/ir_builder.py:83-103` | add_ui() calls UIGraphBuilder |
| `documents/multimodal.py` | Update extract_ui() prompts for JSON |
| `retrieval/orchestrator.py` | Add RetrievalSource.UI_SKETCH |
| `tools/base.py` | Register UISuggestionTool |
| `agents/planner.py` | Add ui_implementation intent |
| `api/main.py` | Mount UI router, add request/response models |

---

## Phase 1: Data Models

### Task 1: Create UI Data Models

**Files:** Create `ui/__init__.py`, `ui/models.py`, Test: `tests/test_ui_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ui_models.py
from datetime import datetime
from ui.models import (
    UISketch, UIElement, UILayout, UIPattern,
    SAPComponent, SAPService, UIExtractionResult, UserAction
)

def test_ui_element_creation():
    elem = UIElement(
        element_id="e1", element_type="table", label="Orders",
        position={"row": 1, "col": 0},
        attributes={"has_filter": True, "columns": 5},
        interactions=["click-row-navigates"], confidence=0.85
    )
    assert elem.element_type == "table"
    assert elem.confidence == 0.85

def test_ui_sketch_creation():
    sketch = UISketch(
        sketch_id="sk_001", title="Order Management",
        source_url="https://example.com/sketch.png",
        format_type="screenshot", ingestion_timestamp=datetime.utcnow()
    )
    assert sketch.sketch_id == "sk_001"

def test_ui_layout_creation():
    layout = UILayout(layout_id="l1", layout_type="header-content-footer",
                      hierarchy=["header", "sidebar", "main"], responsive=True)
    assert layout.layout_type == "header-content-footer"

def test_ui_pattern_creation():
    pattern = UIPattern(pattern_id="p1", pattern_name="list-report",
        description="Fiori List-Report pattern", complexity="medium",
        required_elements=["table", "filter", "button"])
    assert "table" in pattern.required_elements

def test_sap_component_creation():
    comp = SAPComponent(component_id="sc1", name="sap.m.Table", library="sap.m",
        component_type="control", supported_element_types=["table"],
        properties=["items", "growing"], events=["selectionChange"], complexity=2)
    assert "table" in comp.supported_element_types

def test_sap_service_creation():
    svc = SAPService(service_id="ss1", name="XSUAA", service_type="security",
        capabilities=["authentication", "authorization"])
    assert "authentication" in svc.capabilities

def test_user_action_creation():
    action = UserAction(action_id="a1", trigger="click Save", expected_result="form-submitted")
    assert action.trigger == "click Save"

def test_ui_extraction_result():
    sketch = UISketch(sketch_id="sk1", title="Test", source_url="",
        format_type="sketch", ingestion_timestamp=datetime.utcnow())
    layout = UILayout(layout_id="l1", layout_type="single-column", hierarchy=["main"])
    elem = UIElement(element_id="e1", element_type="button", label="Submit", confidence=0.9)
    result = UIExtractionResult(sketch=sketch, layout=layout, elements=[elem], actions=[])
    assert len(result.elements) == 1
    assert result.source_type_confidence == 0.0  # No elements with confidence yet
```

- [ ] **Step 2: Run test** → `python -m pytest tests/test_ui_models.py -v` → FAIL (no module)

- [ ] **Step 3: Create models**

```python
# ui/__init__.py
from ui.models import (
    UISketch, UIElement, UILayout, UIPattern,
    SAPComponent, SAPService, UIExtractionResult, UserAction
)
__all__ = ["UISketch", "UIElement", "UILayout", "UIPattern",
    "SAPComponent", "SAPService", "UIExtractionResult", "UserAction"]
```

```python
# ui/models.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

@dataclass
class UISketch:
    sketch_id: str
    title: str
    source_url: str
    format_type: str  # sketch, screenshot, wireframe, diagram
    ingestion_timestamp: datetime
    page_type: Optional[str] = None
    graph_node_id: Optional[str] = None
    visual_embedding_id: Optional[str] = None

@dataclass
class UIElement:
    element_id: str
    element_type: str  # table, form, button, input, select, chart, navigation, tab, card
    label: Optional[str] = None
    position: Dict[str, Any] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)
    interactions: List[str] = field(default_factory=list)
    confidence: float = 0.0

@dataclass
class UILayout:
    layout_id: str
    layout_type: str  # single-column, two-column, header-content-footer, free-form
    hierarchy: List[str] = field(default_factory=list)
    responsive: bool = False

@dataclass
class UIPattern:
    pattern_id: str
    pattern_name: str
    description: str
    complexity: str = "medium"
    required_elements: List[str] = field(default_factory=list)

@dataclass
class SAPComponent:
    component_id: str
    name: str
    library: str
    component_type: str = "control"
    supported_element_types: List[str] = field(default_factory=list)
    properties: List[str] = field(default_factory=list)
    events: List[str] = field(default_factory=list)
    documentation_url: Optional[str] = None
    complexity: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SAPService:
    service_id: str
    name: str
    service_type: str
    capabilities: List[str] = field(default_factory=list)
    documentation_url: Optional[str] = None

@dataclass
class UserAction:
    action_id: str
    trigger: str
    expected_result: str

@dataclass
class UIExtractionResult:
    sketch: UISketch
    layout: UILayout
    elements: List[UIElement]
    actions: List[UserAction] = field(default_factory=list)
    visual_embedding: Optional[List[float]] = None
    ocr_text: Optional[str] = None
    source_type_confidence: float = 0.0
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)
```

- [ ] **Step 4: Run test** → PASS
- [ ] **Step 5: Commit** → `git add ui/__init__.py ui/models.py tests/test_ui_models.py && git commit -m "feat(ui): add UI sketch data models"`

---

## Phase 2: VLM Extraction

### Task 2: Structured VLM Extractor

**Files:** Create `ui/vlm_extractor.py`, Test: `tests/test_ui_vlm_extractor.py`

- [ ] **Step 1: Write test** — Test JSON schema validation, parse_vlm_response, retry logic
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** VLMUIExtractor with UIExtractionSchema (Pydantic), JSON enforcement, retry
- [ ] **Step 4: Run** → PASS
- [ ] **Step 5: Commit**

Key code: `UIExtractionSchema` Pydantic model validates VLM JSON output. `VLMUIExtractor.extract()` retries on failure.

---

## Phase 3: Evidence Aggregation

### Task 3: Evidence Aggregator

**Files:** Create `ui/evidence_aggregator.py`, Test: `tests/test_ui_evidence_aggregator.py`

- [ ] **Step 1: Write test** — Test VLM-only, with embedding, with OCR, low confidence warning
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** EvidenceAggregator.aggregate() merges VLM schema + embedding + OCR → UIExtractionResult
- [ ] **Step 4: Run** → PASS
- [ ] **Step 5: Commit**

---

## Phase 4: Graph Builder

### Task 4: UIGraphBuilder

**Files:** Create `ui/graph_builder.py`, Test: `tests/test_ui_graph_builder.py`

- [ ] **Step 1: Write test** — Test Cypher generation for sketch, elements, layout nodes
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** UIGraphBuilder.build_cypher() → UISketch, UILayout, UIElement nodes with CONTAINS_ELEMENT, HAS_LAYOUT
- [ ] **Step 4: Run** → PASS
- [ ] **Step 5: Commit**

---

## Phase 5: UI Retriever

### Task 5: UIRetriever

**Files:** Create `ui/retriever.py`, Test: `tests/test_ui_retriever.py`

- [ ] **Step 1: Write test** — Test search_by_element_type, find_similar_structural, find_sap_candidates
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** UIRetriever with Cypher queries for element matching, structural similarity, SAP candidates
- [ ] **Step 4: Run** → PASS
- [ ] **Step 5: Commit**

---

## Phase 6: SAP Knowledge & Suggestion Tool

### Task 6: SAP Component Catalog

**Files:** Create `ui/sap_knowledge.py`, Test: `tests/test_ui_sap_knowledge.py`

- [ ] **Step 1: Write test** — Test seed data, element type lookup, custom component addition
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** SAPComponentCatalog with 12 SAPUI5 controls + 3 BTP services seed data
- [ ] **Step 4: Run** → PASS
- [ ] **Step 5: Commit**

### Task 7: UISuggestionTool

**Files:** Create `ui/suggestion_tool.py`, Test: `tests/test_ui_suggestion_tool.py`

- [ ] **Step 1: Write test** — Test validation, execute with sketch_id, invalid detail_level
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** UISuggestionTool extends BaseTool, returns SAP candidates
- [ ] **Step 4: Run** → PASS
- [ ] **Step 5: Commit**

---

## Phase 7: Integration

### Task 8: Extend UIIR Model

**Modify:** `models/ir.py:125-137` — Add graph_node_id, element_count, pattern_matches, sap_candidates, visual_embedding_id

- [ ] **Step 1: Edit** UIIR class
- [ ] **Step 2: Run** `python -m pytest tests/test_ir.py -v` → PASS
- [ ] **Step 3: Commit**

### Task 9: Integrate UIGraphBuilder into IR Builder

**Modify:** `multimodal/ir_builder.py:83-103` — add_ui() calls UIGraphBuilder

- [ ] **Step 1: Edit** add_ui method
- [ ] **Step 2: Commit**

### Task 10: Update extract_ui Prompts

**Modify:** `documents/multimodal.py` — LlamaIndex + VisionAPI extract_ui() prompts

- [ ] **Step 1: Edit** both extract_ui methods
- [ ] **Step 2: Commit**

### Task 11: Add RetrievalSource.UI_SKETCH

**Modify:** `retrieval/orchestrator.py` — Add enum value, ui_retriever init, _retrieve_ui()

- [ ] **Step 1: Edit** enum, __init__, retrieve(), add _retrieve_ui()
- [ ] **Step 2: Commit**

### Task 12: Register UISuggestionTool

**Modify:** `tools/base.py:331-346` — Register in _register_default_tools()

- [ ] **Step 1: Edit** tool registry
- [ ] **Step 2: Commit**

### Task 13: Add UI Intent to Planner

**Modify:** `agents/planner.py` — Add ui keywords, _identify_sources UI detection

- [ ] **Step 1: Edit** planner intent keywords and source identification
- [ ] **Step 2: Commit**

### Task 14: Add API Endpoints

**Create:** `ui/api.py` — FastAPI router with /ui/analyze, /ui/suggest
**Modify:** `api/main.py` — Mount UI router

- [ ] **Step 1: Create** ui/api.py with endpoints
- [ ] **Step 2: Edit** api/main.py to include router
- [ ] **Step 3: Commit**

---

## Phase 8: Evaluation & SAP Doc Parser

### Task 15: Evaluation Test Suite

**Create:** `evaluation/test_ui_understanding.py`, `evaluation/samples/.gitkeep`

- [ ] **Step 1: Create** evaluation tests with ground truth test cases
- [ ] **Step 2: Commit**

### Task 16: SAPDocParser Stub

**Create:** `ui/sap_doc_parser.py`, Test: `tests/test_ui_sap_doc_parser.py`

- [ ] **Step 1: Write test** — Parse component/service markdown
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** SAPDocParser markdown parsing
- [ ] **Step 4: Run** → PASS
- [ ] **Step 5: Commit**

---

## Phase 9: Final Verification

### Task 17: Run Full Test Suite

- [ ] **Step 1:** `python -m pytest tests/test_ui_*.py -v` → All PASS
- [ ] **Step 2:** `python -m pytest tests/ -v --ignore=evaluation/` → All PASS
- [ ] **Step 3:** `python -m ruff check ui/` → Clean
- [ ] **Step 4: Commit**

---

## Spec Coverage

| Spec Section | Task |
|---|---|
| Graph Schema | Task 4, 6 |
| Multi-Modal Extraction | Task 2, 3 |
| UIGraphBuilder | Task 4 |
| UIIR Extension | Task 8 |
| IR Builder Integration | Task 9 |
| extract_ui JSON prompts | Task 10 |
| RetrievalSource.UI_SKETCH | Task 11 |
| UIRetriever | Task 5 |
| SAP Catalog | Task 6 |
| UISuggestionTool | Task 7 |
| Planner UI intent | Task 13 |
| API Endpoints | Task 14 |
| Error Handling | Task 2, 3, 4 |
| Unit Tests | Tasks 1-7, 16 |
| Evaluation | Task 15 |
| SAP Doc Parser | Task 16 |