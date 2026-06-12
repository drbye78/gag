import hashlib
import logging
from typing import Any, Dict

from documents.diagram_formats import BPMNParser
from unified_ingestion.handlers.base import Handler, HandlerResult

logger = logging.getLogger(__name__)


class BPMNHandler(Handler):
    async def handle(
        self, content: bytes, source_id: str, metadata: Dict[str, Any]
    ) -> HandlerResult:
        filename = metadata.get("filename", "diagram.bpmn")
        text = content.decode("utf-8")

        if filename.endswith(".xml") or "<bpmn" in text.lower():
            return await self._handle_bpmn_xml(content, source_id, filename)
        else:
            return await self._handle_bpmn_text(text, source_id, filename)

    async def _handle_bpmn_xml(
        self, content: bytes, source_id: str, filename: str
    ) -> HandlerResult:
        try:
            parser = BPMNParser()
            result = parser.parse(content.decode("utf-8"))

            chunks = []
            for process in result.processes:
                chunk_id = hashlib.sha256(f"{source_id}:{process.get('id')}".encode()).hexdigest()[
                    :16
                ]
                chunks.append(
                    {
                        "id": chunk_id,
                        "content": str(process),
                        "chunk_index": len(chunks),
                        "start_char": 0,
                        "end_char": 0,
                        "metadata": {
                            "source_id": source_id,
                            "filename": filename,
                            "type": "process",
                        },
                    }
                )

            entities = []
            for task in result.tasks:
                entities.append(
                    {
                        "id": task.get("id"),
                        "name": task.get("name"),
                        "type": "task",
                    }
                )

            for event in result.events:
                entities.append(
                    {
                        "id": event.get("id"),
                        "name": event.get("name"),
                        "type": event.get("event_type"),
                    }
                )

            for gateway in result.gateways:
                entities.append(
                    {
                        "id": gateway.get("id"),
                        "name": gateway.get("name"),
                        "type": gateway.get("gateway_type"),
                    }
                )

            relationships = []
            for flow in result.flows:
                relationships.append(
                    {
                        "source": flow.get("source_ref"),
                        "target": flow.get("target_ref"),
                        "type": "flow",
                    }
                )

            return HandlerResult(
                success=True,
                chunks=chunks,
                entities=entities,
                relationships=relationships,
                metadata={
                    "process_count": len(result.processes),
                    "task_count": len(result.tasks),
                    "event_count": len(result.events),
                },
            )

        except Exception as e:
            logger.error("BPMNHandler XML failed: %s", e)
            return HandlerResult(success=False, error=str(e))

    async def _handle_bpmn_text(self, text: str, source_id: str, filename: str) -> HandlerResult:
        chunks = []
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
                    "format": "text",
                },
            }
        )

        return HandlerResult(success=True, chunks=chunks, metadata={"format": "text"})
