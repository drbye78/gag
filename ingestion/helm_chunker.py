import re
import hashlib
import yaml
from typing import Any, Dict, List
from dataclasses import dataclass

from ingestion.chunker import Chunk, ChunkResult, TextChunker


@dataclass
class HelmResource:
    kind: str
    name: str
    content: str


class HelmChartChunker(TextChunker):
    def __init__(self, chunk_size: int = 2000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str, source_id: str) -> ChunkResult:
        import time
        start = time.time()

        chunks = []

        chart_meta = self._parse_chart_yaml(text)
        if chart_meta:
            chunk_id = self._make_chunk_id(source_id, 0)
            chunks.append(Chunk(
                id=chunk_id,
                content=f"Chart: {chart_meta.get('name', 'unknown')}\nVersion: {chart_meta.get('version', 'unknown')}",
                chunk_index=0,
                start_char=0,
                end_char=0,
                metadata={"type": "chart_metadata", **chart_meta},
            ))

        values = self._parse_values_yaml(text)
        if values:
            chunk_id = self._make_chunk_id(source_id, 1)
            chunks.append(Chunk(
                id=chunk_id,
                content=self._format_values(values),
                chunk_index=1,
                start_char=0,
                end_char=0,
                metadata={"type": "values"},
            ))

        taken = int((time.time() - start) * 1000)
        return ChunkResult(
            source_id=source_id,
            source_type="helm",
            chunks=chunks,
            total_chars=len(text),
            took_ms=taken,
        )

    def _parse_chart_yaml(self, content: str) -> Dict[str, Any]:
        try:
            result = {}
            for line in content.split("\n"):
                if line.strip().startswith("name:"):
                    result["name"] = line.split(":", 1)[1].strip()
                elif line.strip().startswith("version:"):
                    result["version"] = line.split(":", 1)[1].strip()
                elif line.strip().startswith("apiVersion:"):
                    result["apiVersion"] = line.split(":", 1)[1].strip()
            return result
        except Exception:
            return {}

    def _parse_values_yaml(self, content: str) -> Dict[str, Any]:
        try:
            return yaml.safe_load(content) or {}
        except Exception:
            return {}

    def _format_values(self, values: Dict[str, Any]) -> str:
        lines = []
        for key, val in values.items():
            if isinstance(val, dict):
                lines.append(f"{key}:")
                for k, v in val.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"{key}: {val}")
        return "\n".join(lines)

    def _make_chunk_id(self, source_id: str, chunk_idx: int) -> str:
        raw = f"{source_id}:{chunk_idx}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_helm_chunker() -> HelmChartChunker:
    return HelmChartChunker()