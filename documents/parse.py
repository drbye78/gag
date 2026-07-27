"""
Document Parser - Multi-format document parsing with LlamaIndex + Docling.

Uses:
- LlamaIndex readers for document parsing
- Docling for advanced PDF/OCR
"""

import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# LlamaIndex - mandatory dependency
from llama_index.core import SimpleDirectoryReader
from llama_index.core.readers import StringIterableReader

# Docling v2.x - optional dependency (graceful degradation if not installed)
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.document import ConversionResult
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    DocumentConverter = None  # type: ignore[assignment,misc]
    InputFormat = None  # type: ignore[assignment,misc]
    ConversionResult = None  # type: ignore[assignment,misc]
    logger.warning("Docling not installed — advanced PDF/OCR parsing disabled")


@dataclass
class ParsedDocumentResult:
    """Unified parsing result."""

    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tables: List[List[str]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    used_llama_index: bool = False
    used_docling: bool = False
    error: Optional[str] = None
    links: List[str] = field(default_factory=list)
    layout_analysis: Optional[Dict[str, Any]] = field(default_factory=dict)
    structure_analysis: Optional[Dict[str, Any]] = field(default_factory=dict)


class LlamaIndexParser:
    """LlamaIndex-based document parser."""

    def __init__(self):
        self._readers: Dict[str, Any] = {}

    def _get_reader(self, ext: str):
        if ext in self._readers:
            return self._readers[ext]

        reader_map = {
            ".txt": SimpleDirectoryReader,
            ".text": SimpleDirectoryReader,
            ".md": SimpleDirectoryReader,
            ".markdown": SimpleDirectoryReader,
            ".pdf": SimpleDirectoryReader,
            ".docx": SimpleDirectoryReader,
            ".pptx": SimpleDirectoryReader,
            ".csv": SimpleDirectoryReader,
            ".html": SimpleDirectoryReader,
            ".htm": SimpleDirectoryReader,
        }

        reader_cls = reader_map.get(ext)
        if reader_cls:
            try:
                self._readers[ext] = reader_cls()
            except Exception as e:
                logger.error("Failed to initialize LlamaIndex reader for %s: %s", ext, e)

        return self._readers.get(ext)

    async def parse(
        self,
        content: bytes,
        filename: str,
    ) -> ParsedDocumentResult:
        # SECURITY: Sanitize filename to prevent path traversal
        from core.security import sanitize_filename
        safe_filename = sanitize_filename(filename)

        ext = os.path.splitext(safe_filename)[1].lower()
        reader = self._get_reader(ext)

        if not reader:
            return ParsedDocumentResult(text="", error=f"No reader for {ext}")

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            try:
                docs = reader.load_data(tmp_path)
                text = "\n\n".join(doc.text for doc in docs)
                return ParsedDocumentResult(
                    text=text,
                    metadata={"doc_count": len(docs)},
                    used_llama_index=True,
                )
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            return ParsedDocumentResult(text="", error=str(e))


class DoclingParser:
    """Docling v2.x based parser."""

    _converter: Any = None

    def __init__(self, use_ocr: bool = False):
        self._use_ocr = use_ocr

    def _get_converter(self) -> Any:
        if not DOCLING_AVAILABLE:
            raise RuntimeError("Docling is not installed — cannot use DoclingParser")
        if self._converter is None:
            self._converter = DocumentConverter()
        return self._converter  # type: ignore[return-value]

    async def parse(
        self,
        content: bytes,
    ) -> ParsedDocumentResult:
        if not DOCLING_AVAILABLE:
            return ParsedDocumentResult(
                text="",
                error="Docling is not installed — advanced PDF/OCR parsing unavailable",
            )

        converter = self._get_converter()

        try:
            from io import BytesIO
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            try:
                result = converter.convert(tmp_path)
                if result.status.name == "SUCCESS":
                    text = result.document.export_to_markdown()
                    return ParsedDocumentResult(
                        text=text,
                        metadata={
                            "page_count": len(result.pages),
                            "status": result.status.name,
                        },
                        used_docling=True,
                    )
                else:
                    return ParsedDocumentResult(
                        text="",
                        error=f"Docling conversion failed: {result.status.name}",
                    )
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            logger.warning("Docling parse failed: %s", e)
            return ParsedDocumentResult(text="", error=str(e))

    async def parse_with_elements(
        self,
        content: bytes,
    ) -> tuple[str, list[dict], dict]:
        """Parse PDF and return (text, elements, metadata).

        Returns raw tuples for callers to wrap in their own result types.
        """
        converter = self._get_converter()
        if not converter:
            return "", [], {}

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            try:
                result = converter.convert(tmp_path)
                text = result.document.export_to_markdown()

                elements = []
                if hasattr(result.document, 'iter_inferred_terms'):
                    for item in result.document.iter_inferred_terms():
                        elements.append({
                            "element_id": getattr(item, 'id', "") or "",
                            "type": getattr(item, 'label', "") or "unknown",
                            "label": getattr(item, 'text', "") or "",
                            "confidence": getattr(item, 'score', 0.0),
                        })

                metadata = {"page_count": len(result.pages)}
                return text, elements, metadata
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            return "", [], {"error": str(e)}


class HybridDocumentParser:
    """Hybrid parser: Docling → LlamaIndex (both mandatory)."""

    def __init__(self):
        self.llama = LlamaIndexParser()
        self.docling = DoclingParser()

    async def parse(
        self,
        content: bytes,
        filename: str,
    ) -> ParsedDocumentResult:
        # SECURITY: Sanitize filename to prevent path traversal
        from core.security import sanitize_filename
        safe_filename = sanitize_filename(filename)

        ext = os.path.splitext(safe_filename)[1].lower()

        # Try Docling first for PDF
        if ext == ".pdf":
            result = await self.docling.parse(content)
            if result.text and not result.error:
                return result

        # Try LlamaIndex for other formats
        result = await self.llama.parse(content, safe_filename)
        if result.text and not result.error:
            return result

        # Both failed - raise error
        return ParsedDocumentResult(
            text="",
            error=f"Failed to parse {filename}: Docling={ext == '.pdf' and 'n/a' or 'failed'}, LlamaIndex=failed",
        )

    async def parse_file(
        self,
        file_path: str,
        use_ocr: bool = True,
    ) -> ParsedDocumentResult:
        """Parse a file from disk."""
        if not os.path.exists(file_path):
            return ParsedDocumentResult(text="", error=f"File not found: {file_path}")

        try:
            with open(file_path, "rb") as f:
                content = f.read()
        except Exception as e:
            return ParsedDocumentResult(text="", error=f"Failed to read file: {e}")

        return await self.parse(content, os.path.basename(file_path))

    async def parse_url(
        self,
        url: str,
        use_ocr: bool = True,
    ) -> ParsedDocumentResult:
        """Parse a document from URL."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                content = response.content
                # SECURITY: Sanitize filename derived from URL
                from core.security import sanitize_filename
                filename = sanitize_filename(url.split("/")[-1] or "document")
        except Exception as e:
            return ParsedDocumentResult(text="", error=f"Failed to fetch URL: {e}")

        return await self.parse(content, filename)


# Global instance
_parser: Optional[HybridDocumentParser] = None


def get_document_parser() -> HybridDocumentParser:
    global _parser
    if _parser is None:
        _parser = HybridDocumentParser()
    return _parser


def is_llama_index_available() -> bool:
    return True


def is_docling_available() -> bool:
    return DOCLING_AVAILABLE
