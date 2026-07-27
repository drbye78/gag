"""HTML artifact handler — strips tags, extracts text content for chunking."""

import hashlib
import logging
import re
from typing import Any

from unified_ingestion.handlers.base import Handler, HandlerResult

logger = logging.getLogger(__name__)


class HTMLHandler(Handler):
    """Handles HTML content by stripping tags and chunking plain text."""

    # Pattern to match script and style blocks for removal
    _SCRIPT_STYLE_RE = re.compile(
        r"<(script|style|noscript)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL
    )
    # Pattern to strip all remaining HTML tags
    _TAG_RE = re.compile(r"<[^>]+>")
    # Pattern to collapse whitespace
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
            text = self._strip_html(text)
            return self._chunk_text(text, source_id, filename)
        except Exception as e:
            logger.error("HTMLHandler failed for %s: %s", filename, e)
            return HandlerResult(success=False, error=str(e))

    def _strip_html(self, html: str) -> str:
        """Remove script/style blocks, strip tags, collapse whitespace."""
        text = self._SCRIPT_STYLE_RE.sub("", html)
        text = self._TAG_RE.sub(" ", text)
        text = self._WS_RE.sub(" ", text).strip()
        return text

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
                        "format": "html",
                    },
                }
            )

        return HandlerResult(
            success=True,
            chunks=chunks,
            metadata={"filename": filename, "format": "html"},
        )
