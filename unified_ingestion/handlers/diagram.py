import hashlib
import logging
import re
from typing import Any, Dict, List

from documents.diagram_parser import DiagramTypeDetector, DiagramExtractionResult
from documents.diagram_formats import DrawIOParser, PlantUMLParser, MermaidParser

from unified_ingestion.handlers.base import Handler, HandlerResult

logger = logging.getLogger(__name__)


class DiagramHandler(Handler):
    DIAGRAM_PATTERNS = {
        "plantuml": r"^@startuml",
        "mermaid": r"^flowchart|^graph|^sequenceDiagram|^classDiagram|^stateDiagram",
        "uml": r"^class\s+\w+|^interface\s+\w+|^package\s+\w+",
        "c4": r"^System_Context|^Container|^Component\s+\w+",
    }

    def __init__(self):
        self._detector = DiagramTypeDetector()
        self._drawio_parser = DrawIOParser()
        self._plantuml_parser = PlantUMLParser()
        self._mermaid_parser = MermaidParser()

    async def handle(self, content: bytes, source_id: str, metadata: Dict[str, Any]) -> HandlerResult:
        filename = metadata.get("filename", "diagram")
        text = content.decode("utf-8")

        diagram_type = self._detect_diagram_type(text, filename)

        try:
            if diagram_type == "plantuml":
                return await self._handle_plantuml(text, source_id, filename)
            elif diagram_type == "mermaid":
                return await self._handle_mermaid(text, source_id, filename)
            elif diagram_type.startswith("uml_") or diagram_type.startswith("c4_"):
                return await self._handle_uml(text, source_id, filename, diagram_type)
            else:
                return await self._handle_generic(text, source_id, filename)

        except Exception as e:
            logger.error("DiagramHandler failed: %s", e)
            return HandlerResult(success=False, error=str(e))

    async def _handle_plantuml(
        self, text: str, source_id: str, filename: str
    ) -> HandlerResult:
        result = self._plantuml_parser.parse(text)

        chunks = []
        entities = []
        relationships = []

        for rel in result.relationships:
            relationships.append(
                {
                    "source": rel.get("from"),
                    "target": rel.get("to"),
                    "type": rel.get("type"),
                }
            )

        for participant in result.participants:
            entities.append(
                {
                    "name": participant,
                    "type": "participant",
                }
            )

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
                    "diagram_type": "plantuml",
                    "participant_count": len(result.participants),
                },
            }
        )

        return HandlerResult(
            success=True,
            chunks=chunks,
            entities=entities,
            relationships=relationships,
            metadata={"diagram_type": "plantuml"},
        )

    async def _handle_mermaid(
        self, text: str, source_id: str, filename: str
    ) -> HandlerResult:
        result = self._mermaid_parser.parse(text)

        chunks = []
        entities = []
        relationships = []

        for entity in result.entities:
            entities.append(
                {
                    "id": entity.get("id"),
                    "label": entity.get("label"),
                    "type": entity.get("type", "entity"),
                }
            )

        for rel in result.relationships:
            relationships.append(
                {
                    "source": rel.get("from"),
                    "target": rel.get("to"),
                    "type": rel.get("label", "relates"),
                }
            )

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
                    "diagram_type": "mermaid",
                },
            }
        )

        return HandlerResult(
            success=True,
            chunks=chunks,
            entities=entities,
            relationships=relationships,
            metadata={"diagram_type": "mermaid"},
        )

    async def _handle_uml(
        self, text: str, source_id: str, filename: str, diagram_type: str
    ) -> HandlerResult:
        result = self._parser.extract_from_text(text, diagram_type)

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
                    "diagram_type": diagram_type,
                },
            }
        )

        return HandlerResult(
            success=True,
            chunks=chunks,
            entities=result.entities,
            relationships=result.relationships,
            metadata={"diagram_type": diagram_type, "confidence": result.confidence},
        )

    async def _handle_generic(
        self, text: str, source_id: str, filename: str
    ) -> HandlerResult:
        result = self._parser.extract_from_text(text, "unknown")

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
                    "diagram_type": result.diagram_type.value,
                },
            }
        )

        return HandlerResult(
            success=True,
            chunks=chunks,
            entities=result.entities,
            relationships=result.relationships,
            metadata={"diagram_type": result.diagram_type.value},
        )

    def _detect_diagram_type(self, text: str, filename: str) -> str:
        for diag_type, pattern in self.DIAGRAM_PATTERNS.items():
            if re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
                return diag_type

        return self._detector.detect(text)