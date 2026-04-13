"""
Documents Module - Document ingestion subsystem.

Provides document parsing, versioning, Confluence sync,
WebDAV sync, and multimodal processing.
"""

from documents.models import Document, DocumentVersion, DocumentSource
from documents.parse import (
    LlamaIndexParser,
    DoclingParser,
    FallbackParser,
    HybridDocumentParser,
    ParsedDocumentResult,
)
from documents.layout import (
    LayoutType,
    LayoutBlock,
    LayoutAnalysisResult,
    StructureAnalysisResult,
    PDFLayoutAnalyzer,
    DOCXStructureAnalyzer,
    XLSXStructureAnalyzer,
    PPTXStructureAnalyzer,
    UnifiedLayoutParser,
    get_layout_parser,
)

# ColPali requires torch — lazy import to avoid hard dependency
try:
    from documents.colpali import (
        ColPaliClient,
        ColPaliModel,
        ColPaliEmbedding,
        ColPaliResult,
        get_colpali_client,
    )
except ImportError:
    pass
# Diagram parsing requires Pillow — lazy import to avoid hard dependency
try:
    from documents.diagram_parser import (
        DiagramType,
        UMLClass,
        UMLRelationship,
        SequenceMessage,
        C4Container,
        DiagramExtractionResult,
        DiagramTypeDetector,
        UMLClassExtractor,
        UMLSequenceExtractor,
        C4ContainerExtractor,
        UMLActivityExtractor,
        UMLStateMachineExtractor,
        UMLPackageExtractor,
        UMLObjectExtractor,
        UMLUseCaseExtractor,
        ERDExtractor,
        PlantUMLGenerator,
        MermaidGenerator,
        UnifiedDiagramParser,
        get_diagram_parser,
    )
except ImportError:
    pass
from documents.confluence import ConfluenceClient, ConfluencePage
from documents.webdav import WebDAVClient, WebDAVFile
from documents.multimodal import (
    LlamaIndexMultimodalParser,
    DoclingParser as MultimodalDoclingParser,
    VisionAPIParser,
    HybridMultimodalParser,
    MultimodalResult,
)
from documents.pipeline import DocumentPipeline, DocumentJob
from documents.api import app as documents_app
from documents.semantic_chunker import (
    SemanticTextChunker,
    LlamaIndexSentenceChunker,
    LlamaIndexJSONChunker,
    LlamaIndexHTMLChunker,
    MarkdownImageExtractor,
    HTMLImageExtractor,
    get_semantic_chunker,
    get_markdown_image_parser,
    get_html_image_parser,
    get_sentence_chunker,
    get_json_chunker,
    get_html_chunker,
)

from documents.diagram_formats import (
    DrawIOParser,
    DrawIOParseResult,
    PlantUMLParser,
    PlantUMLParseResult,
    BPMNParser,
    BPMNParseResult,
    BPMNElement,
    OpenAPIParser,
    OpenAPIParseResult,
    parse_drawio,
    parse_plantuml,
    parse_bpmn,
    parse_openapi,
    detect_format,
)

from documents.confluence import ConfluenceAttachment


__all__ = [
    "Document",
    "DocumentVersion",
    "DocumentSource",
    "LlamaIndexParser",
    "DoclingParser",
    "FallbackParser",
    "HybridDocumentParser",
    "ParsedDocumentResult",
    "ConfluenceClient",
    "ConfluencePage",
    "WebDAVClient",
    "WebDAVFile",
    "LlamaIndexMultimodalParser",
    "VisionAPIParser",
    "HybridMultimodalParser",
    "MultimodalResult",
    "DocumentPipeline",
    "DocumentJob",
    "documents_app",
    "LayoutType",
    "LayoutBlock",
    "LayoutAnalysisResult",
    "StructureAnalysisResult",
    "PDFLayoutAnalyzer",
    "DOCXStructureAnalyzer",
    "XLSXStructureAnalyzer",
    "PPTXStructureAnalyzer",
    "UnifiedLayoutParser",
    "get_layout_parser",
    "ColPaliClient",
    "ColPaliModel",
    "ColPaliEmbedding",
    "ColPaliResult",
    "get_colpali_client",
    "DiagramType",
    "DRAW_IO",
    "PLANTUML",
    "BPMN",
    "OPENAPI",
    "UMLClass",
    "UMLRelationship",
    "SequenceMessage",
    "C4Container",
    "DiagramExtractionResult",
    "DiagramTypeDetector",
    "UMLClassExtractor",
    "UMLSequenceExtractor",
    "C4ContainerExtractor",
    "UMLActivityExtractor",
    "UMLStateMachineExtractor",
    "UMLPackageExtractor",
    "UMLObjectExtractor",
    "UMLUseCaseExtractor",
    "ERDExtractor",
    "PlantUMLGenerator",
    "MermaidGenerator",
    "UnifiedDiagramParser",
    "get_diagram_parser",
    "SemanticTextChunker",
    "MarkdownImageExtractor",
    "HTMLImageExtractor",
    "get_semantic_chunker",
    "get_markdown_image_parser",
    "get_html_image_parser",
    "get_sentence_chunker",
    "get_json_chunker",
    "get_html_chunker",
    "ConfluenceAttachment",
    "DrawIOParser",
    "DrawIOParseResult",
    "PlantUMLParser",
    "PlantUMLParseResult",
    "BPMNParser",
    "BPMNParseResult",
    "BPMNElement",
    "OpenAPIParser",
    "OpenAPIParseResult",
    "parse_drawio",
    "parse_plantuml",
    "parse_openapi",
    "detect_format",
]
