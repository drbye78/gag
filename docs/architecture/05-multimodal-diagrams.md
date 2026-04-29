# Multimodal & Diagram Understanding Architecture

The system provides multimodal understanding through VLM processing, diagram parsing, and visual embeddings. This document covers the components and capabilities.

## Architecture Overview

```
Image/Diagram → VLM Processing → Entity Extraction → Vector Index
                                           ↓
                                    Graph Index (FalkorDB)
                                           ↓
                          Query → Visual Retrieval
```

### Processing Pipeline

```
1. Input: Image/Diagram (PNG, JPEG, PDF, SVG)
2. Format Detection: Magic bytes detection
3. Preprocessing: Resize, normalize, convert to RGB
4. VLM Inference: Qwen2-VL or OpenAI GPT-4o
5. Entity Extraction: Parser-specific (UML, C4, BPMN, etc.)
6. Text Extraction: OCR if needed (PDF)
7. Indexing: Qdrant (vectors) + FalkorDB (graph)
8. Retrieval: Visual similarity + text search
```

## VLM Processing (`multimodal/`)

### VLM Providers (`multimodal/vlm.py`)

| Provider | Model | Language Support | Speed |
|----------|-------|------------------|-------|
| Qwen (default) | Qwen2-VL | Multilingual | Fast |
| OpenAI | gpt-4o | English | Medium |

### Configuration

```python
# Environment variables
VLM_PROVIDER=qwen          # or "openai"
VLM_MODEL=qwen2-vl-2b     # or "gpt-4o"
VLM_API_KEY=your-key       # for OpenAI
```

### VLM Processor

```python
from multimodal import VLMProcessor, VLMProvider

# Initialize with provider
processor = VLMProcessor(provider="qwen")

# Process image
response = await processor.process_image(
    image_data=image_bytes,
    prompt="Describe this architecture diagram"
)

# Response contains:
# - text: extracted text description
# - entities: detected entities
# - confidence: detection confidence
```

### VLM Response Structure

```python
class VLMResponse(BaseModel):
    text: str                          # Full text description
    entities: List[Dict[str, Any]]    # Extracted entities
    relationships: List[Dict[str, Any]] # Detected relationships
    confidence: float                  # Overall confidence (0-1)
    language: str                      # Detected language
```

## Diagram Formats

### Supported Formats (`documents/diagram_parser.py`)

| Format | Parser | Entities Extracted | File |
|--------|--------|-------------------|------|
| UML Class | `UMLParser` | Classes, attributes, methods, relationships | `uml_parser.py` |
| UML Sequence | `SequenceParser` | Actors, messages, lifelines | `sequence_parser.py` |
| UML Component | `ComponentParser` | Components, interfaces, ports | `component_parser.py` |
| UML Activity | `ActivityParser` | Activities, decisions, flows | `activity_parser.py` |
| UML State | `StateParser` | States, transitions, events | `state_parser.py` |
| C4 | `C4Parser` | Person, System, Container, Component | `c4_parser.py` |
| BPMN 2.0 | `BPMNParser` | Processes, tasks, gateways, events | `bpmn_parser.py` |
| PlantUML | `PlantUMLParser` | Actors, rectangles, arrows | `plantuml_parser.py` |
| Mermaid | `MermaidParser` | Flowcharts, sequence, class, state | `mermaid_parser.py` |
| Draw.io | `DrawioParser` | Shapes, connectors, labels | `drawio_parser.py` |
| OpenAPI | `OpenAPIParser` | Paths, methods, schemas, parameters | `openapi_parser.py` |

### Parser Details

#### UML Class Parser
```python
# Extracts: class name, attributes, methods, visibility, relationships
parser = UMLParser()
result = await parser.parse_file("class_diagram.png")

# Output:
{
    "classes": [
        {
            "name": "UserService",
            "attributes": [
                {"name": "id", "type": "UUID", "visibility": "private"},
                {"name": "email", "type": "str", "visibility": "private"}
            ],
            "methods": [
                {"name": "create_user", "params": ["email"], "visibility": "public"}
            ]
        }
    ],
    "relationships": [
        {"from": "UserService", "to": "Database", "type": "USES"}
    ]
}
```

#### C4 Parser
```python
# Extracts: C4 levels (Context, Container, Component, Code)
parser = C4Parser()
result = await parser.parse_file("c4-diagram.png")

# Output:
{
    "people": [{"name": "Customer", "description": "End user"}],
    "systems": [{"name": "BankingSystem", "description": "Core banking"}],
    "containers": [
        {"name": "WebApp", "technology": "React", "description": "Frontend"}
    ]
}
```

#### BPMN Parser
```python
# Extracts: processes, tasks, gateways, events, flows
parser = BPMNParser()
result = await parser.parse_file("process.bpmn")

# Output:
{
    "processes": [{"id": "order_process", "name": "Order Processing"}],
    "tasks": [
        {"id": "task1", "name": "Verify Order", "type": "SERVICE_TASK"}
    ],
    "gateways": [
        {"id": "gw1", "name": "Payment OK?", "type": "EXCLUSIVE"}
    ],
    "flows": [{"from": "task1", "to": "gw1", "condition": "verified"}]
}
```

#### Mermaid Parser
```python
# Supports: flowchart, sequence, classDiagram, stateDiagram, er, gantt
parser = MermaidParser()
result = await parser.parse("""
    graph TD
        A[Start] --> B{Decision}
        B -->|Yes| C[Process]
        B -->|No| D[End]
""")

# Output:
{
    "nodes": [
        {"id": "A", "label": "Start", "type": "start"},
        {"id": "B", "label": "Decision", "type": "decision"}
    ],
    "edges": [
        {"from": "A", "to": "B"},
        {"from": "B", "to": "C", "label": "Yes"},
        {"from": "B", "to": "D", "label": "No"}
    ]
}
```

## Image Format Support

| Format | Support | Notes |
|--------|---------|-------|
| PNG | ✅ Full | Primary format |
| JPEG | ✅ Full | Photos, screenshots |
| PDF | ✅ Full | Vector and raster via PyMuPDF |
| WebP | ✅ Full | Modern format |
| SVG | ⚠️ Partial | Path extraction only |
| TIFF | ✅ Full | Multi-page |
| BMP | ✅ Full | Raster only |

### Image Processing

```python
from documents import ImageProcessor

processor = ImageProcessor()

# Process image with format conversion
result = await processor.process(
    input_path="diagram.pdf",
    output_format="png",
    max_size=(2048, 2048)
)
```

### Processing Options

| Option | Default | Description |
|--------|---------|-------------|
| `max_width` | 2048 | Maximum image width |
| `max_height` | 2048 | Maximum image height |
| `normalize` | true | Normalize colors |
| `background` | white | Background color for transparency |

### Limitations

| Issue | Severity | Workaround |
|-------|----------|------------|
| Scanned PDFs | High | Pre-process with OCR |
| Complex UML | Medium | Simplify diagrams |
| Hand-drawn sketches | Medium | Use clearer images |
| Nested containers | Low | Flatten hierarchy |
| Color-only indicators | Low | Add text labels |

## Visual Embeddings (ColPali)

### ColPali Integration (`documents/colpali.py`)

ColPali provides visual embeddings for semantic image search:

| Component | Purpose | File |
|-----------|---------|------|
| `ColPaliIndexer` | Generate visual embeddings | `colpali.py` |
| `ColPaliRetriever` | Search by visual similarity | `colpali.py` |
| `ColBERTIndexer` | Late interaction embeddings | `colbert.py` |
| `ColBERTRetriever` | Hybrid text + visual search | `colbert.py` |

### Architecture

```
Query → ColPali Encoder → Query Embeddings
                    ↓
Image → ColPali Encoder → Image Embeddings
                    ↓
Similarity Search → Top-K Results
```

### Usage

```python
from documents import ColPaliIndexer, ColPaliRetriever

# Index UI sketch
indexer = ColPaliIndexer()
await indexer.index_sketch(
    image_data=sketch_bytes,
    metadata={"component": "button", "style": "primary"}
)

# Search by visual similarity
retriever = ColPaliRetriever()
results = await retriever.search(
    query="button with icon",
    visual_similarity=True,
    limit=10
)
```

## UI Sketch Retrieval (`ui/`)

The UI Sketch retrieval system finds similar UI components from design sketches:

### Supported UI Elements

| Element | Patterns | File |
|---------|----------|------|
| Button | `.btn`, `button`, `submit` | `ui/button.py` |
| Input | `input`, `textarea`, `field` | `ui/input.py` |
| Table | `table`, `grid`, `datagrid` | `ui/table.py` |
| List | `ul`, `ol`, `listview` | `ui/list.py` |
| Card | `card`, `panel`, `tile` | `ui/card.py` |
| Navigation | `nav`, `menu`, `toolbar` | `ui/navigation.py` |
| Dialog | `modal`, `dialog`, `popup` | `ui/dialog.py` |
| Form | `form`, `fieldset` | `ui/form.py` |

### Usage

```python
from ui import UIRetriever

retriever = UIRetriever()

# Search UI sketches by element type
results = await retriever.search_by_element(
    element_type="button",
    style_patterns=["primary", "outline"],
    limit=10
)

# Combined search
results = await retriever.search_combined(
    element_types=["button", "input"],
    style_patterns=["primary", "outline"],
    limit=10
)

# Structural similarity search
results = await retriever.search_structural(
    sketch_path="button-design.png",
    similarity_threshold=0.8
)
```

### Search Options

| Option | Type | Description |
|--------|------|-------------|
| `element_type` | str | Filter by element type |
| `style_patterns` | List[str] | Filter by style |
| `color_scheme` | str | Filter by color |
| `layout` | str | Filter by layout type |
| `similarity_threshold` | float | Minimum similarity (0-1) |

## Graph Indexing (FalkorDB)

### Entity-relationship Storage

FalkorDB stores extracted diagram entities and relationships for graph-based retrieval:

```python
from graph import FalkorDBClient

client = FalkorDBClient()

# Index extracted entities from diagram
client.execute("""
    CREATE (c:Component {name: "API Gateway"})
    CREATE (s:Service {name: "UserService"})
    CREATE (c)-[:ROUTES_TO]->(s)
    CREATE (s)-[:RETURNS]->(token:Token {type: "JWT"})
""")

# Query relationships
results = client.execute("""
    MATCH (c:Component)-[r]->(s:Service)
    RETURN c.name, type(r), s.name
""")
```

### Schema

| Node | Properties | Description |
|------|------------|-------------|
| `Component` | name, type, technology | System components |
| `Actor` | name, role, description | Actors/users |
| `Process` | name, id, type | Business processes |
| `Container` | name, technology | Application containers |

| Relationship | Description |
|--------------|-------------|
| `ROUTES_TO` | Request routing |
| `DEPENDS_ON` | Dependency |
| `USES` | Service usage |
| `RETURNS` | Return type |

### Graph Query Examples

```python
# Find all components that depend on a service
results = client.execute("""
    MATCH (c:Component)-[:DEPENDS_ON]->(s:Service {name: $service})
    RETURN c.name
""", service="Database")

# Find path between components
results = client.execute("""
    MATCH path = (a:Component)-[:DEPENDS_ON*]->(b:Component)
    WHERE a.name = "Frontend" AND b.name = "Database"
    RETURN path
""")
```

### Supported Edge Types

| Edge | Description |
|------|-------------|
| `ROUTES_TO` | Request routing |
| `CONTAINS_ELEMENT` | UI hierarchy |
| `DEPENDS_ON` | Dependency |
| `SIBLING_OF` | Layout relationship |
| `LINKED_TO` | External link |
| `DOCUMENTED_BY` | Documentation reference |

## Multimodal Queries

### Query Types

| Query | Example | Processing |
|-------|---------|-------------|
| `visual` | "Show me a button like this" | Visual similarity |
| `text` | "Find login forms" | Keyword search |
| `hybrid` | "Button with icon" | Combined |

### Example Query Flow

```python
# Hybrid query combining visual and text
result = await orchestrator.retrieve(
    query="Find dashboard components with charts",
    sources=["diagram", "ui_sketch"],
    hybrid=True
)
```

## Image Processing Pipeline

```
1. Load Image (PyMuPDF/Pillow)
2. Detect Format (magic bytes)
3. Preprocess (resize, normalize)
4. VLM Inference (Qwen/OpenAI)
5. Extract Entities (diagram parser)
6. Extract Text (OCR if needed)
7. Index (Qdrant + FalkorDB)
```

## Configuration

| Env Variable | Default | Purpose |
|--------------|---------|---------|
| `VLM_PROVIDER` | qwen | VLM provider |
| `VLM_MODEL` | qwen2-vl-2b | Model name |
| `COLPALI_ENABLED` | false | Enable visual embeddings |
| `DIAGRAM_FORMATS` | uml,c4,bpmn,mermaid | Supported formats |
| `OCR_ENABLED` | false | Enable OCR for scanned docs |
| `MAX_IMAGE_SIZE` | 5242880 | Max 5MB |

## Limitations and Known Issues

| Issue | Severity | Workaround |
|-------|----------|------------|
| Scanned PDFs | High | Manual OCR preprocessing |
| Complex UML | Medium | Simplify diagrams |
| Hand-drawn sketches | Medium | Use clearer images |
| Nested containers | Low | Flatten hierarchy |
| Color-only indicators | Low | Add text labels |

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/multimodal/extract` | POST | Extract text from images |
| `/search/diagram` | POST | Search diagrams |
| `/search/ui-sketch` | POST | Search UI sketches |
| `/search/colpal` | POST | ColPali visual search |