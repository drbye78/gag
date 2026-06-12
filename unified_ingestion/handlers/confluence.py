"""
Confluence Attachment Handler.

Handles attachments from Confluence pages with MIME-type routing
to appropriate handlers (document, image, diagram, etc.)
"""

import logging
from typing import Any, Dict, List, Optional

from unified_ingestion.handlers.base import Chunk, Handler, HandlerResult
from unified_ingestion.handlers.registry import get_handler_registry

logger = logging.getLogger(__name__)


# MIME type to handler mapping
MIME_TYPE_ROUTING: Dict[str, str] = {
    # Images
    "image/png": "image",
    "image/jpeg": "image",
    "image/jpg": "image",
    "image/gif": "image",
    "image/svg+xml": "image",
    "image/webp": "image",
    # PDF
    "application/pdf": "document",
    # DOCX
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "document",
    "application/msword": "document",
    # PPTX
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "document",
    "application/vnd.ms-powerpoint": "document",
    # XLSX
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "document",
    "application/vnd.ms-excel": "document",
    # XML (draw.io)
    "application/xml": "diagram",
    "image/vnd.graphdraw": "diagram",
    # PlantUML
    "text/plain": "diagram",  # May be PlantUML if filename matches
    # JSON
    "application/json": "config",
    # YAML
    "application/x-yaml": "config",
    "text/yaml": "config",
    # Other
    "text/plain": "text",
    "text/html": "html",
}


def detect_handler_type(mime_type: str, filename: str) -> str:
    """Detect handler type from MIME type and filename."""
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    if ext in ("puml", "plantuml", "pu", "mermaid", "mmd", "uml", "dsl", "drawio", "dio"):
        return "diagram"
    if ext in ("bpmn",):
        return "bpmn"
    if ext in ("py", "js", "ts", "java", "kt", "go", "rs", "cs", "rb", "php"):
        return "source_code"
    if ext in ("json", "yaml", "yml", "xml", "toml", "gradle", "properties"):
        return "config"

    mime_lower = mime_type.lower() if mime_type else ""
    handler_type = MIME_TYPE_ROUTING.get(mime_lower)
    if handler_type:
        return handler_type

    for pattern, handler in MIME_TYPE_ROUTING.items():
        if pattern in mime_lower:
            return handler

    return "text"


class ConfluenceAttachmentHandler(Handler):
    """Handler for Confluence page attachments with MIME-type routing."""

    def __init__(self):
        self._registry = get_handler_registry()
        self._handler_cache: Dict[str, Handler] = {}

    def _get_handler(self, handler_type: str) -> Optional[Handler]:
        """Get handler by type with caching."""
        if handler_type in self._handler_cache:
            return self._handler_cache[handler_type]

        handler = self._registry.get(handler_type)
        if handler:
            self._handler_cache[handler_type] = handler
        return handler

    async def handle(
        self,
        content: bytes,
        path: str,
        metadata: Dict[str, Any],
    ) -> HandlerResult:
        """Handle attachment with MIME-type routing."""
        mime_type = metadata.get("mime_type", "")
        filename = metadata.get("title", path)

        # Detect handler type
        handler_type = detect_handler_type(mime_type, filename)

        # Get appropriate handler
        handler = self._get_handler(handler_type)
        if not handler:
            return HandlerResult(
                chunks=[],
                error=f"No handler for type: {handler_type} (MIME: {mime_type})",
            )

        # Route to handler
        try:
            result = await handler.handle(content, path, metadata)
            # Add handler type to metadata
            result.metadata["handler_type"] = handler_type
            result.metadata["source"] = "confluence_attachment"
            return result
        except Exception as e:
            logger.warning(f"Handler {handler_type} failed for {path}: {e}")
            return HandlerResult(
                chunks=[],
                error=str(e),
            )

    async def handle_batch(
        self,
        attachments: List[Dict[str, Any]],
    ) -> HandlerResult:
        """Handle multiple attachments."""
        all_chunks: List[Chunk] = []
        errors: List[str] = []

        for att in attachments:
            content = att.get("content")
            if not content:
                errors.append(f"No content for {att.get('title', 'unknown')}")
                continue

            result = await self.handle(
                content=content,
                path=att.get("title", ""),
                metadata={
                    "mime_type": att.get("mime_type", ""),
                    "title": att.get("title", ""),
                    "attachment_id": att.get("attachment_id", ""),
                },
            )

            all_chunks.extend(result.chunks)
            if result.error:
                errors.append(result.error)

        return HandlerResult(
            chunks=all_chunks,
            error="; ".join(errors) if errors else None,
        )
