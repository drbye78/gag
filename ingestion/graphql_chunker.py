import re
import hashlib
from typing import Any, Dict, List
from dataclasses import dataclass

from ingestion.chunker import Chunk, ChunkResult, TextChunker


@dataclass
class GraphQLDefinition:
    kind: str
    name: str
    content: str
    fields: List[str]


class GraphQLChunker(TextChunker):
    def __init__(self):
        pass

    def chunk(self, text: str, source_id: str) -> ChunkResult:
        import time
        start = time.time()

        definitions = self._parse_graphql(text)
        chunks = []

        for idx, defn in enumerate(definitions):
            chunk_id = self._make_chunk_id(source_id, idx)
            chunks.append(Chunk(
                id=chunk_id,
                content=defn.content,
                chunk_index=idx,
                start_char=0,
                end_char=0,
                metadata={"kind": defn.kind, "name": defn.name, "fields": defn.fields},
            ))

        taken = int((time.time() - start) * 1000)
        return ChunkResult(
            source_id=source_id,
            source_type="graphql",
            chunks=chunks,
            total_chars=len(text),
            took_ms=taken,
        )

    def _parse_graphql(self, content: str) -> List[GraphQLDefinition]:
        definitions = []

        type_pattern = r"(?:type|interface|input|enum)\s+(\w+)\s*\{([^}]+)\}"
        for match in re.finditer(type_pattern, content, re.MULTILINE):
            name = match.group(1)
            fields = self._extract_fields(match.group(2))
            definitions.append(GraphQLDefinition(
                kind="type",
                name=name,
                content=match.group(0),
                fields=fields,
            ))

        op_pattern = r"(?:query|mutation|subscription)\s*(?:\w+)?\s*(?:\([^)]*\))?\s*\{([^}]+)\}"
        for match in re.finditer(op_pattern, content):
            definitions.append(GraphQLDefinition(
                kind="operation",
                name="anonymous",
                content=match.group(0),
                fields=[],
            ))

        schema_pattern = r"schema\s*\{([^}]+)\}"
        for match in re.finditer(schema_pattern, content):
            definitions.append(GraphQLDefinition(
                kind="schema",
                name="schema",
                content=match.group(0),
                fields=[],
            ))

        return definitions

    def _extract_fields(self, body: str) -> List[str]:
        fields = []
        for line in body.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                match = re.match(r"(\w+)", line)
                if match:
                    fields.append(match.group(1))
        return fields

    def _make_chunk_id(self, source_id: str, chunk_idx: int) -> str:
        raw = f"{source_id}:{chunk_idx}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_graphql_chunker() -> GraphQLChunker:
    return GraphQLChunker()