# UI Sketch Understanding — Graph-First Design Specification

**Date:** 2026-04-14  
**Status:** Draft — Awaiting Review  
**Approach:** C (Graph-First with Multi-Modal Evidence)

---

## 1. Executive Summary

This specification designs UI sketch understanding for the GAG Engineering Intelligence System, enabling ingestion of UI artifacts (hand-drawn sketches, digital wireframes, screenshots, embedded diagrams), structured knowledge extraction, graph-based indexing, and retrieval capable of suggesting SAP BTP implementations from sketches.

### Scope

- **Input types:** Hand-drawn sketches, Figma/Sketch exports, Balsamiq wireframes, application screenshots, embedded UI diagrams from documents (draw.io, PlantUML, PowerPoint)
- **Output:** Structured UI component extraction, SAP BTP component mapping, adaptive implementation suggestions (overview → code → full scaffold)
- **Success criteria:** End-to-end task success — given a sketch, produce correct SAP BTP implementation suggestion (component + code + reasoning) rated acceptable by SAP BTP developers
- **Quality priority:** Both ingestion quality and retrieval speed are equally important

---

## 2. Architecture

### 2.1 High-Level Design

Three new layers added to existing GAG architecture:

```
┌─────────────────────────────────────────────────────────────┐
│              NEW: UI Understanding Layer                      │
│  Multi-Modal Extractor → Evidence Aggregator → Graph Builder  │
├─────────────────────────────────────────────────────────────┤
│              NEW: SAP BTP Knowledge Layer                     │
│  SAP Component Catalog → Pattern Registry → Anti-Pattern DB   │
├─────────────────────────────────────────────────────────────┤
│              EXISTING: Knowledge Graph (extended)              │
│  FalkorDB: new node types + relationships                     │
├─────────────────────────────────────────────────────────────┤
│              EXISTING: Retrieval Layer (extended)              │
│  Graph-first retrieval via Cypher + vector fallback           │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Graph Schema

#### New Node Types

| Node Type | Key Properties | Purpose |
|-----------|----------------|---------|
| `UISketch` | `id`, `title`, `source_url`, `format`, `ingestion_timestamp` | The sketch/document artifact |
| `UIElement` | `element_type`, `label`, `position`, `attributes`, `confidence` | Individual extracted UI component |
| `UILayout` | `layout_type`, `hierarchy`, `responsive` | Structural container for elements |
| `UIPattern` | `pattern_name`, `description`, `complexity`, `required_elements` | Recognized UI pattern |
| `SAPComponent` | `name`, `library`, `type`, `documentation_url`, `properties`, `events`, `supported_element_types` | SAPUI5/Fiori/BTP component |
| `SAPService` | `name`, `type`, `capabilities` | Backend BTP service |

#### New Relationships

| Relationship | From → To | Meaning |
|--------------|-----------|---------|
| `CONTAINS_ELEMENT` | UISketch/UILayout → UIElement | Contains this element |
| `HAS_LAYOUT` | UISketch → UILayout | Sketch has this layout |
| `MATCHES_PATTERN` | UISketch → UIPattern | Sketch matches this pattern |
| `CAN_BE_IMPLEMENTED_AS` | UIElement → SAPComponent | Element could be this SAP control |
| `SIMILAR_TO` | UISketch → UISketch | Two sketches are semantically similar |
| `USES_PATTERN` | SAPComponent → UIPattern | SAP component implements this pattern |
| `SERVED_BY` | UIElement → SAPService | UI element backed by this service |
| `HAS_ISSUE` | SAPComponent → UISketch | Component had problems in past projects |
| `USED_IN_PROJECT` | UISketch → String | Source project reference |
| `IMPLEMENTS_UI` | Component (code) → UISketch | Code implements this UI |

### 2.3 Integration Points

| Existing Component | Extension |
|--------------------|-----------|
| `models/ir.py` | `UIIR` gains `graph_node_id`, `element_count`, `pattern_matches`, `sap_candidates` |
| `multimodal/ir_builder.py` | `add_ui()` calls `UIGraphBuilder` after creating IR node |
| `documents/multimodal.py` | `extract_ui()` prompt updated for structured JSON |
| `documents/colpali.py` | UI image embeddings during ingestion |
| `retrieval/orchestrator.py` | New `RetrievalSource.UI_SKETCH` |
| `tools/base.py` | New `UISuggestionTool` |
| `agents/planner.py` | New intent: `ui_implementation` |
| `api/main.py` | New endpoints: `POST /ui/analyze`, `POST /ui/suggest` |
| `ingestion/indexer.py` | ColPali embeddings for UISketch nodes |

---

## 3. Multi-Modal Extraction Pipeline

### 3.1 Pipeline Phases

**Phase 1: Multi-Evidence Collection**

Input: Image (any format). Three parallel extractors run:

1. **VLM Extract** (GPT-4o or Qwen-VL) — Produces structured UI JSON
2. **ColPali Embed** — Produces visual similarity vector
3. **Docling OCR** (fallback for hand-drawn) — Extracts text content

**VLM Structured Prompt (JSON output enforced):**

```json
{
  "source_type": "sketch|screenshot|wireframe|diagram",
  "page_type": "object-page|list-report|worklist|overview|custom",
  "layout": {
    "type": "single-column|two-column|header-content-footer|free-form",
    "regions": [{"name": "header|sidebar|main|footer", "elements": [...]}]
  },
  "elements": [
    {
      "id": "e1",
      "type": "table|form|button|input|select|chart|navigation|tab|card",
      "label": "Orders",
      "position": {"row": 1, "col": 0, "span": "full"},
      "attributes": {"has_filter": true, "has_pagination": true, "columns": 5},
      "interactions": ["click-row-navigates", "filter-triggers-refresh"],
      "confidence": 0.85
    }
  ],
  "user_actions": [{"trigger": "click Save", "expected_result": "form-submitted"}]
}
```

**Phase 2: Evidence Aggregation**

`EvidenceAggregator` merges VLM JSON, ColPali embedding, and OCR text into:

```python
@dataclass
class UIExtractionResult:
    sketch: UISketch
    layout: UILayout
    elements: list[UIElement]
    actions: list[UserAction]
    visual_embedding: Optional[List[float]]
    ocr_text: Optional[str]
    source_type_confidence: float
    extraction_metadata: Dict[str, Any]
```

**Phase 3: SAP BTP Knowledge Population (Parallel Pipeline)**

Separate batch ingestion populates SAP knowledge:

- SAPUI5 API docs → `SAPComponent` nodes
- Fiori guidelines → `UIPattern` nodes
- BTP service docs → `SAPService` nodes
- Internal repos → Company-specific `SAPComponent` variants
- Tickets/incidents → `HAS_ISSUE` relationships

### 3.2 Design Decisions

- **JSON enforcement:** Response format parsing (GPT-4o JSON mode) rather than free text
- **ColPali on UISketch nodes:** Visual similarity via vector operations
- **Source type detection:** VLM classifies input to set confidence expectations
- **Lossy by design:** Extract what's needed for reasoning, not pixel-perfect reconstruction

---

## 4. Graph Builder & Indexing

### 4.1 UIGraphBuilder

Takes `UIExtractionResult` and constructs graph in five steps:

1. **Create UISketch node** — With visual embedding
2. **Create Layout & Elements** — With `CONTAINS_ELEMENT` and `HAS_LAYOUT` relationships
3. **Pattern Matching** — Query graph for patterns matching element composition
4. **SAP Component Mapping** — Graph query: element type → SAP component candidates
5. **Similarity Indexing** — Both structural (graph) and visual (ColPali) similarity

### 4.2 SAP Component Mapping Query

```cypher
MATCH (elem:UIElement {id: $elem_id})
MATCH (sc:SAPComponent)-[:USES_PATTERN]->(p:UIPattern)
WHERE sc.supported_element_types CONTAINS elem.element_type
  AND elem.attributes.sc_requirement IS NULL OR elem.attributes.sc_requirement = true
RETURN sc ORDER BY sc.complexity ASC
LIMIT 5
```

### 4.3 Similarity Queries

**Structural similarity (graph):**
```cypher
MATCH (a:UISketch {id: $query_id})-[:CONTAINS_ELEMENT]->(ae)
MATCH (b:UISketch)-[:CONTAINS_ELEMENT]->(be)
WHERE a <> b AND ae.element_type = be.element_type
WITH b, count(DISTINCT be.element_type) as overlap
RETURN b, overlap ORDER BY overlap DESC LIMIT 10
```

**Visual similarity (Qdrant):** ColPali vector search via existing infrastructure.

### 4.4 Indexing Strategy

| Index Type | Storage | Query Pattern |
|------------|---------|---------------|
| Vector (Qdrant) | UISketch embeddings + element descriptions | Visual similarity |
| Graph (FalkorDB) | Full UI structure, SAP components, patterns | "What implements X?" |
| Inverted (FalkorDB) | Element types, labels, pattern names | "Find all sketches with forms" |
| Entity Cache (Redis) | Frequent UISketch → SAPComponent mappings | Fast common pattern lookup |

### 4.5 UIIR Extension

```python
class UIIR(IRNode):
    # Existing
    artifact_type: ArtifactType = Field(default=ArtifactType.UI, frozen=True)
    ui_type: Optional[str]
    framework: Optional[str]
    component_name: Optional[str]
    image_urls: list[str]

    # New
    graph_node_id: Optional[str]
    element_count: int = 0
    pattern_matches: list[str]
    sap_candidates: list[str]
    visual_embedding_id: Optional[str]
```

---

## 5. Retrieval & Reasoning

### 5.1 Graph-First Retrieval

`RetrievalOrchestrator` gains `RetrievalSource.UI_SKETCH`:

```
Query: "How do I implement a table with filters?"
  ↓
Phase 1: Graph pattern match — Find UISketches with table+filter elements
Phase 2: SAP component candidates — What SAP controls implement table+filter?
Phase 3: Historical issues — Known problems with these components?
Phase 4: Similar patterns — Multi-hop: sketches → patterns → other implementations
  ↓
Fusion → Ranked context for Reasoner
```

### 5.2 Retrieval Query Types

| Query Intent | Strategy | Fallback |
|--------------|----------|----------|
| "Implement X" | Element type → SAPComponent match | Vector search on UI descriptions |
| "Show similar UIs" | Structural overlap + visual similarity | Text description match |
| "Fiori way to do X" | UIPattern → SAPComponent → guidelines | Doc retrieval |
| "Has anyone done X" | UISketch + USED_IN_PROJECT | Ticket retrieval |
| "Why not use X" | HAS_ISSUE relationships | Anti-pattern retrieval |

### 5.3 Adaptive Reasoning Engine

Extended `ReasoningAgent` with `UIImplementationMode`. Three detail levels:

| Level | User Pattern | Output |
|-------|-------------|--------|
| 1 (Overview) | "How would I implement..." | Component suggestions + reasoning |
| 2 (Detail) | "Show me code for X" | Level 1 + SAPUI5 code snippets |
| 3 (Full) | "Give me full implementation" | Level 2 + CAP services + structure + deployment |

```python
class UIReasoningState:
    query: str
    sketch_id: Optional[str]
    retrieved_context: dict
    current_detail_level: int
    suggestions: list[UISuggestion]
    drill_down_history: list[str]
```

### 5.4 New MCP Tool

```python
class UISuggestionTool(BaseTool):
    name = "ui_suggest_implementation"
    description = "Given a UI sketch (by ID or image), suggest SAP BTP implementation"
    # Parameters: ui_sketch_id or image_url, detail_level (1-3)
```

### 5.5 New API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ui/analyze` | POST | Analyze UI sketch image, return structured extraction + graph node ID |
| `/ui/suggest` | POST | Given sketch ID or image, get SAP BTP implementation suggestions |

---

## 6. Error Handling

| Failure Mode | Detection | Recovery |
|--------------|-----------|----------|
| VLM extraction fails | JSON parse failure / empty | Retry with simpler prompt → fallback to text-only |
| Low confidence (< 0.6 avg) | Confidence scores | Warn user: "Results are approximate" |
| No matching SAP components | Empty graph query | Vector search on SAP descriptions |
| No similar sketches | Structural overlap = 0 | Element-type-only suggestions |
| Graph builder fails | Cypher exception | Create UIIR with PARTIAL status, queue for retry |
| SAP knowledge stale | `last_ingestion` > 30 days | Health alert, flag suggestions |

---

## 7. Testing Strategy

### 7.1 Unit Tests

- `test_vlm_extractor.py` — JSON schema validation, retry logic, confidence
- `test_evidence_aggregator.py` — Multi-source merging, null handling
- `test_ui_graph_builder.py` — Cypher generation, ID dedup, relationships
- `test_ui_retriever.py` — Graph queries against known inputs

### 7.2 Integration Tests

- End-to-end: ingest sketch → extract → graph → retrieve → suggest → validate structure
- SAP component matching against known element types
- ColPali visual similarity for test image pairs

### 7.3 Evaluation Tests

`evaluation/test_ui_understanding.py`:
- 10 sample sketches (hand-drawn, Figma, screenshots)
- Ground truth annotations (expected elements, SAP components)
- Scoring: element F1, SAP component accuracy, suggestion quality

```python
test_case = {
    "sketch": "samples/table_with_filter.png",
    "expected_elements": [
        {"type": "table", "label": "Orders"},
        {"type": "input", "label": "Search/Filter"},
        {"type": "button", "label": "Go"}
    ],
    "expected_sap_candidates": ["sap.m.Table", "sap.ui.comp.filterbar.FilterBar"],
    "min_acceptable_score": 0.7
}
```

---

## 8. SAP BTP Knowledge Base Ingestion

New source type: `sap_documentation`.

```
POST /ingestion/sap_docs
  → SAPDocParser (parses HTML, PDF, markdown from SAP sources)
  → Creates SAPComponent/SAPService/UIPattern nodes
  → Links to existing code entities
  → Runs via cron or manual trigger
```

Parses:
- SAPUI5 API reference (component names, properties, events) — HTML/API format
- Fiori design guidelines (pattern definitions) — HTML/markdown
- BTP service documentation (capabilities, integrations) — HTML/markdown
- Internal company docs (company patterns, themes) — PDF/markdown/HTML

---

## 9. File Plan

### New Files

| File | Purpose |
|------|---------|
| `ui/vlm_extractor.py` | Structured VLM extraction with JSON enforcement |
| `ui/evidence_aggregator.py` | Merges VLM, ColPali, OCR into UIExtractionResult |
| `ui/graph_builder.py` | UIGraphBuilder — creates nodes, relationships, indexes |
| `ui/sap_doc_parser.py` | SAP documentation ingestion pipeline |
| `ui/models.py` | UISketch, UIElement, UILayout, UIPattern, SAPComponent dataclasses |
| `ui/retriever.py` | UIRetriever — graph-first retrieval |
| `ui/suggestion_tool.py` | UISuggestionTool MCP tool |
| `ui/sap_knowledge.py` | SAP component catalog management |
| `evaluation/test_ui_understanding.py` | Evaluation test suite |
| `tests/test_ui_*.py` | Unit tests for all new modules |

### Modified Files

| File | Changes |
|------|---------|
| `models/ir.py` | Extend `UIIR` with new fields |
| `multimodal/ir_builder.py` | `add_ui()` calls `UIGraphBuilder` |
| `documents/multimodal.py` | Update `extract_ui()` prompt |
| `documents/colpali.py` | Support UI image embeddings |
| `retrieval/orchestrator.py` | Add `RetrievalSource.UI_SKETCH` |
| `tools/base.py` | Add `UISuggestionTool` |
| `agents/planner.py` | Add `ui_implementation` intent |
| `api/main.py` | Add `/ui/analyze`, `/ui/suggest` endpoints |
| `ingestion/indexer.py` | ColPali embeddings for UISketch |

---

## 10. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| VLM hallucinates non-existent UI elements | High | Ground with confidence scores, fallback to text-only |
| SAP component knowledge becomes stale | Medium | Regular ingestion pipeline with health monitoring |
| Hand-drawn sketch extraction is poor | Medium | OCR fallback, explicit low-confidence warnings |
| Graph queries too complex/slow | Medium | Cache frequent queries, pre-compute similarity |
| Suggestions too generic | Medium | Company-specific pattern ingestion, ticket-based anti-patterns |

---

END OF SPECIFICATION
