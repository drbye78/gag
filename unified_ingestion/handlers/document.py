import hashlib
import logging
import os
from typing import Any, Dict

from documents.parse import LlamaIndexParser, DoclingParser, ParsedDocumentResult

from unified_ingestion.handlers.base import Handler, HandlerResult

logger = logging.getLogger(__name__)


class DocumentHandler(Handler):
    EXTENSION_MAP = {
        ".pdf": "docling",
        ".docx": "llamaindex",
        ".pptx": "llamaindex",
        ".xlsx": "llamaindex",
        ".doc": "docling",
        ".ppt": "docling",
    }

    def __init__(self):
        self._llama_parser = LlamaIndexParser()
        self._docling_parser = DoclingParser()

    async def handle(self, content: bytes, source_id: str, metadata: Dict[str, Any]) -> HandlerResult:
        filename = metadata.get("filename", "document")
        ext = os.path.splitext(filename)[1].lower()

        parser_type = self.EXTENSION_MAP.get(ext, "llamaindex")

        try:
            if parser_type == "docling" and ext == ".pdf":
                parsed = await self._docling_parser.parse(content)
            else:
                parsed = await self._llama_parser.parse(content, filename)

            if parsed.error:
                return HandlerResult(success=False, error=parsed.error)

            chunks = self._create_chunks(parsed, source_id, filename)
            return HandlerResult(success=True, chunks=chunks, metadata=parsed.metadata)

        except Exception as e:
            logger.error("DocumentHandler failed: %s", e)
            return HandlerResult(success=False, error=str(e))

    def _create_chunks(
        self, parsed: ParsedDocumentResult, source_id: str, filename: str
    ) -> list[Dict[str, Any]]:
        chunks = []
        if parsed.text:
            text = parsed.text
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
                            "total_tables": len(parsed.tables),
                            "total_images": len(parsed.images),
                        },
                    }
                )

        return chunks