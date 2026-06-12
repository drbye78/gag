import logging
import re
import time
from dataclasses import dataclass, field
from typing import List

from ingestion.chunker import Chunk, ChunkResult, TextChunker

logger = logging.getLogger(__name__)


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

    @staticmethod
    def _looks_like_yaml(text: str) -> bool:
        """Heuristic check whether text looks like YAML content."""
        lines = text.strip().split("\n")
        if len(lines) < 2:
            return False
        yaml_indicator = 0
        for line in lines[:10]:
            stripped_line = line.strip()
            if stripped_line and ":" in stripped_line and not stripped_line.startswith("#"):
                # key: value pattern
                if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*:", stripped_line):
                    yaml_indicator += 1
        return yaml_indicator >= 2

    def _extract_yaml_sections(self, text: str) -> List[Section]:
        """Parse YAML front matter and extract sections from it."""
        import yaml  # type: ignore[import-untyped]  # no stubs for PyYAML

        lines = text.split("\n")

        # Handle YAML front matter (--- delimited)
        if lines and lines[0].strip() == "---":
            end_idx = None
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    end_idx = i
                    break
            if end_idx is not None:
                yaml_content = "\n".join(lines[1:end_idx])
                parsed = yaml.safe_load(yaml_content)
                if isinstance(parsed, dict):
                    sections = []
                    for key, value in parsed.items():
                        content = (
                            f"{key}: {value}"
                            if not isinstance(value, (dict, list))
                            else f"{key}: {yaml.dump(value, default_flow_style=True)}"
                        )
                        sections.append(
                            Section(
                                heading=str(key),
                                level=1,
                                content=content,
                                start_line=1,
                                end_line=end_idx,
                                parent_headings=[],
                            )
                        )
                    # Also process any content after the front matter
                    remaining = "\n".join(lines[end_idx + 1 :])
                    if remaining.strip():
                        sections.extend(self._extract_sections(remaining))
                    return sections
                # If not a dict, fall through to regular extraction

        # Try parsing as full YAML document
        parsed = yaml.safe_load(text)
        if isinstance(parsed, dict):
            sections = []
            for key, value in parsed.items():
                content = (
                    f"{key}: {value}"
                    if not isinstance(value, (dict, list))
                    else f"{key}: {yaml.dump(value, default_flow_style=True)}"
                )
                sections.append(
                    Section(
                        heading=str(key),
                        level=1,
                        content=content,
                        start_line=1,
                        end_line=len(lines),
                        parent_headings=[],
                    )
                )
            return sections

        # Fall back to regular section extraction
        return self._extract_sections(text)

    def _create_error_chunk(
        self, source_id: str, text: str, error_msg: str, start_time: float
    ) -> ChunkResult:
        """Create an error chunk when YAML parsing fails."""
        took = int((time.time() - start_time) * 1000)
        return ChunkResult(
            source_id=source_id,
            source_type="document",
            chunks=[
                Chunk(
                    id=self._make_chunk_id(source_id, 0),
                    content=text[:2000] if text else "",
                    chunk_index=0,
                    start_char=0,
                    end_char=len(text) if text else 0,
                    metadata={
                        "parse_error": error_msg,
                        "chunk_type": "error",
                        "original_format": "yaml",
                    },
                )
            ],
            total_chars=len(text) if text else 0,
            took_ms=took,
        )

    def chunk(self, text: str, source_id: str) -> ChunkResult:
        import time

        start = time.time()

        # Check if text looks like YAML and handle it specially
        stripped = text.strip()
        if stripped.startswith("---") or self._looks_like_yaml(stripped):
            try:
                sections = self._extract_yaml_sections(text)
            except Exception as e:
                logger.warning("Failed to parse YAML in %s: %s", source_id, e)
                return self._create_error_chunk(source_id, text, str(e), start)
        else:
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
                            "section_path": " > ".join(section.parent_headings + [section.heading]),
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
                            heading=current_headings[-1] if current_headings else "Document",
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
                            "path": "|".join([section.heading] + section.parent_headings),
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
                                "path": "|".join([section.heading] + section.parent_headings),
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
