"""gRPC Proto artifact handler — parses .proto files for service/message definitions."""

import hashlib
import logging
import re
from typing import Any

from unified_ingestion.handlers.base import Handler, HandlerResult

logger = logging.getLogger(__name__)


class GRPCProtoHandler(Handler):
    """Handles .proto files by extracting service definitions and message types.

    Produces:
    - Chunks: each top-level block (service, message, enum) becomes a chunk.
    - Entities: service and message/enum definitions extracted as named entities.
    """

    # Match top-level blocks: service, message, enum, oneof, extend, reserved
    _BLOCK_RE = re.compile(
        r"^(service|message|enum|oneof|extend)\s+(\w+)\s*\{",
        re.MULTILINE,
    )
    # Match rpc method declarations inside services
    _RPC_RE = re.compile(
        r"^\s*rpc\s+(\w+)\s*\((\w+)\)\s*returns\s*\((\w+)\)",
        re.MULTILINE,
    )
    # Match field declarations: optional label support for proto2
    _FIELD_RE = re.compile(
        r"^\s*(?:optional|repeated|required)?\s*(\w+)\s+(\w+)\s*=\s*(\d+)",
        re.MULTILINE,
    )
    # Match import statements
    _IMPORT_RE = re.compile(r'^import\s+(?:public\s+)?"([^"]+)"', re.MULTILINE)
    # Match package declaration
    _PACKAGE_RE = re.compile(r"^package\s+([\w.]+)\s*;", re.MULTILINE)

    async def handle(
        self, content: bytes, source_id: str, metadata: dict[str, Any]
    ) -> HandlerResult:
        filename = metadata.get("filename", "file")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        try:
            return self._parse_proto(text, source_id, filename)
        except Exception as e:
            logger.error("GRPCProtoHandler failed for %s: %s", filename, e)
            return HandlerResult(success=False, error=str(e))

    def _parse_proto(
        self, text: str, source_id: str, filename: str
    ) -> HandlerResult:
        """Parse a .proto file into chunks and entities."""
        chunks: list[dict[str, Any]] = []
        entities: list[dict[str, Any]] = []

        # Extract package
        pkg_match = self._PACKAGE_RE.search(text)
        package = pkg_match.group(1) if pkg_match else ""

        # Extract imports
        imports = self._IMPORT_RE.findall(text)

        # Extract top-level blocks
        block_starts = list(self._BLOCK_RE.finditer(text))

        if not block_starts:
            # No structured blocks found — treat as plain text chunk
            return self._fallback_chunk(text, source_id, filename)

        for idx, match in enumerate(block_starts):
            block_type = match.group(1)
            block_name = match.group(2)
            start = match.start()

            # Find end of block (simple brace counting)
            end = self._find_block_end(text, match.end() - 1)
            block_text = text[start:end].strip()

            chunk_id = hashlib.sha256(
                f"{source_id}:{block_type}:{block_name}".encode()
            ).hexdigest()[:16]
            chunks.append(
                {
                    "id": chunk_id,
                    "content": block_text,
                    "chunk_index": idx,
                    "start_char": start,
                    "end_char": end,
                    "metadata": {
                        "source_id": source_id,
                        "filename": filename,
                        "format": "grpc_proto",
                        "block_type": block_type,
                        "block_name": block_name,
                        "package": package,
                    },
                }
            )

            # Create entity for services, messages, and enums
            if block_type in ("service", "message", "enum"):
                entity: dict[str, Any] = {
                    "id": chunk_id,
                    "name": block_name,
                    "type": block_type,
                    "package": package,
                    "source_file": filename,
                    "metadata": {},
                }

                # For services, extract rpc methods
                if block_type == "service":
                    rpcs = self._RPC_RE.findall(block_text)
                    entity["metadata"]["methods"] = [
                        {
                            "name": rpc[0],
                            "input_type": rpc[1],
                            "output_type": rpc[2],
                        }
                        for rpc in rpcs
                    ]

                # For messages, extract field info
                if block_type == "message":
                    fields = self._FIELD_RE.findall(block_text)
                    entity["metadata"]["fields"] = [
                        {"type": f[0], "name": f[1], "number": int(f[2])}
                        for f in fields
                    ]

                entities.append(entity)

        # Add file-level entity
        file_entity_id = hashlib.sha256(
            f"{source_id}:proto_file".encode()
        ).hexdigest()[:16]
        entities.append(
            {
                "id": file_entity_id,
                "name": filename,
                "type": "proto_file",
                "package": package,
                "source_file": filename,
                "metadata": {
                    "imports": imports,
                    "block_count": len(block_starts),
                },
            }
        )

        # Add import relationships
        relationships = []
        for imp in imports:
            rel_id = hashlib.sha256(
                f"{source_id}:import:{imp}".encode()
            ).hexdigest()[:16]
            relationships.append(
                {
                    "id": rel_id,
                    "source_id": file_entity_id,
                    "target_id": imp,
                    "type": "imports",
                    "metadata": {},
                }
            )

        return HandlerResult(
            success=True,
            chunks=chunks,
            entities=entities,
            relationships=relationships,
            metadata={
                "filename": filename,
                "format": "grpc_proto",
                "package": package,
                "import_count": len(imports),
                "block_count": len(block_starts),
            },
        )

    def _find_block_end(self, text: str, start: int) -> int:
        """Find the closing brace for a block starting at 'start' position."""
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return i + 1
        return len(text)

    def _fallback_chunk(
        self, text: str, source_id: str, filename: str
    ) -> HandlerResult:
        """Chunk raw text when no structured blocks are found."""
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
                        "format": "grpc_proto",
                    },
                }
            )

        return HandlerResult(
            success=True,
            chunks=chunks,
            metadata={"filename": filename, "format": "grpc_proto"},
        )
