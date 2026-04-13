"""
Chunker - Text chunking for documents and code.

Provides DocumentChunker and CodeChunker with configurable
chunk sizes, overlap, and metadata extraction.
"""

import re
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path


@dataclass
class Chunk:
    id: str
    content: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkResult:
    source_id: str
    source_type: str
    chunks: List[Chunk]
    total_chars: int
    took_ms: int
    error: Optional[str] = None


class TextChunker(ABC):
    @abstractmethod
    def chunk(self, text: str, source_id: str) -> ChunkResult:
        pass


class DocumentChunker(TextChunker):
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
        language: str = "en",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.language = language

    def chunk(self, text: str, source_id: str) -> ChunkResult:
        import time

        start = time.time()
        chunks = []

        if not text or not text.strip():
            return ChunkResult(
                source_id=source_id,
                source_type="document",
                chunks=[],
                total_chars=0,
                took_ms=0,
            )

        text_len = len(text)
        pos = 0
        idx = 0

        while pos < text_len:
            chunk_end = min(pos + self.chunk_size, text_len)
            chunk_text = text[pos:chunk_end]

            if chunk_end < text_len:
                chunk_text = self._split_on_sentence_boundary(chunk_text)

            if len(chunk_text) < self.min_chunk_size and chunks:
                break

            chunk_id = self._make_chunk_id(source_id, idx)
            chunks.append(
                Chunk(
                    id=chunk_id,
                    content=chunk_text,
                    chunk_index=idx,
                    start_char=pos,
                    end_char=pos + len(chunk_text),
                )
            )

            pos += len(chunk_text)
            if pos >= text_len:
                break
            pos = pos - self.chunk_overlap
            idx += 1

        took = int((time.time() - start) * 1000)
        return ChunkResult(
            source_id=source_id,
            source_type="document",
            chunks=chunks,
            total_chars=text_len,
            took_ms=took,
        )

    def _split_on_sentence_boundary(self, text: str) -> str:
        sentence_endings = r"[.!?]+\s+"
        matches = list(re.finditer(sentence_endings, text))
        if not matches:
            return text
        last_match = matches[-1]
        return text[: last_match.end()]

    def _make_chunk_id(self, source_id: str, chunk_idx: int) -> str:
        raw = f"{source_id}:{chunk_idx}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


class MarkdownChunker(DocumentChunker):
    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 200):
        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def chunk(self, text: str, source_id: str) -> ChunkResult:
        import time

        start = time.time()
        chunks = []

        lines = text.split("\n")
        current_chunk = []
        current_size = 0
        idx = 0
        pos = 0

        for line in lines:
            line_len = len(line)
            if current_size + line_len > self.chunk_size and current_chunk:
                chunk_text = "\n".join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    chunk_id = self._make_chunk_id(source_id, idx)
                    chunks.append(
                        Chunk(
                            id=chunk_id,
                            content=chunk_text,
                            chunk_index=idx,
                            start_char=pos,
                            end_char=pos + len(chunk_text),
                        )
                    )
                    idx += 1

                overlap_lines = []
                overlap_size = 0
                for l in reversed(current_chunk):
                    if overlap_size >= self.chunk_overlap:
                        break
                    overlap_lines.insert(0, l)
                    overlap_size += len(l)
                current_chunk = overlap_lines
                current_size = overlap_size

            current_chunk.append(line)
            current_size += line_len + 1

        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunk_id = self._make_chunk_id(source_id, idx)
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        content=chunk_text,
                        chunk_index=idx,
                        start_char=pos,
                        end_char=pos + len(chunk_text),
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


class CodeChunker(TextChunker):
    def __init__(
        self,
        max_entity_lines: int = 200,
        include_docstrings: bool = True,
        language_hints: Optional[Dict[str, str]] = None,
    ):
        self.max_entity_lines = max_entity_lines
        self.include_docstrings = include_docstrings
        self.language_hints = language_hints or {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".tsvelte": "svelte",
        }

    def chunk_file(self, file_path: str, content: str) -> ChunkResult:
        import time

        start = time.time()
        path = Path(file_path)
        source_id = f"{path.stem}:{path.suffix.lstrip('.')}"

        language = self._detect_language(path)
        chunks = []

        entities = self._extract_entities(content, language)

        for idx, entity in enumerate(entities):
            chunk_id = self._make_chunk_id(source_id, idx)
            chunks.append(
                Chunk(
                    id=chunk_id,
                    content=entity["content"],
                    chunk_index=idx,
                    start_char=entity.get("start_line", 0),
                    end_char=entity.get("end_line", 0),
                    metadata={
                        "entity_type": entity.get("type"),
                        "entity_name": entity.get("name"),
                        "language": language,
                    },
                )
            )

        took = int((time.time() - start) * 1000)
        return ChunkResult(
            source_id=source_id,
            source_type="code",
            chunks=chunks,
            total_chars=len(content),
            took_ms=took,
        )

    def chunk(self, text: str, source_id: str) -> ChunkResult:
        import time

        start = time.time()
        chunks = []
        entities = self._extract_entities(text, "python")

        for idx, entity in enumerate(entities):
            chunk_id = self._make_chunk_id(source_id, idx)
            chunks.append(
                Chunk(
                    id=chunk_id,
                    content=entity["content"],
                    chunk_index=idx,
                    start_char=entity.get("start_line", 0),
                    end_char=entity.get("end_line", 0),
                    metadata={
                        "entity_type": entity.get("type"),
                        "entity_name": entity.get("name"),
                    },
                )
            )

        took = int((time.time() - start) * 1000)
        return ChunkResult(
            source_id=source_id,
            source_type="code",
            chunks=chunks,
            total_chars=len(text),
            took_ms=took,
        )

    def _detect_language(self, path: Path) -> str:
        ext = path.suffix.lstrip(".")
        lang = self.language_hints.get(f".{ext}")
        if lang:
            return lang
        if ext == "tsx" or ext == "jsx":
            return "typescript"
        return ext

    def _extract_entities(self, code: str, language: str) -> List[Dict[str, Any]]:
        entities = []
        lines = code.split("\n")

        if language == "python":
            entities = self._extract_python_entities(lines)
        else:
            entities = self._extract_generic_entities(lines)

        return entities

    def _extract_python_entities(self, lines: List[str]) -> List[Dict[str, Any]]:
        entities = []
        current_entity = None
        entity_lines = []
        indent_level = 0

        for idx, line in enumerate(lines):
            stripped = line.strip()

            is_class = re.match(r"^class \w+", stripped)
            is_def = re.match(r"^def \w+", stripped)
            is_async = re.match(r"^async def \w+", stripped)

            if is_class or is_def or is_async:
                if current_entity and entity_lines:
                    content = "\n".join(entity_lines)
                    if len(content) > 20:
                        entities.append(
                            {
                                "name": current_entity["name"],
                                "type": current_entity["type"],
                                "content": content,
                                "start_line": current_entity["start"],
                                "end_line": idx - 1,
                            }
                        )

                if is_class:
                    match = re.search(r"class (\w+)", stripped)
                    name = match.group(1) if match else "UnknownClass"
                    current_entity = {"name": name, "type": "class", "start": idx}
                elif is_async:
                    match = re.search(r"async def (\w+)", stripped)
                    name = match.group(1) if match else "UnknownFunction"
                    current_entity = {
                        "name": name,
                        "type": "async_function",
                        "start": idx,
                    }
                else:
                    match = re.search(r"def (\w+)", stripped)
                    name = match.group(1) if match else "UnknownFunction"
                    current_entity = {"name": name, "type": "function", "start": idx}

                entity_lines = [line]

            elif current_entity:
                if line.strip() or len(entity_lines) < self.max_entity_lines:
                    entity_lines.append(line)
                else:
                    content = "\n".join(entity_lines)
                    if len(content) > 20:
                        entities.append(
                            {
                                "name": current_entity["name"],
                                "type": current_entity["type"],
                                "content": content,
                                "start_line": current_entity["start"],
                                "end_line": idx - 1,
                            }
                        )
                    current_entity = None
                    entity_lines = []

        if current_entity and entity_lines:
            content = "\n".join(entity_lines)
            if len(content) > 20:
                entities.append(
                    {
                        "name": current_entity["name"],
                        "type": current_entity["type"],
                        "content": content,
                        "start_line": current_entity["start"],
                        "end_line": len(lines) - 1,
                    }
                )

        return entities

    def _extract_generic_entities(self, lines: List[str]) -> List[Dict[str, Any]]:
        entities = []
        current_block = []
        idx = 0

        while idx < len(lines):
            line = lines[idx]
            stripped = line.strip()

            if stripped.startswith("function ") or stripped.startswith("func "):
                name_match = re.search(r"(?:function|func)\s+(\w+)", stripped)
                name = name_match.group(1) if name_match else "unknown"
                start_idx = idx

                brace_count = 0
                current_block = [line]
                idx += 1

                while idx < len(lines):
                    current_block.append(lines[idx])
                    brace_count += lines[idx].count("{") - lines[idx].count("}")
                    if brace_count == 0 and len(current_block) > 1:
                        break
                    idx += 1

                if current_block:
                    entities.append(
                        {
                            "name": name,
                            "type": "function",
                            "content": "\n".join(current_block),
                            "start_line": start_idx,
                            "end_line": idx,
                        }
                    )

            idx += 1

        if not entities:
            chunk_size = 100
            for i in range(0, len(lines), chunk_size):
                chunk_lines = lines[i : i + chunk_size]
                entities.append(
                    {
                        "name": f"chunk_{i // chunk_size}",
                        "type": "block",
                        "content": "\n".join(chunk_lines),
                        "start_line": i,
                        "end_line": min(i + chunk_size, len(lines)),
                    }
                )

        return entities

    def _make_chunk_id(self, source_id: str, chunk_idx: int) -> str:
        raw = f"{source_id}:{chunk_idx}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_document_chunker(language: str = "en") -> DocumentChunker:
    return DocumentChunker(language=language)


def get_code_chunker() -> CodeChunker:
    return CodeChunker()


def get_markdown_chunker() -> MarkdownChunker:
    return MarkdownChunker()
