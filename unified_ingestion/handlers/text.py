import csv
import hashlib
import io
import logging
import os
import re
from typing import Any

from unified_ingestion.handlers.base import Handler, HandlerResult

logger = logging.getLogger(__name__)


class TextHandler(Handler):
    EXTENSION_PARSERS = {
        ".txt": "text",
        ".csv": "csv",
        ".tsv": "tsv",
        ".text": "text",
    }

    async def handle(self, content: bytes, source_id: str, metadata: dict[str, Any]) -> HandlerResult:
        filename = metadata.get("filename", "file")
        ext = os.path.splitext(filename)[1].lower()

        parser_type = self.EXTENSION_PARSERS.get(ext, "text")

        try:
            if parser_type == "csv":
                return await self._parse_csv(content, source_id, filename)
            elif parser_type == "tsv":
                return await self._parse_tsv(content, source_id, filename)
            else:
                return await self._parse_text(content, source_id, filename)

        except Exception as e:
            logger.error("TextHandler failed: %s", e)
            return HandlerResult(success=False, error=str(e))

    async def _parse_text(
        self, content: bytes, source_id: str, filename: str
    ) -> HandlerResult:
        text = content.decode("utf-8")
        return self._chunk_text(text, source_id, filename)

    async def _parse_csv(
        self, content: bytes, source_id: str, filename: str
    ) -> HandlerResult:
        text = content.decode("utf-8")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)

        if not rows:
            return HandlerResult(success=True, chunks=[], metadata={"row_count": 0})

        header = rows[0] if rows else []
        data_rows = rows[1:] if len(rows) > 1 else []

        csv_text = text
        return self._chunk_text(csv_text, source_id, filename, metadata={"row_count": len(data_rows)})

    async def _parse_tsv(
        self, content: bytes, source_id: str, filename: str
    ) -> HandlerResult:
        text = content.decode("utf-8")
        reader = csv.reader(io.StringIO(text), delimiter="\t")
        rows = list(reader)

        if not rows:
            return HandlerResult(success=True, chunks=[], metadata={"row_count": 0})

        data_rows = rows[1:] if len(rows) > 1 else []

        tsv_text = content.decode("utf-8")
        return self._chunk_text(tsv_text, source_id, filename, metadata={"row_count": len(data_rows)})

    def _chunk_text(
        self,
        text: str,
        source_id: str,
        filename: str,
        metadata: dict[str, Any] = None,
    ) -> HandlerResult:
        chunks = []
        chunk_size = 1000
        overlap = 200
        meta: dict[str, Any] = metadata if metadata is not None else {}

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
                        **meta,
                    },
                }
            )

        return HandlerResult(success=True, chunks=chunks, metadata=meta)


class PlainTextHandler(Handler):
    """Handler for PLAINTEXT artifacts — plain UTF-8 text files."""

    async def handle(self, content: bytes, source_id: str, metadata: dict[str, Any]) -> HandlerResult:
        filename = metadata.get("filename", "file")
        try:
            text = content.decode("utf-8")
            return self._chunk_text(text, source_id, filename)
        except Exception as e:
            logger.error("PlainTextHandler failed for %s: %s", filename, e)
            return HandlerResult(success=False, error=str(e))

    def _chunk_text(self, text: str, source_id: str, filename: str) -> HandlerResult:
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
                        "format": "plaintext",
                    },
                }
            )

        return HandlerResult(
            success=True,
            chunks=chunks,
            metadata={"filename": filename, "format": "plaintext"},
        )


class RSTHandler(Handler):
    """Handler for reStructuredText artifacts — strips RST directives and roles."""

    _DIRECTIVE_RE = re.compile(r"\.\.\s+\w+::.*?(?=\n\S|\Z)", re.DOTALL)
    _ROLE_RE = re.compile(r":\w+:`[^`]*`")
    _SUBSTITUTION_RE = re.compile(r"\|[^|]+\|")
    _WS_RE = re.compile(r"\s+")

    async def handle(self, content: bytes, source_id: str, metadata: dict[str, Any]) -> HandlerResult:
        filename = metadata.get("filename", "file")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        try:
            cleaned = self._strip_rst(text)
            return self._chunk_text(cleaned, source_id, filename)
        except Exception as e:
            logger.error("RSTHandler failed for %s: %s", filename, e)
            return HandlerResult(success=False, error=str(e))

    def _strip_rst(self, text: str) -> str:
        text = self._DIRECTIVE_RE.sub("", text)
        text = self._ROLE_RE.sub(lambda m: m.group(0)[m.group(0).index("`") + 1 : -1], text)
        text = self._SUBSTITUTION_RE.sub("", text)
        text = self._WS_RE.sub(" ", text).strip()
        return text

    def _chunk_text(self, text: str, source_id: str, filename: str) -> HandlerResult:
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
                        "format": "rst",
                    },
                }
            )

        return HandlerResult(
            success=True,
            chunks=chunks,
            metadata={"filename": filename, "format": "rst"},
        )


class AsciiDocHandler(Handler):
    """Handler for AsciiDoc artifacts — strips admonitions and formatting markers."""

    _BLOCK_RE = re.compile(r"={2,4}\s+.*", re.MULTILINE)
    _ATTR_RE = re.compile(r"^:\w+:.*$", re.MULTILINE)
    _WS_RE = re.compile(r"\s+")

    async def handle(self, content: bytes, source_id: str, metadata: dict[str, Any]) -> HandlerResult:
        filename = metadata.get("filename", "file")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        try:
            cleaned = self._strip_asciidoc(text)
            return self._chunk_text(cleaned, source_id, filename)
        except Exception as e:
            logger.error("AsciiDocHandler failed for %s: %s", filename, e)
            return HandlerResult(success=False, error=str(e))

    def _strip_asciidoc(self, text: str) -> str:
        text = self._ATTR_RE.sub("", text)
        text = self._WS_RE.sub(" ", text).strip()
        return text

    def _chunk_text(self, text: str, source_id: str, filename: str) -> HandlerResult:
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
                        "format": "asciidoc",
                    },
                }
            )

        return HandlerResult(
            success=True,
            chunks=chunks,
            metadata={"filename": filename, "format": "asciidoc"},
        )


class PropertiesHandler(Handler):
    """Handler for .properties files — key=value format, treats as plain text chunking."""

    async def handle(self, content: bytes, source_id: str, metadata: dict[str, Any]) -> HandlerResult:
        filename = metadata.get("filename", "file")
        try:
            text = content.decode("utf-8")
            return self._chunk_text(text, source_id, filename)
        except Exception as e:
            logger.error("PropertiesHandler failed for %s: %s", filename, e)
            return HandlerResult(success=False, error=str(e))

    def _chunk_text(self, text: str, source_id: str, filename: str) -> HandlerResult:
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
                        "format": "properties",
                    },
                }
            )

        return HandlerResult(
            success=True,
            chunks=chunks,
            metadata={"filename": filename, "format": "properties"},
        )


class INIHandler(Handler):
    """Handler for .ini files — section-based key=value format."""

    _SECTION_RE = re.compile(r"^\[([^\]]+)\]", re.MULTILINE)

    async def handle(self, content: bytes, source_id: str, metadata: dict[str, Any]) -> HandlerResult:
        filename = metadata.get("filename", "file")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        try:
            return self._chunk_text(text, source_id, filename)
        except Exception as e:
            logger.error("INIHandler failed for %s: %s", filename, e)
            return HandlerResult(success=False, error=str(e))

    def _chunk_text(self, text: str, source_id: str, filename: str) -> HandlerResult:
        chunks: list[dict[str, Any]] = []
        chunk_size = 1000
        overlap = 200

        # Extract section names for metadata
        sections = self._SECTION_RE.findall(text)

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
                        "format": "ini",
                    },
                }
            )

        return HandlerResult(
            success=True,
            chunks=chunks,
            metadata={"filename": filename, "format": "ini", "sections": sections},
        )
