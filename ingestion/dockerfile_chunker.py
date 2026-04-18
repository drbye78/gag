import re
import hashlib
from typing import Any, Dict, List
from dataclasses import dataclass

from ingestion.chunker import Chunk, ChunkResult, TextChunker


@dataclass
class DockerfileInstruction:
    instruction: str
    argument: str
    line_number: int


class DockerfileChunker(TextChunker):
    def __init__(self):
        pass

    def chunk(self, text: str, source_id: str) -> ChunkResult:
        import time
        start = time.time()

        instructions = self._parse_dockerfile(text)
        chunks = []

        by_type: Dict[str, List[str]] = {}
        for inst in instructions:
            if inst.instruction not in by_type:
                by_type[inst.instruction] = []
            by_type[inst.instruction].append(inst.argument)

        idx = 0
        for inst_type, args in by_type.items():
            chunk_id = self._make_chunk_id(source_id, idx)
            chunks.append(Chunk(
                id=chunk_id,
                content=f"{inst_type}:\n" + "\n".join(f"  {a}" for a in args),
                chunk_index=idx,
                start_char=0,
                end_char=0,
                metadata={"instruction": inst_type, "count": len(args)},
            ))
            idx += 1

        taken = int((time.time() - start) * 1000)
        return ChunkResult(
            source_id=source_id,
            source_type="dockerfile",
            chunks=chunks,
            total_chars=len(text),
            took_ms=taken,
        )

    def _parse_dockerfile(self, content: str) -> List[DockerfileInstruction]:
        instructions = []
        lines = content.split("\n")

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            match = re.match(r"^(\w+)\s+(.+)$", stripped)
            if match:
                instructions.append(DockerfileInstruction(
                    instruction=match.group(1).upper(),
                    argument=match.group(2).strip(),
                    line_number=idx,
                ))

        return instructions

    def _make_chunk_id(self, source_id: str, chunk_idx: int) -> str:
        raw = f"{source_id}:{chunk_idx}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_dockerfile_chunker() -> DockerfileChunker:
    return DockerfileChunker()