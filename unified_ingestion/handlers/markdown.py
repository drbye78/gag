import hashlib
import logging
import re
from typing import Any, Dict, List

from ingestion.structural_chunker import StructuralChunker

from unified_ingestion.handlers.base import Handler, HandlerResult

logger = logging.getLogger(__name__)

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)


class MarkdownHandler(Handler):
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self._chunker = StructuralChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    async def handle(self, content: bytes, source_id: str, metadata: Dict[str, Any]) -> HandlerResult:
        try:
            text = content.decode("utf-8")
            frontmatter = self._parse_frontmatter(text)
            body = FRONTMATTER_RE.sub("", text, count=1).strip()

            code_blocks = self._extract_code_blocks(body)

            chunks = []
            current_idx = 0

            for lang, code in code_blocks:
                chunk_id = hashlib.sha256(f"{source_id}:code:{current_idx}".encode()).hexdigest()[:16]
                chunks.append(
                    {
                        "id": chunk_id,
                        "content": code,
                        "chunk_index": current_idx,
                        "start_char": 0,
                        "end_char": len(code),
                        "metadata": {
                            "source_id": source_id,
                            "type": "code_block",
                            "language": lang,
                        },
                    }
                )
                current_idx += 1

            text_chunks = self._chunk_text(body, source_id, start_idx=current_idx)
            chunks.extend(text_chunks)

            return HandlerResult(
                success=True,
                chunks=chunks,
                metadata={"frontmatter": frontmatter, "code_block_count": len(code_blocks)},
            )

        except Exception as e:
            logger.error("MarkdownHandler failed: %s", e)
            return HandlerResult(success=False, error=str(e))

    def _parse_frontmatter(self, text: str) -> Dict[str, Any]:
        match = FRONTMATTER_RE.match(text)
        if not match:
            return {}

        fm_text = match.group(1)
        frontmatter = {}
        for line in fm_text.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                frontmatter[key.strip()] = value.strip()

        return frontmatter

    def _extract_code_blocks(self, text: str) -> List[tuple[str, str]]:
        blocks = []
        for match in CODE_BLOCK_RE.finditer(text):
            lang = match.group(1) or "text"
            code = match.group(2).strip()
            blocks.append((lang, code))
        return blocks

    def _chunk_text(
        self, text: str, source_id: str, start_idx: int = 0
    ) -> List[Dict[str, Any]]:
        from ingestion.chunker import ChunkResult

        result = self._chunker.chunk(text, source_id)
        chunks = []

        for chunk in result.chunks:
            chunk_id = hashlib.sha256(f"{source_id}:{chunk.chunk_index}".encode()).hexdigest()[:16]
            chunks.append(
                {
                    "id": chunk_id,
                    "content": chunk.content,
                    "chunk_index": start_idx + chunk.chunk_index,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "metadata": {
                        "source_id": source_id,
                        "type": "text",
                    },
                }
            )

        return chunks