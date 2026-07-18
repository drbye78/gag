"""
Documents Module - Document ingestion subsystem.

All imports are lazy to avoid forcing llama_index/docling dependencies
on modules that only need document models.
"""

from documents.models import Document, DocumentVersion, DocumentSource

__all__ = [
    "Document", "DocumentVersion", "DocumentSource",
    "LlamaIndexParser", "DoclingParser", "HybridDocumentParser", "ParsedDocumentResult",
    "LayoutType", "LayoutBlock", "LayoutAnalysisResult", "StructureAnalysisResult",
    "PDFLayoutAnalyzer", "DOCXStructureAnalyzer", "XLSXStructureAnalyzer",
    "PPTXStructureAnalyzer", "UnifiedLayoutParser", "get_layout_parser",
]

def __getattr__(name):
    """Lazy-load document parsing components on first access."""
    _parse_imports = {
        "LlamaIndexParser", "DoclingParser", "HybridDocumentParser", "ParsedDocumentResult",
    }
    _layout_imports = {
        "LayoutType", "LayoutBlock", "LayoutAnalysisResult", "StructureAnalysisResult",
        "PDFLayoutAnalyzer", "DOCXStructureAnalyzer", "XLSXStructureAnalyzer",
        "PPTXStructureAnalyzer", "UnifiedLayoutParser", "get_layout_parser",
    }
    if name in _parse_imports:
        from documents import parse
        return getattr(parse, name)
    if name in _layout_imports:
        from documents import layout
        return getattr(layout, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
