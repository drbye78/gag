# Unified Ingestion Architecture

The unified_ingestion package provides a unified pipeline for handling all artifact types through pluggable handlers with platform-specific extension support.

## Overview

```
Artifact → Platform Detection → Handler Selection → Parse → Chunk → Index
                                              ↓
                                    PlatformArtifactHandler (SAP, AWS, Azure)
```

## Core Components

### 1. Handler Registry (`core/registry.py`)

Central registry for all artifact handlers:

```python
class HandlerRegistry:
    def register(artifact_type: ArtifactType, handler: Handler) -> None
    def get(artifact_type: ArtifactType) -> Optional[Handler]
    def get_handler_for_path(path: str) -> Optional[Tuple[Handler, ArtifactType]]
```

### 2. Platform Artifact Registry (`platform/__init__.py`)

Registry for platform-specific handlers:

```python
class PlatformArtifactRegistry:
    def register(handler: PlatformArtifactHandler) -> None
    def get(platform_id: str) -> Optional[PlatformArtifactHandler]
    def detect_platform(path: str, content: Optional[bytes] = None) -> Optional[str]
```

## Handler Hierarchy

```
Handler (ABC)
├── DocumentHandler       # docx, xlsx, pptx, pdf
├── MarkdownHandler       # markdown
├── SourceCodeHandler    # programming languages
├── ConfigHandler       # yaml, json, toml
├── KubernetesHandler   # k8s manifests
├── DiagramHandler     # PlantUML, Mermaid, draw.io
└── PlatformArtifactHandler (ABC)
    ├── SAPBTPArtifactHandler
    ├── PowerPlatformArtifactHandler
    ├── AWSArtifactHandler
    └── AzureArtifactHandler
```

## Supported Artifacts (33 Types)

| Artifact Type | Handler | Platform |
|--------------|--------|----------|
| `document` | DocumentHandler | - |
| `markdown` | MarkdownHandler | - |
| `source_code` | SourceCodeHandler | - |
| `yaml` | ConfigHandler | - |
| `json` | ConfigHandler | - |
| `mta` | MTAHandler | SAP |
| `cds` | CDSHandler | SAP |
| `cap_package` | CAPPackageHandler | SAP |
| `security` | SecurityConfigHandler | SAP |
| `cloudformation` | CloudFormationHandler | AWS |
| `cdk` | CDKHandler | AWS |
| `bicep` | BicepHandler | Azure |
| `terraform` | TerraformHandler | Azure |

## Platform Detection

Platform detection uses filename/path markers:

| Platform | Markers |
|----------|---------|
| SAP | `mta`, `mtad`, `cds`, `xs-security`, `sap`, `btp`, `package` |
| PowerPlatform | `powerapps`, `powerautomate`, `powerpages`, `dataverse` |
| AWS | `cloudformation`, `cdk`, `sam`, `amplify`, `aws` |
| Azure | `bicep`, `arm`, `azure`, `logicapp`, `funcapp` |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /artifacts/ingest` | Ingest single artifact |
| `POST /artifacts/batch` | Batch ingest |
| `POST /artifacts/zip` | Ingest ZIP archive |
| `POST /artifacts/git` | Ingest git repository |
| `GET /artifacts/formats` | Supported formats |
| `GET /artifacts/types` | Artifact types enum |

## Implementation Files

```
unified_ingestion/
├── __init__.py              # Package exports
├── core/
│   ├── types.py            # ArtifactType enum (33 types)
│   ├── job.py             # IngestionJob, JobStatus
│   └── registry.py        # HandlerRegistry
├── platform/
│   └── __init__.py       # PlatformArtifactRegistry
├── handlers/
│   ├── base.py           # Handler, HandlerResult, Chunk
│   ├── document.py       # DocumentHandler
│   ├── markdown.py      # MarkdownHandler
│   ├── config.py       # ConfigHandler
│   ├── platform/
│   │   ��── __init__.py
│   │   └── sap.py      # MTAHandler, CDSHandler, CAPPackageHandler, SecurityConfigHandler
│   ├── k8s.py         # KubernetesHandler
│   ├── diagram.py      # DiagramHandler
│   ├── confluence.py  # ConfluenceAttachmentHandler
│   └── ...
└── api.py              # FastAPI endpoints
```

## Key Design Decisions

1. **Platform detection by path first**: Avoids expensive content parsing for detection
2. **Handler as async**: Enables parallel processing
3. **Extensible registry**: New platforms add via `register()` method
4. **HandlerResult includes success flag**: Enables error tracking without exceptions