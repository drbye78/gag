import hashlib
import logging
from typing import Any, Dict, List

from ingestion.graphql_chunker import GraphQLChunker

from unified_ingestion.handlers.base import Handler, HandlerResult

logger = logging.getLogger(__name__)


class GraphQLHandler(Handler):
    def __init__(self):
        self._chunker = GraphQLChunker()

    async def handle(self, content: bytes, source_id: str, metadata: Dict[str, Any]) -> HandlerResult:
        filename = metadata.get("filename", "schema.graphql")
        text = content.decode("utf-8")

        try:
            result = self._chunker.chunk(text, source_id)

            chunks = []
            entities = []
            relationships = []

            for chunk in result.chunks:
                chunk_id = hashlib.sha256(f"{source_id}:{chunk.chunk_index}".encode()).hexdigest()[:16]
                chunks.append(
                    {
                        "id": chunk_id,
                        "content": chunk.content,
                        "chunk_index": chunk.chunk_index,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                        "metadata": {
                            "source_id": source_id,
                            "filename": filename,
                            "type": chunk.metadata.get("type"),
                        },
                    }
                )

                if chunk.metadata.get("type") == "type":
                    entities.append(
                        {
                            "name": chunk.metadata.get("name"),
                            "type": "type",
                            "fields": chunk.metadata.get("fields", []),
                        }
                    )
                elif chunk.metadata.get("type") == "query" or chunk.metadata.get("type") == "mutation":
                    relationships.append(
                        {
                            "source": chunk.metadata.get("name"),
                            "target": chunk.metadata.get("return_type"),
                            "type": chunk.metadata.get("type"),
                        }
                    )

            if not chunks:
                chunk_id = hashlib.sha256(f"{source_id}".encode()).hexdigest()[:16]
                chunks.append(
                    {
                        "id": chunk_id,
                        "content": text,
                        "chunk_index": 0,
                        "start_char": 0,
                        "end_char": len(text),
                        "metadata": {
                            "source_id": source_id,
                            "filename": filename,
                        },
                    }
                )

            return HandlerResult(
                success=True,
                chunks=chunks,
                entities=entities,
                relationships=relationships,
                metadata={},
            )

        except Exception as e:
            logger.error("GraphQLHandler failed: %s", e)
            return HandlerResult(success=False, error=str(e))