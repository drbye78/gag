"""
Git Parser - Code entity extraction from git repositories.

Extracts functions, classes, imports, exports
with per-language parsers.
"""

import re
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EntityType(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    MODULE = "module"
    INTERFACE = "interface"
    CONSTANT = "constant"
    VARIABLE = "variable"
    IMPORT = "import"
    EXPORT = "export"


@dataclass
class CodeEntity:
    entity_id: str
    name: str
    entity_type: EntityType
    file_path: str
    start_line: int
    end_line: int
    content: str
    language: str
    parent_entity: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedFile:
    file_path: str
    language: str
    entities: List[CodeEntity]
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    total_lines: int = 0


class CodeParser:
    def __init__(self):
        self._language_parsers = {
            "python": self._parse_python,
            "javascript": self._parse_javascript,
            "typescript": self._parse_typescript,
            "go": self._parse_go,
            "rust": self._parse_rust,
            "java": self._parse_java,
            "csharp": self._parse_csharp,
        }

    def parse(self, content: str, file_path: str) -> ParsedFile:
        language = self._detect_language(file_path)
        parser = self._language_parsers.get(language, self._parse_generic)

        return parser(content, file_path, language)

    def _detect_language(self, file_path: str) -> str:
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".kt": "kotlin",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".scala": "scala",
        }
        import re

        match = re.search(r"\.(\w+)$", file_path)
        if match:
            return ext_map.get(f".{match.group(1)}", "unknown")
        return "unknown"

    def _parse_python(self, content: str, file_path: str, language: str) -> ParsedFile:
        lines = content.split("\n")
        entities = []
        imports = []
        exports = []
        current_entity = None
        in_class = None
        entity_lines = []
        entity_start = 0

        for idx, line in enumerate(lines):
            stripped = line.strip()

            is_import = re.match(r"^(import|from)\s+", stripped)
            is_class = re.match(r"^class\s+(\w+)", stripped)
            is_def = re.match(r"^(async\s+)?def\s+(\w+)", stripped)
            is_decorator = stripped.startswith("@")

            if is_import:
                match = re.search(r"^(?:from\s+)?(\S+)", stripped)
                if match:
                    imports.append(match.group(1))

            if is_class or is_def:
                if current_entity:
                    entities.append(
                        self._build_entity(
                            current_entity,
                            file_path,
                            entity_lines,
                            entity_start,
                            language,
                        )
                    )

                if is_class:
                    match = re.search(r"class\s+(\w+)", stripped)
                    name = match.group(1) if match else "Unknown"
                    current_entity = {
                        "name": name,
                        "type": EntityType.CLASS,
                        "parent": None if not in_class else in_class,
                    }
                else:
                    match = re.search(r"(?:async\s+)?def\s+(\w+)", stripped)
                    name = match.group(1) if match else "Unknown"
                    entity_type = EntityType.METHOD if in_class else EntityType.FUNCTION
                    current_entity = {
                        "name": name,
                        "type": entity_type,
                        "parent": in_class,
                    }

                entity_start = idx
                entity_lines = [line]

                if is_class and "(" in stripped:
                    base_match = re.search(r"\(([^)]+)\)", stripped)
                    if base_match:
                        bases = base_match.group(1).split(",")
                        current_entity["bases"] = [b.strip() for b in bases]

            elif current_entity:
                entity_lines.append(line)

        if current_entity:
            entities.append(
                self._build_entity(
                    current_entity, file_path, entity_lines, entity_start, language
                )
            )

        export_match = re.search(r"^__all__\s*=\s*\[(.*)\]", content, re.MULTILINE)
        if export_match:
            exports_str = export_match.group(1)
            exports = re.findall(r"['\"](\w+)['\"]", exports_str)

        return ParsedFile(
            file_path=file_path,
            language=language,
            entities=entities,
            imports=imports,
            exports=exports,
            total_lines=len(lines),
        )

    def _parse_javascript(
        self, content: str, file_path: str, language: str
    ) -> ParsedFile:
        lines = content.split("\n")
        entities = []
        imports = []
        exports = []

        for idx, line in enumerate(lines):
            stripped = line.strip()

            if stripped.startswith("import "):
                match = re.search(r'import\s+.*?from\s+["\']([^"\']+)["\']', stripped)
                if match:
                    imports.append(match.group(1))
                else:
                    match = re.search(r'import\s+["\']([^"\']+)["\']', stripped)
                    if match:
                        imports.append(match.group(1))

            if stripped.startswith("export "):
                if "default" in stripped:
                    exports.append("default")
                else:
                    match = re.search(
                        r"export\s+(?:const|let|var|function|class)\s+(\w+)", stripped
                    )
                    if match:
                        exports.append(match.group(1))

        func_pattern = r"(?:export\s+)?(?:const|let|var|function)\s+(\w+)\s*="
        for match in re.finditer(func_pattern, content):
            name = match.group(1)
            entities.append(
                CodeEntity(
                    entity_id=self._generate_id(file_path, name),
                    name=name,
                    entity_type=EntityType.FUNCTION,
                    file_path=file_path,
                    start_line=content[: match.start()].count("\n"),
                    end_line=0,
                    content=name,
                    language=language,
                )
            )

        class_pattern = r"(?:export\s+)?class\s+(\w+)"
        for match in re.finditer(class_pattern, content):
            name = match.group(1)
            entities.append(
                CodeEntity(
                    entity_id=self._generate_id(file_path, name),
                    name=name,
                    entity_type=EntityType.CLASS,
                    file_path=file_path,
                    start_line=content[: match.start()].count("\n"),
                    end_line=0,
                    content=name,
                    language=language,
                )
            )

        return ParsedFile(
            file_path=file_path,
            language=language,
            entities=entities,
            imports=imports,
            exports=exports,
            total_lines=len(lines),
        )

    def _parse_typescript(
        self, content: str, file_path: str, language: str
    ) -> ParsedFile:
        result = self._parse_javascript(content, file_path, language)

        interface_pattern = r"(?:export\s+)?interface\s+(\w+)"
        for match in re.finditer(interface_pattern, content):
            name = match.group(1)
            result.entities.append(
                CodeEntity(
                    entity_id=self._generate_id(file_path, name),
                    name=name,
                    entity_type=EntityType.INTERFACE,
                    file_path=file_path,
                    start_line=content[: match.start()].count("\n"),
                    end_line=0,
                    content=name,
                    language=language,
                )
            )

        return result

    def _parse_go(self, content: str, file_path: str, language: str) -> ParsedFile:
        lines = content.split("\n")
        entities = []
        imports = []
        exports = []

        package_match = re.search(r"^package\s+(\w+)", content, re.MULTILINE)
        package_name = package_match.group(1) if package_match else "main"

        for idx, line in enumerate(lines):
            stripped = line.strip()

            if stripped.startswith("import ("):
                in_import_block = True
                continue
            if stripped.startswith(")"):
                in_import_block = False
                continue
            if in_import_block:
                match = re.match(r'"([^"]+)"', stripped)
                if match:
                    imports.append(match.group(1))

            if re.match(r"^func\s+", stripped):
                match = re.match(
                    r"^func\s+(?:\((\w+)\s+\*)?(\w+)\))?\s*(\w+)", stripped
                )
                if match:
                    name = match.group(3)
                    entities.append(
                        CodeEntity(
                            entity_id=self._generate_id(file_path, name),
                            name=name,
                            entity_type=EntityType.FUNCTION,
                            file_path=file_path,
                            start_line=idx,
                            end_line=idx,
                            content=stripped,
                            language=language,
                        )
                    )

        return ParsedFile(
            file_path=file_path,
            language=language,
            entities=entities,
            imports=imports,
            exports=exports,
            total_lines=len(lines),
        )

    def _parse_rust(self, content: str, file_path: str, language: str) -> ParsedFile:
        lines = content.split("\n")
        entities = []
        imports = []
        exports = []

        for idx, line in enumerate(lines):
            stripped = line.strip()

            if stripped.startswith("use ") and "::" in stripped:
                match = re.search(r"use\s+(.+?);", stripped)
                if match:
                    imports.append(match.group(1))

            pub_match = re.match(r"^pub\s+(?:struct|enum|fn|trait)", stripped)
            struct_match = re.match(r"^(?:pub\s+)?struct\s+(\w+)", stripped)
            enum_match = re.match(r"^(?:pub\s+)?enum\s+(\w+)", stripped)
            fn_match = re.match(r"^(?:pub\s+)?fn\s+(\w+)", stripped)

            if struct_match:
                name = struct_match.group(1)
                entities.append(
                    CodeEntity(
                        entity_id=self._generate_id(file_path, name),
                        name=name,
                        entity_type=EntityType.CLASS,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx,
                        content=stripped,
                        language=language,
                    )
                )
            elif enum_match:
                name = enum_match.group(1)
                entities.append(
                    CodeEntity(
                        entity_id=self._generate_id(file_path, name),
                        name=name,
                        entity_type=EntityType.CLASS,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx,
                        content=stripped,
                        language=language,
                    )
                )
            elif fn_match:
                name = fn_match.group(1)
                entities.append(
                    CodeEntity(
                        entity_id=self._generate_id(file_path, name),
                        name=name,
                        entity_type=EntityType.FUNCTION,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx,
                        content=stripped,
                        language=language,
                    )
                )

        return ParsedFile(
            file_path=file_path,
            language=language,
            entities=entities,
            imports=imports,
            exports=exports,
            total_lines=len(lines),
        )

    def _parse_java(self, content: str, file_path: str, language: str) -> ParsedFile:
        lines = content.split("\n")
        entities = []
        imports = []
        exports = []

        for idx, line in enumerate(lines):
            stripped = line.strip()

            if stripped.startswith("import "):
                match = re.search(r"import\s+(.+);", stripped)
                if match:
                    imports.append(match.group(1))

            class_match = re.match(r"^(?:public\s+)?class\s+(\w+)", stripped)
            interface_match = re.match(r"^(?:public\s+)?interface\s+(\w+)", stripped)
            method_match = re.match(
                r"^\s*(?:public|private|protected)?\s*(?:static)?\s+\w+\s+(\w+)\s*\(",
                stripped,
            )

            if class_match:
                entities.append(
                    CodeEntity(
                        entity_id=self._generate_id(file_path, class_match.group(1)),
                        name=class_match.group(1),
                        entity_type=EntityType.CLASS,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx,
                        content=stripped,
                        language=language,
                    )
                )
            elif interface_match:
                entities.append(
                    CodeEntity(
                        entity_id=self._generate_id(
                            file_path, interface_match.group(1)
                        ),
                        name=interface_match.group(1),
                        entity_type=EntityType.INTERFACE,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx,
                        content=stripped,
                        language=language,
                    )
                )
            elif method_match and idx > 0:
                prev_line = lines[idx - 1].strip()
                if "class " in prev_line or "interface " in prev_line:
                    name = method_match.group(1)
                    entities.append(
                        CodeEntity(
                            entity_id=self._generate_id(file_path, name),
                            name=name,
                            entity_type=EntityType.METHOD,
                            file_path=file_path,
                            start_line=idx,
                            end_line=idx,
                            content=stripped,
                            language=language,
                        )
                    )

        return ParsedFile(
            file_path=file_path,
            language=language,
            entities=entities,
            imports=imports,
            exports=exports,
            total_lines=len(lines),
        )

    def _parse_csharp(self, content: str, file_path: str, language: str) -> ParsedFile:
        lines = content.split("\n")
        entities = []
        imports = []

        for idx, line in enumerate(lines):
            stripped = line.strip()

            if stripped.startswith("using "):
                match = re.search(r"using\s+(.+);", stripped)
                if match:
                    imports.append(match.group(1))

            class_match = re.match(
                r"^(?:public|private|internal)?\s*class\s+(\w+)", stripped
            )
            interface_match = re.match(
                r"^(?:public|private)?\s*interface\s+(\w+)", stripped
            )

            if class_match:
                entities.append(
                    CodeEntity(
                        entity_id=self._generate_id(file_path, class_match.group(1)),
                        name=class_match.group(1),
                        entity_type=EntityType.CLASS,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx,
                        content=stripped,
                        language=language,
                    )
                )
            elif interface_match:
                entities.append(
                    CodeEntity(
                        entity_id=self._generate_id(
                            file_path, interface_match.group(1)
                        ),
                        name=interface_match.group(1),
                        entity_type=EntityType.INTERFACE,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx,
                        content=stripped,
                        language=language,
                    )
                )

        return ParsedFile(
            file_path=file_path,
            language=language,
            entities=entities,
            imports=imports,
            exports=[],
            total_lines=len(lines),
        )

    def _parse_generic(self, content: str, file_path: str, language: str) -> ParsedFile:
        lines = content.split("\n")
        return ParsedFile(
            file_path=file_path,
            language=language,
            entities=[],
            imports=[],
            exports=[],
            total_lines=len(lines),
        )

    def _build_entity(
        self,
        entity_info: Dict[str, Any],
        file_path: str,
        lines: List[str],
        start_line: int,
        language: str,
    ) -> CodeEntity:
        content = "\n".join(lines)
        end_line = start_line + len(lines) - 1

        return CodeEntity(
            entity_id=self._generate_id(file_path, entity_info["name"]),
            name=entity_info["name"],
            entity_type=entity_info["type"],
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            content=content,
            language=language,
            parent_entity=entity_info.get("parent"),
            metadata={"bases": entity_info.get("bases", [])},
        )

    def _generate_id(self, file_path: str, name: str) -> str:
        raw = f"{file_path}:{name}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


_code_parser: Optional[CodeParser] = None


def get_code_parser() -> CodeParser:
    global _code_parser
    if _code_parser is None:
        _code_parser = CodeParser()
    return _code_parser
