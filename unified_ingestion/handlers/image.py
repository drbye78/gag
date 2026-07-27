"""Image artifact handler — records metadata only, no pixel-level processing."""

import hashlib
import logging
from typing import Any

from unified_ingestion.handlers.base import Handler, HandlerResult

logger = logging.getLogger(__name__)


class ImageHandler(Handler):
    """Handles image artifacts by recording metadata and chunking file info.

    This handler does NOT perform visual processing (no VLM calls).
    It records the image's existence and basic metadata as a single chunk
    for downstream retrieval. Actual image understanding is handled
    separately by the multimodal pipeline.
    """

    async def handle(
        self, content: bytes, source_id: str, metadata: dict[str, Any]
    ) -> HandlerResult:
        filename = metadata.get("filename", "file")
        try:
            file_size = len(content)
            content_hash = hashlib.sha256(content).hexdigest()[:16]
            chunk_id = hashlib.sha256(f"{source_id}:image".encode()).hexdigest()[:16]

            chunk_content = (
                f"[Image: {filename}] "
                f"Size: {file_size} bytes. "
                f"Content hash: {content_hash}. "
                f"No text content extracted — use multimodal pipeline for visual analysis."
            )

            chunk = {
                "id": chunk_id,
                "content": chunk_content,
                "chunk_index": 0,
                "start_char": 0,
                "end_char": len(chunk_content),
                "metadata": {
                    "source_id": source_id,
                    "filename": filename,
                    "format": "image",
                    "file_size": file_size,
                    "content_hash": content_hash,
                    "has_text_content": False,
                },
            }

            return HandlerResult(
                success=True,
                chunks=[chunk],
                metadata={
                    "filename": filename,
                    "format": "image",
                    "file_size": file_size,
                },
            )
        except Exception as e:
            logger.error("ImageHandler failed for %s: %s", filename, e)
            return HandlerResult(success=False, error=str(e))
