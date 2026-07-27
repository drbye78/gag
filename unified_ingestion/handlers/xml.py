"""XML artifact handler — parses XML and extracts text content for chunking."""

import hashlib
import logging
import re
from typing import Any
from xml.etree import ElementTree

from unified_ingestion.handlers.base import Handler, HandlerResult

logger = logging.getLogger(__name__)


class XMLHandler(Handler):
    """Handles XML content by parsing and extracting text nodes for chunking."""

    _WS_RE = re.compile(r"\s+")

    async def handle(
        self, content: bytes, source_id: str, metadata: dict[str, Any]
    ) -> HandlerResult:
        filename = metadata.get("filename", "file")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        try:
            extracted = self._extract_text(text)
            return self._chunk_text(extracted, source_id, filename)
        except Exception as e:
            logger.error("XMLHandler failed for %s: %s", filename, e)
            return HandlerResult(success=False, error=str(e))

    def _extract_text(self, xml_str: str) -> str:
        """Parse XML and extract all text nodes, preserving structure."""
        try:
            root = ElementTree.fromstring(xml_str)
        except ElementTree.ParseError:
            # Fallback: strip tags like HTML
            return self._WS_RE.sub(" ", re.sub(r"<[^>]+>", " ", xml_str)).strip()

        texts: list[str] = []
        self._walk_tree(root, texts)
        return " ".join(texts)

    def _walk_tree(self, elem: ElementTree.Element, texts: list[str]) -> None:
        """Recursively collect text from an XML element tree."""
        if elem.text and elem.text.strip():
            texts.append(elem.text.strip())
        for child in elem:
            self._walk_tree(child, texts)
            if child.tail and child.tail.strip():
                texts.append(child.tail.strip())

    def _chunk_text(
        self, text: str, source_id: str, filename: str
    ) -> HandlerResult:
        chunks: list[dict[str, Any]] = []
        chunk_size = 1000
        overlap = 200

        for i in range(0, len(text), chunk_size - overlap):
            chunk_text = text[i : i + chunk_size]
            if not chunk_text.strip():
                continue
            chunk_id = hashlib.sha256(f"{source_id}:{i}".encode()).hexdigest()[:16]
            chunks.append(
                {
                    "id": chunk_id,
                    "content": chunk_text,
                    "chunk_index": len(chunks),
                    "start_char": i,
                    "end_char": i + len(chunk_text),
                    "metadata": {
                        "source_id": source_id,
                        "filename": filename,
                        "format": "xml",
                    },
                }
            )

        return HandlerResult(
            success=True,
            chunks=chunks,
            metadata={"filename": filename, "format": "xml"},
        )
