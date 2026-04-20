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

## VLM Processing (`multimodal/`)

### VLM Providers (`multimodal/vlm.py`)

| Provider | Model | Language Support |
|----------|-------|------------------|
| Qwen (default) | Qwen2-VL | Multilingual |
| OpenAI | gpt-4o | English |

### VLM Processor

```python
class VLMProcessor:
    def __init__(self, provider: str = "qwen"):
        self.provider = get_vlm_provider(provider)

    async def process_image(
        self,
        image_data: bytes,
        prompt: str = "Describe this image in detail"
    ) -> VLMResponse:
        # Extract text from image via VLM
        return await self.provider.generate(prompt, image_data)
```

## Diagram Formats

### Supported Formats (`documents/diagram_parser.py`)

| Format | Parser | Entities Extracted |
|--------|--------|------------------|
| UML Class | `UMLParser` | Classes, attributes, methods, relationships |
| UML Sequence | `SequenceParser` | Actors, messages, lifelines |
| UML Component | `ComponentParser` | Components, interfaces, ports |
| UML Activity | `ActivityParser` | Activities, decisions, flows |
| UML State | `StateParser` | States, transitions, events |
| C4 | `C4Parser` | Person, System, Container, Component |
| BPMN 2.0 | `BPMNParser` | Processes, tasks, gateways, events |
| PlantUML | `PlantUMLParser` | Actors, rectangles, arrows |
| Mermaid | `MermaidParser` | Flowcharts, sequence, class, state |
| Draw.io | `DrawioParser` | Shapes, connectors, labels |
| OpenAPI | `OpenAPIParser` | Paths, methods, schemas, parameters |

### Diagram Entity Types

| Type | Description | Example |
|------|-------------|---------|
| `COMPONENT` | System component | "Database", "API Gateway" |
| `ACTOR` | User/role | "Admin", "Customer" |
| `CONNECTION` | Data flow | "API → Database" |
| `CONTAINER` | Application container | "Web App", "Mobile App" |
| `PROCESS` | Business process | "Order Processing" |
| `DECISION` | Decision point | "Is valid?" |
| `STATE` | System state | "Logged In" |

### Parsing Example

```python
parser = UMLParser()
diagram = await parser.parse_file("architecture.puml")

results = {
    "entities": [
        {"type": "COMPONENT", "name": "UserService", "properties": ["id", "name", "email"]},
        {"type": "COMPONENT", "name": "OrderService", "properties": ["id", "user_id"]}
    ],
    "relationships": [
        {"from": "UserService", "to": "OrderService", "type": "DEPENDS_ON"}
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

### Limitations

1. **Scanned PDFs**: Require OCR (not currently supported)
2. **Complex diagrams**: Lower accuracy for nested elements
3. **Hand-drawn sketches**: Variable accuracy
4. **Multi-page PDFs**: Processed page-by-page

## Visual Embeddings (ColPali)

### ColPali Integration (`ui/`, `colbert.py`)

| Component | Purpose |
|-----------|---------|
| `ColPaliIndexer` | Generate visual embeddings |
| `ColPaliRetriever` | Search by visual similarity |
| `ColBERTIndexer` | Late interaction embeddings |
| `ColBERTRetriever` | Hybrid text + visual search |

### Usage

```python
# Index UI sketch
indexer = get_colpali_indexer()
await indexer.index_sketch(
    image_data=sketch_bytes,
    metadata={"component": "button", "style": "primary"}
)

# Search by visual similarity
retriever = get_colpali_retriever()
results = await retriever.search(
    query="button with icon",
    visual_similarity=True,
    limit=10
)
```

## UI Sketch Retrieval (`ui/`)

### Supported UI Elements

| Element | Patterns |
|---------|----------|
| Button | `.btn`, `button`, `submit` |
| Input | `input`, `textarea`, `field` |
| Table | `table`, `grid`, `datagrid` |
| List | `ul`, `ol`, `listview` |
| Card | `card`, `panel`, `tile` |
| Navigation | `nav`, `menu`, `toolbar` |
| Dialog | `modal`, `dialog`, `popup` |
| Form | `form`, `fieldset` |

### Extraction

```python
retriever = get_ui_retriever()
results = await retriever.search_combined(
    element_types=["button", "input"],
    style_patterns=["primary", "outline"],
    limit=10
)
```

## Graph Indexing (FalkorDB)

### Entity-relationship Storage

```cypher
CREATE (c:Component {name: "API Gateway"})
CREATE (s:Service {name: "UserService"})
CREATE (c)-[:ROUTES_TO]->(s)
CREATE (s)-[:RETURNS]->(token:Token {type: "JWT"})
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