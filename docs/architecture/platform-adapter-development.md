# Platform Adapter Development Guide

This guide covers creating a complete platform adapter with:
1. **Unified Ingestion** - Artifact parsing for indexing
2. **Reasoning Adapter** - Pattern matching, constraints, config generation
3. **Knowledge Layer** - Use cases, ADRs, ontology, taxonomy, UI components

The SAP BTP adapter serves as the reference implementation.

## Prerequisites

- Python 3.12+
- Understanding of artifact types for your platform
- Familiarity with Handler/HandlerResult pattern for ingestion
- Understanding of IRFeature, Pattern, Constraint for reasoning

## Architecture Overview

A complete platform adapter has **5 components**:

| Component | Purpose | Location |
|-----------|---------|----------|
| **Ingestion Handler** | Parse artifacts for indexing | `unified_ingestion/` |
| **Reasoning Adapter** | Match patterns, generate configs | `core/adapters/` |
| **Constraints** | Validate architectures | `core/constraints/` |
| **Knowledge Layer** | Use cases, ADRs, ontology | `core/knowledge/` |
| **UI Components** | Visual recognition | `core/ui/` |

## Step 1: Identify Your Artifacts

List the file types your platform uses and their detection patterns:

| Your Platform | File Patterns | Example Files |
|---------------|--------------|---------------|
| `myplatform` | `artifact1` | `artifact1.yaml`, `artifact1.json` |
| | `artifact2` | `config.artifact2` |

## Step 2: Create Handler File

Create `unified_ingestion/handlers/platform/myplatform.py`:

```python
"""MyPlatform artifact handlers."""

import json
import logging
from typing import Any, Dict, List

from unified_ingestion.handlers.base import Chunk, Handler, HandlerResult
from unified_ingestion.platform import PlatformArtifactHandler


logger = logging.getLogger(__name__)


class MyPlatformArtifactHandler(PlatformArtifactHandler):
    """Main handler that routes to specialized handlers."""

    def get_platform_id(self) -> str:
        return "myplatform"

    def get_supported_artifacts(self) -> List[str]:
        return ["artifact1", "artifact2"]

    async def handle(
        self,
        content: bytes,
        path: str,
        metadata: Dict[str, Any],
    ) -> HandlerResult:
        filename = path.lower()

        if "artifact1" in filename:
            handler = MyArtifact1Handler()
        elif "artifact2" in filename:
            handler = MyArtifact2Handler()
        else:
            return HandlerResult(
                success=False,
                chunks=[],
                error=f"Unknown MyPlatform artifact: {path}",
            )

        return await handler.handle(content, path, metadata)


class MyArtifact1Handler(Handler):
    """Handler for artifact1 files."""

    async def handle(
        self,
        content: bytes,
        path: str,
        metadata: Dict[str, Any],
    ) -> HandlerResult:
        try:
            text = content.decode("utf-8", errors="ignore")
            data = json.loads(text)

            artifact_id = data.get("id", "unknown")
            version = data.get("version", "1.0.0")

            chunks = [
                Chunk(
                    id=f"{path}:artifact1",
                    content=f"MyPlatform Artifact1: {artifact_id}",
                    chunk_index=0,
                    start_char=0,
                    end_char=len(text),
                    metadata={
                        "artifact_type": "artifact1",
                        "platform": "myplatform",
                        "artifact_id": artifact_id,
                    },
                )
            ]

            return HandlerResult(
                success=True,
                chunks=chunks,
                metadata={
                    "platform": "myplatform",
                    "artifact_type": "artifact1",
                    "artifact_id": artifact_id,
                    "version": version,
                },
            )
        except Exception as e:
            logger.warning(f"Artifact1 parsing failed for {path}: {e}")
            return HandlerResult(success=False, chunks=[], error=str(e))


class MyArtifact2Handler(Handler):
    """Handler for artifact2 files."""

    async def handle(
        self,
        content: bytes,
        path: str,
        metadata: Dict[str, Any],
    ) -> HandlerResult:
        try:
            text = content.decode("utf-8", errors="ignore")
            return HandlerResult(
                success=True,
                chunks=[],
                metadata={"platform": "myplatform", "artifact_type": "artifact2"},
            )
        except Exception as e:
            logger.warning(f"Artifact2 parsing failed for {path}: {e}")
            return HandlerResult(success=False, chunks=[], error=str(e))
```

## Step 3: Add to package exports

Edit `unified_ingestion/handlers/platform/sap.py` to add your exports, or add your own module:

```python
"""Platform artifact handlers."""

from unified_ingestion.handlers.platform.sap import (
    MTAHandler,
    CDSHandler,
    CAPPackageHandler,
    SecurityConfigHandler,
)
from unified_ingestion.handlers.platform.myplatform import (
    MyPlatformArtifactHandler,
    MyArtifact1Handler,
    MyArtifact2Handler,
)

__all__ = [
    "MTAHandler",
    "CDSHandler",
    "CAPPackageHandler",
    "SecurityConfigHandler",
    "MyPlatformArtifactHandler",
    "MyArtifact1Handler",
    "MyArtifact2Handler",
]
```

## Step 4: Register in Platform Registry

Edit `unified_ingestion/platform/__init__.py`:

```python
def get_platform_registry() -> PlatformArtifactRegistry:
    global _platform_registry
    if _platform_registry is None:
        _platform_registry = PlatformArtifactRegistry()
        _platform_registry.register(SAPBTPArtifactHandler())
        _platform_registry.register(MyPlatformArtifactHandler())  # Add this
        _platform_registry.register(PowerPlatformArtifactHandler())
        _platform_registry.register(AWSArtifactHandler())
        _platform_registry.register(AzureArtifactHandler())
    return _platform_registry
```

## Step 5: Add Platform Detection Markers

Edit `detect_platform()` in `PlatformArtifactRegistry`:

```python
def detect_platform(self, path: str, content: Optional[bytes] = None) -> Optional[str]:
    filename = unquote(Path(path).name).lower()

    # Existing detection...
    
    # Add your platform markers
    if any(marker in filename for marker in ["myplatform", "artifact1", "artifact2"]):
        return "myplatform"

    return None
```

## Step 6: Test Your Adapter

```python
import asyncio
from unified_ingestion.platform import get_platform_registry

registry = get_platform_registry()

# Test detection
assert registry.detect_platform("artifact1.yaml") == "myplatform"
assert registry.detect_platform("config.artifact2") == "myplatform"

# Test handler
handler = registry.get("myplatform")
result = asyncio.run(handler.handle(
    b'{"id": "test", "version": "1.0.0"}',
    "artifact1.yaml",
    {},
))
assert result.success == True
```

## Handler Pattern Reference

### HandlerResult Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Whether parsing succeeded |
| `chunks` | `List[Dict]` | Extracted content chunks |
| `entities` | `List[Dict]` | Extracted entities |
| `relationships` | `List[Dict]` | Extracted relationships |
| `error` | `Optional[str]` | Error message if failed |
| `metadata` | `Dict[str, Any]` | Parsed metadata |

### Chunk Structure

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique chunk identifier |
| `content` | `str` | Chunk text content |
| `chunk_index` | `int` | Position in document |
| `start_char` | `int` | Start character position |
| `end_char` | `int` | End character position |
| `metadata` | `Dict` | Chunk-specific metadata |

### PlatformArtifactHandler Interface

```python
class PlatformArtifactHandler(Handler):
    @abstractmethod
    def get_platform_id(self) -> str:
        """Return platform identifier (e.g., 'sap', 'aws')."""
    
    @abstractmethod
    def get_supported_artifacts(self) -> List[str]:
        """Return list of supported artifact type names."""

    @abstractmethod
    async def handle(
        self,
        content: bytes,
        path: str,
        metadata: Dict[str, Any],
    ) -> HandlerResult:
        """Route to appropriate artifact handler."""
```

## Common Patterns

### YAML Parsing

```python
import yaml

data = yaml.safe_load(content.decode("utf-8"))
```

### JSON Parsing

```python
data = json.loads(content.decode("utf-8"))
```

### Multi-file Archives

```python
import zipfile

with zipfile.ZipFile(io.BytesIO(content)) as zf:
    for name in zf.namelist():
        with zf.open(name) as f:
            # process each file
            pass
```

### Error Handling

Always return a HandlerResult with success=False on error:

```python
except Exception as e:
    logger.warning(f"Parsing failed for {path}: {e}")
    return HandlerResult(success=False, chunks=[], error=str(e))
```

## Part 2: Reasoning Adapter (core/adapters/)

Create `core/adapters/myplatform.py`:

```python
"""MyPlatform adapter for reasoning and generation."""

from typing import Any, Dict, List, Optional
from core.adapters.base import AdapterInput, AdapterOutput, PlatformAdapter
from core.patterns.schema import Pattern, get_pattern_library
from core.constraints.engine import get_constraint_engine


class MyPlatformAdapter(PlatformAdapter):
    @property
    def platform_id(self) -> str:
        return "myplatform"

    @property
    def supported_services(self) -> List[str]:
        return ["service1", "service2", "service3"]

    @property
    def patterns(self) -> List[Pattern]:
        library = get_pattern_library()
        patterns = [
            Pattern(
                id="myplatform_pattern1",
                name="MyPlatform Pattern 1",
                domain="architecture",
                triggers=["trigger1", "trigger2"],
                conditions=[],
                components=["component1", "component2"],
                benefits=["Benefit 1", "Benefit 2"],
                tradeoffs=["Tradeoff 1"],
                priority=8,
                confidence=0.85,
            ),
        ]
        for p in patterns:
            library.register(p)
        return patterns

    @property
    def constraints(self) -> Any:
        return get_constraint_engine()._constraint_sets.get("myplatform")

    def transform_ir_to_platform(self, input: AdapterInput) -> AdapterOutput:
        features = input.ir_features
        pattern_results = input.pattern_matches
        violations = input.constraint_violations

        config_templates = self.generate_config(features)
        code_snippets = self.generate_code(features)
        recommendations = self._build_recommendations(pattern_results, features, violations)

        can_deploy = not any(v.severity == "error" for v in violations)
        confidence = sum(p.match_score for p in pattern_results) / max(1, len(pattern_results))

        return AdapterOutput(
            recommendations=recommendations,
            config_templates=config_templates,
            code_snippets=code_snippets,
            explanation=self._explain(recommendations, violations),
            confidence=confidence,
            can_deploy=can_deploy,
        )

    def generate_config(self, features=None) -> Dict[str, str]:
        return {}

    def generate_code(self, features=None) -> Dict[str, str]:
        return {}
```

Register in `core/adapters/__init__.py`:

```python
from core.adapters.base import AdapterRegistry
from core.adapters.sap import SAPBTPAdapter
from core.adapters.myplatform import MyPlatformAdapter

_registry: AdapterRegistry = None

def _ensure_registry() -> AdapterRegistry:
    global _registry
    if _registry is None:
        _registry = AdapterRegistry()
        _registry.register(SAPBTPAdapter())
        _registry.register(MyPlatformAdapter())
    return _registry

def get_adapter_registry() -> AdapterRegistry:
    return _ensure_registry()
```

## Part 3: Platform Constraints (core/constraints/)

Add constraint set to `core/constraints/platforms/myplatform.py`:

```python
from core.constraints.engine import ConstraintSet, Constraint

MYPLATFORM_CONSTRAINTS = ConstraintSet(
    id="myplatform",
    name="MyPlatform Constraints",
    description="Platform-specific constraints",
    constraints=[
        Constraint(
            id="myplatform_service_limit",
            name="Service Limit",
            domain="operations",
            type="limit",
            feature="service_count",
            operator="<=",
            threshold=10,
            message="Maximum 10 services allowed",
            fix_hint="Use service consolidation",
            severity="warning",
            platforms=["myplatform"],
        ),
    ],
)
```

Register in `core/constraints/engine.py` (or wherever the engine is initialized):

```python
from core.constraints.engine import get_constraint_engine
from core.constraints.platforms.myplatform import MYPLATFORM_CONSTRAINTS

engine = get_constraint_engine()
engine.register_constraint_set(MYPLATFORM_CONSTRAINTS)
```

## Part 4: Platform Knowledge (core/knowledge/)

### Use Cases

Add `core/knowledge/usecases/myplatform.py`:

```python
from core.knowledge.usecases import UseCase, UseCaseCategory, UseCasePriority

MYPLATFORM_USE_CASES = [
    UseCase(
        id="myplatform_integration",
        name="MyPlatform Integration",
        description="Integrate with MyPlatform services",
        category=UseCaseCategory.INTEGRATION,
        priority=UseCasePriority.HIGH,
        platforms=["myplatform"],
        patterns=["myplatform_pattern1"],
        acceptance_criteria=["Service connected", "Data flowing"],
    ),
]
```

### ADRs

Add `core/knowledge/adrs/myplatform.py`:

```python
from core.knowledge.adrs import ADR, ADRStatus

MYPLATFORM_ADRS = [
    ADR(
        id="adr-001",
        title="Use MyPlatform for real-time data",
        status=ADRStatus.ACCEPTED,
        context="Need real-time processing",
        decision="Use MyPlatform streaming service",
        consequences="Benefits: Low latency. Tradeoffs: Cost",
        related_platforms=["myplatform"],
    ),
]
```

### Ontology & Taxonomy

Add entity types and relationships:

```python
from core.knowledge.ontology import ExtractedEntity

MYPLATFORM_ONTOLOGY = {
    "Service": {"type": "service", "properties": ["name", "endpoint", "region"]},
    "Component": {"type": "component", "properties": ["name", "version"]},
    "API": {"type": "api", "properties": ["endpoint", "methods", "auth"]},
}

MYPLATFORM_RELATIONSHIPS = [
    ("Service", "Component", "contains"),
    ("Component", "API", "exposes"),
]
```

Register in knowledge graph:

```python
def register_myplatform_knowledge():
    from core.knowledge.graph import get_knowledge_graph
    kg = get_knowledge_graph()
    for entity, data in MYPLATFORM_ONTOLOGY.items():
        kg.add_entity(f"myplatform:{entity}", entity, data)
```

## Part 5: UI Component Library (UI Recognition)

Define UI components for visual recognition:

```python
MYPLATFORM_UI_COMPONENTS = {
    "Button": {
        "type": "component",
        "library": "myplatform-ui",
        "properties": ["variant", "size", "disabled"],
        "children": [],
    },
    "DataTable": {
        "type": "component", 
        "library": "myplatform-ui",
        "properties": ["columns", "dataSource", "sortable"],
        "children": ["columns"],
    },
    "Form": {
        "type": "component",
        "library": "myplatform-ui", 
        "properties": ["layout", "validation"],
        "children": ["fields"],
    },
}

def get_ui_component_library(platform: str) -> Dict:
    return MYPLATFORM_UI_COMPONENTS
```

## Complete File Structure

```
core/
├── adapters/
│   ├── __init__.py           # Registry
│   ├── sap.py               # SAP BTP adapter
│   ├── template.py          # Reasoning adapter template
│   └── myplatform.py       # Your platform adapter
├── constraints/
│   ├── engine.py          # Constraint engine
│   └── platforms/
│       └── myplatform.py  # Platform constraints
├── knowledge/
│   ├── usecases.py       # Use case registry
│   ├── adrs.py          # ADR registry
│   ├── ontology.py       # Entity ontology
│   ├── taxonomy.py       # Pattern taxonomy
│   ├── graph.py         # Knowledge graph
│   └── myplatform.py   # Platform knowledge template
└── ui/
    └── myplatform.py    # UI component library

unified_ingestion/
├── handlers/
│   ├── platform/
│   │   ├── sap.py
│   │   └── myplatform.py
│   └── platform/
│       └── __init__.py
└── platform/
    └── __init__.py        # Platform detection
```

## Testing Complete Adapter

```python
from core.adapters import get_adapter_registry
from unified_ingestion.platform import get_platform_registry

# Test reasoning adapter
adapter = get_adapter_registry().get("myplatform")
print(f"Services: {adapter.supported_services}")
print(f"Patterns: {[p.id for p in adapter.patterns]}")

# Test ingestion handler
registry = get_platform_registry()
handler = registry.get("myplatform")
print(f"Artifacts: {handler.get_supported_artifacts()}")

# Test knowledge
from core.knowledge.usecases import get_use_case_library
usecases = get_use_case_library().list_by_platform("myplatform")
print(f"Use cases: {[uc.id for uc in usecases]}")
```

## Next Steps

- Add tests in `tests/test_platform_*.py`
- Add schema validation using Pydantic models
- Add FalkorDB entity indexing
- Document artifact types in `docs/platform-adapter-architecture.md`