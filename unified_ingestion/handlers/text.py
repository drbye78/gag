import hashlib
import logging
import csv
import io
import os
from typing import Any, Dict

from unified_ingestion.handlers.base import Handler, HandlerResult

logger = logging.getLogger(__name__)


class TextHandler(Handler):
    EXTENSION_PARSERS = {
        ".txt": "text",
        ".csv": "csv",
        ".tsv": "tsv",
        ".text": "text",
    }

    async def handle(self, content: bytes, source_id: str, metadata: Dict[str, Any]) -> HandlerResult:
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
        metadata: Dict[str, Any] = None,
    ) -> HandlerResult:
        chunks = []
        chunk_size = 1000
        overlap = 200
        meta: Dict[str, Any] = metadata if metadata is not None else {}

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