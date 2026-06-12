import hashlib
import logging
from typing import Any, Dict

from git.parser import CodeParser, ParsedFile
from unified_ingestion.handlers.base import Handler, HandlerResult

logger = logging.getLogger(__name__)


class SourceCodeHandler(Handler):
    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".jsx": "javascript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".cs": "csharp",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".scala": "scala",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
    }

    def __init__(self):
        self._parser = CodeParser()

    async def handle(
        self, content: bytes, source_id: str, metadata: Dict[str, Any]
    ) -> HandlerResult:
        try:
            filename = metadata.get("filename", "file")
            text = content.decode("utf-8")

            parsed = self._parser.parse(text, filename)

            chunks = []
            for entity in parsed.entities:
                chunk_id = hashlib.sha256(f"{source_id}:{entity.entity_id}".encode()).hexdigest()[
                    :16
                ]
                chunks.append(
                    {
                        "id": chunk_id,
                        "content": entity.content,
                        "chunk_index": len(chunks),
                        "start_char": 0,
                        "end_char": len(entity.content),
                        "metadata": {
                            "source_id": source_id,
                            "entity_type": entity.entity_type.value,
                            "entity_name": entity.name,
                            "language": entity.language,
                            "start_line": entity.start_line,
                            "end_line": entity.end_line,
                        },
                    }
                )

            if not chunks:
                chunk_id = hashlib.sha256(f"{source_id}:full".encode()).hexdigest()[:16]
                chunks.append(
                    {
                        "id": chunk_id,
                        "content": text,
                        "chunk_index": 0,
                        "start_char": 0,
                        "end_char": len(text),
                        "metadata": {
                            "source_id": source_id,
                            "entity_type": "file",
                            "language": parsed.language,
                        },
                    }
                )

            entities = [
                {
                    "id": e.entity_id,
                    "name": e.name,
                    "type": e.entity_type.value,
                    "language": e.language,
                    "file_path": e.file_path,
                    "start_line": e.start_line,
                    "end_line": e.end_line,
                }
                for e in parsed.entities
            ]

            relationships = self._build_relationships(parsed)

            return HandlerResult(
                success=True,
                chunks=chunks,
                entities=entities,
                relationships=relationships,
                metadata={
                    "language": parsed.language,
                    "entity_count": len(parsed.entities),
                    "import_count": len(parsed.imports),
                    "export_count": len(parsed.exports),
                },
            )

        except Exception as e:
            logger.error("SourceCodeHandler failed: %s", e)
            return HandlerResult(success=False, error=str(e))

    def _build_relationships(self, parsed: ParsedFile) -> list[Dict[str, Any]]:
        relationships = []

        for imp in parsed.imports:
            relationships.append(
                {
                    "source_id": parsed.file_path,
                    "target_id": imp,
                    "type": "IMPORTS",
                }
            )

        for exp in parsed.exports:
            relationships.append(
                {
                    "source_id": parsed.file_path,
                    "target_id": exp,
                    "type": "EXPORTS",
                }
            )

        return relationships
