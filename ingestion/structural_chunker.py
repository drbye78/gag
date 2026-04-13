from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re

from ingestion.chunker import Chunk, ChunkResult, TextChunker


@dataclass
class Section:
    heading: str
    level: int
    content: str
    start_line: int
    end_line: int
    parent_headings: List[str] = field(default_factory=list)


class StructuralChunker(TextChunker):
    def __init__(
        self,
        chunk_size: int = 1500,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
        preserve_headings: bool = True,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.preserve_headings = preserve_headings

    def chunk(self, text: str, source_id: str) -> ChunkResult:
        import time

        start = time.time()

        sections = self._extract_sections(text)

        chunks = []
        for idx, section in enumerate(sections):
            if len(section.content) <= self.chunk_size:
                chunk_id = self._make_chunk_id(source_id, idx)
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        content=self._format_chunk(section),
                        chunk_index=idx,
                        start_char=0,
                        end_char=len(section.content),
                        metadata={
                            "section_heading": section.heading,
                            "section_level": section.level,
                            "section_path": " > ".join(
                                section.parent_headings + [section.heading]
                            ),
                            "start_line": section.start_line,
                            "end_line": section.end_line,
                        },
                    )
                )
            else:
                subchunks = self._split_section_with_overlap(section)
                for j, sub in enumerate(subchunks):
                    chunk_id = self._make_chunk_id(source_id, idx * 100 + j)
                    chunks.append(
                        Chunk(
                            id=chunk_id,
                            content=sub,
                            chunk_index=idx * 100 + j,
                            start_char=0,
                            end_char=len(sub),
                            metadata={
                                "section_heading": section.heading,
                                "section_level": section.level,
                                "section_path": " > ".join(
                                    section.parent_headings + [section.heading]
                                ),
                                "subchunk_index": j,
                            },
                        )
                    )

        took = int((time.time() - start) * 1000)
        return ChunkResult(
            source_id=source_id,
            source_type="document",
            chunks=chunks,
            total_chars=len(text),
            took_ms=took,
        )

    def _extract_sections(self, text: str) -> List[Section]:
        lines = text.split("\n")
        sections = []

        heading_pattern = r"^(#{1,6})\s+(.+)$"
        current_headings = []
        current_content = []
        content_start_line = 0

        for line_num, line in enumerate(lines, 1):
            match = re.match(heading_pattern, line)

            if match:
                if current_content:
                    sections.append(
                        Section(
                            heading=current_headings[-1]
                            if current_headings
                            else "Document",
                            level=len(current_headings) if current_headings else 0,
                            content="\n".join(current_content),
                            start_line=content_start_line,
                            end_line=line_num - 1,
                            parent_headings=current_headings[:-1]
                            if len(current_headings) > 1
                            else [],
                        )
                    )
                    current_content = []

                level = len(match.group(1))
                heading = match.group(2).strip()

                current_headings = current_headings[: level - 1]
                current_headings.append(heading)
                content_start_line = line_num + 1
            else:
                current_content.append(line)

        if current_content:
            sections.append(
                Section(
                    heading=current_headings[-1] if current_headings else "Document",
                    level=len(current_headings) if current_headings else 0,
                    content="\n".join(current_content),
                    start_line=content_start_line,
                    end_line=len(lines),
                    parent_headings=current_headings[:-1] if current_headings else [],
                )
            )

        if not sections:
            sections.append(
                Section(
                    heading="Document",
                    level=0,
                    content=text,
                    start_line=1,
                    end_line=len(lines),
                    parent_headings=[],
                )
            )

        return sections

    def _split_section_with_overlap(self, section: Section) -> List[str]:
        content = section.content
        chunks = []

        pos = 0
        while pos < len(content):
            chunk_end = min(pos + self.chunk_size, len(content))

            if chunk_end < len(content):
                last_newline = content.rfind("\n", pos, chunk_end)
                if last_newline > pos:
                    chunk_end = last_newline

            chunk = content[pos:chunk_end].strip()
            if chunk:
                chunks.append(chunk)

            pos = chunk_end - self.chunk_overlap
            if pos <= 0:
                break

        return chunks

    def _format_chunk(self, section: Section) -> str:
        if self.preserve_headings and section.heading != "Document":
            return f"{'#' * min(section.level + 1, 6)} {section.heading}\n\n{section.content}"
        return section.content

    def _make_chunk_id(self, source_id: str, chunk_idx: int) -> str:
        import hashlib

        raw = f"{source_id}:{chunk_idx}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


class HierarchicalChunker(StructuralChunker):
    def __init__(
        self,
        chunk_size: int = 1500,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
        max_depth: int = 3,
    ):
        super().__init__(chunk_size, chunk_overlap, min_chunk_size)
        self.max_depth = max_depth

    def chunk(self, text: str, source_id: str) -> ChunkResult:
        import time

        start = time.time()

        sections = self._extract_sections(text)
        chunks = []
        idx = 0

        for section in sections:
            if section.level > self.max_depth:
                continue

            if len(section.content) <= self.chunk_size:
                chunk_id = self._make_chunk_id(source_id, idx)
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        content=self._format_chunk(section),
                        chunk_index=idx,
                        start_char=0,
                        end_char=len(section.content),
                        metadata={
                            "section_heading": section.heading,
                            "section_level": section.level,
                            "depth": section.level,
                            "path": "|".join(
                                [section.heading] + section.parent_headings
                            ),
                            "is_leaf": True,
                        },
                    )
                )
                idx += 1
            else:
                subchunks = self._split_section_with_overlap(section)
                for j, sub in enumerate(subchunks):
                    chunk_id = self._make_chunk_id(source_id, idx)
                    chunks.append(
                        Chunk(
                            id=chunk_id,
                            content=sub,
                            chunk_index=idx,
                            start_char=0,
                            end_char=len(sub),
                            metadata={
                                "section_heading": section.heading,
                                "section_level": section.level,
                                "depth": section.level,
                                "path": "|".join(
                                    [section.heading] + section.parent_headings
                                ),
                                "subchunk_index": j,
                                "is_leaf": False,
                            },
                        )
                    )
                    idx += 1

        took = int((time.time() - start) * 1000)
        return ChunkResult(
            source_id=source_id,
            source_type="document",
            chunks=chunks,
            total_chars=len(text),
            took_ms=took,
        )


def get_structural_chunker() -> StructuralChunker:
    return StructuralChunker()


def get_hierarchical_chunker(max_depth: int = 3) -> HierarchicalChunker:
    return HierarchicalChunker(max_depth=max_depth)
