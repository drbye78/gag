import hashlib
import re
from dataclasses import dataclass
from typing import Dict, List

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

        # Detect multi-stage builds by grouping instructions by FROM directives
        stages = self._split_stages(instructions)

        if len(stages) > 1:
            # Multi-stage: chunk by stage
            for idx, (stage_name, stage_instructions) in enumerate(stages.items()):
                chunk_id = self._make_chunk_id(source_id, idx)
                content_lines = [
                    f"{inst.instruction} {inst.argument}" for inst in stage_instructions
                ]
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        content=f"Stage: {stage_name}\n" + "\n".join(content_lines),
                        chunk_index=idx,
                        start_char=0,
                        end_char=0,
                        metadata={
                            "stage": stage_name,
                            "instruction_count": len(stage_instructions),
                        },
                    )
                )
        else:
            # Single-stage: chunk by instruction type
            by_type: Dict[str, List[str]] = {}
            for inst in instructions:
                if inst.instruction not in by_type:
                    by_type[inst.instruction] = []
                by_type[inst.instruction].append(inst.argument)

            idx = 0
            for inst_type, args in by_type.items():
                chunk_id = self._make_chunk_id(source_id, idx)
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        content=f"{inst_type}:\n" + "\n".join(f"  {a}" for a in args),
                        chunk_index=idx,
                        start_char=0,
                        end_char=0,
                        metadata={"instruction": inst_type, "count": len(args)},
                    )
                )
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
                instructions.append(
                    DockerfileInstruction(
                        instruction=match.group(1).upper(),
                        argument=match.group(2).strip(),
                        line_number=idx,
                    )
                )

        return instructions

    def _split_stages(
        self, instructions: List[DockerfileInstruction]
    ) -> Dict[str, List[DockerfileInstruction]]:
        """Split instructions into build stages based on FROM directives.

        Returns an ordered dict mapping stage name to its instructions.
        A single FROM produces one stage; multiple FROMs indicate multi-stage.
        """
        from collections import OrderedDict

        stages: OrderedDict[str, List[DockerfileInstruction]] = OrderedDict()
        current_stage = "stage_0"
        stage_counter = 0

        for inst in instructions:
            if inst.instruction == "FROM":
                # Parse stage alias: FROM image AS builder
                alias_match = re.match(r".*\bAS\s+(\w+)", inst.argument, re.IGNORECASE)
                if alias_match:
                    current_stage = alias_match.group(1)
                else:
                    stage_counter += 1
                    current_stage = f"stage_{stage_counter}"
                if current_stage not in stages:
                    stages[current_stage] = []
            else:
                if current_stage not in stages:
                    stages[current_stage] = []
                stages[current_stage].append(inst)

        return stages

    def _make_chunk_id(self, source_id: str, chunk_idx: int) -> str:
        raw = f"{source_id}:{chunk_idx}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_dockerfile_chunker() -> DockerfileChunker:
    return DockerfileChunker()
