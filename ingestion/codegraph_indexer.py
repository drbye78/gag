"""
CodeGraphContext-aware ingestion pipeline.

Provides AST-based code parsing, entity/relationship extraction,
and full graph indexing via CodeGraphContext CLI.

Architecture:
- CodeGraphIndexer: Wraps CodeGraphContext CLI (cgc)
- CLI-based: Uses subprocess for all operations
- Entity extraction: functions, classes, modules from graph
- Relationship inference: CALLS, IMPORTS, INHERITS from graph
- Dual indexing: Vector (chunks) + Graph (entities/relationships)

Integration:
- Primary: `cgc` CLI (v0.4+)
- Database: FalkorDB Lite (bundled) or external FalkorDB/Neo4j
- Indexing: cgc index <path> to add repositories
"""

import asyncio
import logging
import os
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import get_settings
from core.errors import IngestionError

logger = logging.getLogger(__name__)

# Check CLI availability
def _check_cgc_available() -> bool:
    try:
        result = subprocess.run(
            ["cgc", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

_cgc_available = _check_cgc_available()

if _cgc_available:
    logger.info("CodeGraphContext CLI available for ingestion")
else:
    logger.info("CodeGraphContext CLI not installed (optional for ingestion)")

CODEGRAPH_AVAILABLE = _cgc_available


class CodeGraphIndexingMode(str, Enum):
    """Indexing modes for CodeGraphContext."""

    WATCH = "watch"  # Live directory watching
    ONESHOT = "oneshot"  # Single ingestion
    BATCH = "batch"  # Multi-file batch


@dataclass
class CodeGraphChunk:
    """Enhanced code chunk with graph metadata."""

    id: str
    content: str
    chunk_index: int
    start_line: int = 0
    end_line: int = 0
    file_path: str = ""
    entity_type: str = ""  # function, class, module
    entity_name: str = ""
    language: str = ""
    complexity: int = 0
    callers: List[str] = field(default_factory=list)
    callees: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeGraphEntity:
    """Entity extracted from code graph."""

    id: str
    name: str
    node_type: str  # Function, Class, Module
    file_path: str
    start_line: int
    end_line: int
    language: str
    complexity: int = 0
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeGraphRelationship:
    """Relationship between entities."""

    id: str
    source_id: str
    target_id: str
    relation_type: str  # CALLS, IMPORTS, INHERITS, DEFINES
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeGraphIndexResult:
    """Result of CodeGraphContext indexing."""

    indexed_files: int
    indexed_entities: int
    indexed_relationships: int
    chunks: List[CodeGraphChunk]
    entities: List[CodeGraphEntity]
    relationships: List[CodeGraphRelationship]
    took_ms: int
    errors: List[str] = field(default_factory=list)


class CodeGraphIndexer:
    """
    CodeGraphContext-based indexer for code.

    Features:
    - AST parsing for 17+ languages
    - Entity extraction (functions, classes, modules)
    - Relationship inference (CALLS, IMPORTS, INHERITS)
    - Complexity metrics (cyclomatic)
    - Dead code detection

    Usage:
        indexer = CodeGraphIndexer(repo_path="/path/to/repo")
        result = await indexer.index_codebase(files)
        #chunks, entities, relationships available
    """

    def __init__(
        self,
        repo_path: str = ".",
        watch: bool = False,
        batch_size: int = 100,
    ):
        self.repo_path = repo_path
        self.watch = watch
        self.batch_size = batch_size
        self._indexed_files: set = set()

    async def index_codebase(
        self,
        files: Dict[str, str],
        mode: CodeGraphIndexingMode = CodeGraphIndexingMode.ONESHOT,
    ) -> CodeGraphIndexResult:
        """
        Index a codebase using CodeGraphContext.

        Args:
            files: Dict[file_path -> content]
            mode: WATCH, ONESHOT, or BATCH

        Returns:
            CodeGraphIndexResult with chunks, entities, relationships
        """
        if not CODEGRAPH_AVAILABLE:
            return CodeGraphIndexResult(
                indexed_files=0,
                indexed_entities=0,
                indexed_relationships=0,
                chunks=[],
                entities=[],
                relationships=[],
                took_ms=0,
                errors=["CodeGraphContext CLI not installed"],
            )

        start = int(time.time() * 1000)
        chunks = []
        entities = []
        relationships = []
        errors = []
        indexed_files = 0

        try:
            # Index each file to CodeGraphContext
            for file_path, content in files.items():
                try:
                    result = await add_code_to_graph(
                        path=file_path,
                        is_dependency=False,
                    )
                    if result.get("status") == "completed":
                        indexed_files += 1
                        self._indexed_files.add(file_path)
                except Exception as e:
                    errors.append(f"Failed to index {file_path}: {e}")

            # Query entities from graph
            entities = await self._extract_entities(list(files.keys()))

            # Query relationships from graph
            relationships = await self._extract_relationships(entities)

            # Build chunks from entities
            for entity in entities:
                chunk = CodeGraphChunk(
                    id=entity.id,
                    content=self._build_chunk_content(entity, files),
                    chunk_index=len(chunks),
                    start_line=entity.start_line,
                    end_line=entity.end_line,
                    file_path=entity.file_path,
                    entity_type=entity.node_type,
                    entity_name=entity.name,
                    language=entity.language,
                    complexity=entity.complexity,
                )
                chunks.append(chunk)

            # Start watching if requested
            if self.watch and mode == CodeGraphIndexingMode.WATCH:
                await self._start_watching()

        except Exception as e:
            logger.exception("CodeGraphContext indexing failed")
            errors.append(str(e))

        took = int(time.time() * 1000) - start
        return CodeGraphIndexResult(
            indexed_files=indexed_files,
            indexed_entities=len(entities),
            indexed_relationships=len(relationships),
            chunks=chunks,
            entities=entities,
            relationships=relationships,
            took_ms=took,
            errors=errors,
        )

    async def _extract_entities(
        self,
        file_paths: List[str],
    ) -> List[CodeGraphEntity]:
        """Extract entities (functions, classes, modules) from code graph."""
        entities = []

        for file_path in file_paths:
            try:
                # Query functions
                result = await find_code(
                    query=f"function",
                    repo_path=file_path,
                )
                for item in result.get("ranked_results", []):
                    ent = CodeGraphEntity(
                        id=item.get("id", ""),
                        name=item.get("name", ""),
                        node_type="Function",
                        file_path=item.get("path", file_path),
                        start_line=item.get("start_line", 0),
                        end_line=item.get("end_line", 0),
                        language=item.get("language", "unknown"),
                        complexity=await self._get_complexity(
                            item.get("name", ""),
                            file_path,
                        ),
                    )
                    entities.append(ent)

                # Query classes
                result = await find_code(
                    query=f"class",
                    repo_path=file_path,
                )
                for item in result.get("ranked_results", []):
                    ent = CodeGraphEntity(
                        id=item.get("id", ""),
                        name=item.get("name", ""),
                        node_type="Class",
                        file_path=item.get("path", file_path),
                        start_line=item.get("start_line", 0),
                        end_line=item.get("end_line", 0),
                        language=item.get("language", "unknown"),
                    )
                    entities.append(ent)

            except Exception as e:
                logger.warning(f"Entity extraction failed for {file_path}: {e}")

        return entities

    async def _extract_relationships(
        self,
        entities: List[CodeGraphEntity],
    ) -> List[CodeGraphRelationship]:
        """Extract relationships between entities from code graph."""
        relationships = []

        for entity in entities:
            try:
                result = await analyze_code_relationships(
                    query_type="find_callees",
                    target=entity.name,
                    context=entity.file_path,
                )

                for item in result.get("results", []):
                    rel = CodeGraphRelationship(
                        id=str(uuid.uuid4()),
                        source_id=entity.id,
                        target_id=item.get("target_id", ""),
                        relation_type="CALLS",
                        properties=item,
                    )
                    relationships.append(rel)

            except Exception as e:
                logger.warning(
                    f"Relationship extraction failed for {entity.name}: {e}"
                )

        return relationships

    async def _get_complexity(self, function_name: str, file_path: str) -> int:
        """Get cyclomatic complexity for a function."""
        if not CODEGRAPH_AVAILABLE:
            return 0

        try:
            result = await calculate_cyclomatic_complexity(
                function_name=function_name,
                path=file_path,
            )
            return result.get("cyclomatic_complexity", 0)
        except Exception:
            return 0

    def _build_chunk_content(
        self,
        entity: CodeGraphEntity,
        files: Dict[str, str],
    ) -> str:
        """Build chunk content from entity and file content."""
        content = files.get(entity.file_path, "")
        lines = content.split("\n")

        start = max(0, entity.start_line - 1)
        end = min(len(lines), entity.end_line)

        return "\n".join(lines[start:end])

    async def _start_watching(self) -> None:
        """Start live directory watching."""
        if not CODEGRAPH_AVAILABLE:
            return

        try:
            await watch_directory(path=self.repo_path)
            logger.info(f"Started watching {self.repo_path}")
        except Exception as e:
            logger.warning(f"Failed to start watching: {e}")

    async def find_dead_code(
        self,
        exclude_decorators: Optional[List[str]] = None,
    ) -> List[CodeGraphEntity]:
        """Find unused functions (dead code)."""
        if not CODEGRAPH_AVAILABLE:
            return []

        try:
            result = await find_dead_code(
                exclude_decorated_with=exclude_decorators or [],
                repo_path=self.repo_path,
            )

            entities = []
            for item in result.get("functions", []):
                entities.append(
                    CodeGraphEntity(
                        id=item.get("id", ""),
                        name=item.get("name", ""),
                        node_type="Function",
                        file_path=item.get("path", ""),
                        start_line=item.get("start_line", 0),
                        end_line=item.get("end_line", 0),
                        language=item.get("language", "unknown"),
                    )
                )
            return entities
        except Exception as e:
            logger.warning(f"Dead code detection failed: {e}")
            return []

    async def get_complex_functions(
        self,
        limit: int = 10,
    ) -> List[CodeGraphEntity]:
        """Get most complex functions."""
        if not CODEGRAPH_AVAILABLE:
            return []

        try:
            result = await find_most_complex_functions(
                limit=limit,
                repo_path=self.repo_path,
            )

            entities = []
            for item in result.get("functions", []):
                entities.append(
                    CodeGraphEntity(
                        id=item.get("id", ""),
                        name=item.get("name", ""),
                        node_type="Function",
                        file_path=item.get("path", ""),
                        start_line=item.get("start_line", 0),
                        end_line=item.get("end_line", 0),
                        language=item.get("language", "unknown"),
                        complexity=item.get("cyclomatic_complexity", 0),
                    )
                )
            return entities
        except Exception as e:
            logger.warning(f"Complex function detection failed: {e}")
            return []

    async def execute_cypher(
        self,
        query: str,
    ) -> List[Dict[str, Any]]:
        """Execute custom Cypher query on code graph."""
        if not CODEGRAPH_AVAILABLE:
            return []

        try:
            result = await execute_cypher_query(cypher_query=query)
            return result.get("results", [])
        except Exception as e:
            logger.warning(f"Cypher query failed: {e}")
            return []

    @property
    def is_available(self) -> bool:
        """Check if CodeGraphContext is available."""
        return CODEGRAPH_AVAILABLE


class CodeGraphFallbackIndexer:
    """
    Fallback indexer when CodeGraphContext is not available.

    Uses simple regex-based parsing to provides basic functionality.
    """

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path

    async def index_codebase(
        self,
        files: Dict[str, str],
        mode: CodeGraphIndexingMode = CodeGraphIndexingMode.ONESHOT,
    ) -> CodeGraphIndexResult:
        """Index using regex-based fallback."""
        start = int(time.time() * 1000)
        chunks = []
        entities = []
        relationships = []

        import re

        for file_path, content in files.items():
            # Simple function extraction
            for match in re.finditer(
                r"(?:^def |^async def |^class )(\w+)",
                content,
                re.MULTILINE,
            ):
                entity_type = (
                    "Function"
                    if "def " in match.group()
                    else "Class"
                )
                entity = CodeGraphEntity(
                    id=str(uuid.uuid4()),
                    name=match.group(1).strip(),
                    node_type=entity_type,
                    file_path=file_path,
                    start_line=content[: match.start()].count("\n") + 1,
                    end_line=content[: match.end()].count("\n") + 1,
                    language=Path(file_path).suffix.lstrip("."),
                )
                entities.append(entity)

                # Build chunk
                lines = content.split("\n")
                start_line = entity.start_line - 1
                end_line = min(len(lines), start_line + 50)
                chunk_text = "\n".join(lines[start_line:end_line])

                chunks.append(
                    CodeGraphChunk(
                        id=entity.id,
                        content=chunk_text,
                        chunk_index=len(chunks),
                        start_line=entity.start_line,
                        end_line=entity.end_line,
                        file_path=file_path,
                        entity_type=entity_type,
                        entity_name=entity.name,
                        language=entity.language,
                    )
                )

        took = int(time.time() * 1000) - start
        return CodeGraphIndexResult(
            indexed_files=len(files),
            indexed_entities=len(entities),
            indexed_relationships=len(relationships),
            chunks=chunks,
            entities=entities,
            relationships=relationships,
            took_ms=took,
            errors=[],
        )

    @property
    def is_available(self) -> bool:
        """Always available as fallback."""
        return True


def get_codegraph_indexer(
    repo_path: str = ".",
    watch: bool = False,
) -> "CodeGraphIndexer | CodeGraphFallbackIndexer":
    if CODEGRAPH_AVAILABLE:
        return CodeGraphIndexer(repo_path=repo_path, watch=watch)
    return CodeGraphFallbackIndexer(repo_path=repo_path)