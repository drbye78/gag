"""
Bidirectional Code-Diagram Sync.

Enables synchronization between code and diagrams:
- Code → Diagram (generate diagram from code)
- Diagram → Code (extract code from diagram)
"""

import re
import ast
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SyncResult:
    success: bool
    direction: str
    output: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class CodeToDiagramConverter:
    """Convert code to UML diagrams."""

    @classmethod
    def parse_python_class(cls, code: str) -> SyncResult:
        classes = []
        relationships = []

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    attrs = []
                    methods = []

                    for item in node.body:
                        if isinstance(item, ast.AnnAssign):
                            if isinstance(item.target, ast.Name):
                                name = item.target.id
                                atype = "any"
                                if item.annotation and isinstance(
                                    item.annotation, ast.Name
                                ):
                                    atype = item.annotation.id
                                attrs.append({"name": name, "type": atype})
                        elif isinstance(item, ast.FunctionDef):
                            params = [a.arg for a in item.args.args]
                            methods.append({"name": item.name, "params": params})

                    classes.append(
                        {
                            "name": node.name,
                            "attributes": attrs,
                            "methods": methods,
                        }
                    )

                for node_b in ast.walk(tree):
                    if isinstance(node_b, ast.ClassDef):
                        for base in node_b.bases:
                            if isinstance(base, ast.Name):
                                for child in ast.walk(tree):
                                    if isinstance(child, ast.ClassDef):
                                        for base2 in child.bases:
                                            if (
                                                isinstance(base2, ast.Name)
                                                and base2.id == node_b.name
                                            ):
                                                relationships.append(
                                                    {
                                                        "from": child.name,
                                                        "to": node_b.name,
                                                        "type": "inheritance",
                                                    }
                                                )

            from documents.diagram_parser import (
                PlantUMLGenerator,
                DiagramExtractionResult,
                DiagramType,
            )

            result = DiagramExtractionResult(
                diagram_type=DiagramType.UML_CLASS,
                entities=classes,
                relationships=relationships,
                generated_code="",
                confidence=0.9,
            )

            plantuml = PlantUMLGenerator.generate_uml_class(result)

            return SyncResult(
                success=True,
                direction="code_to_diagram",
                output=plantuml,
                metadata={"classes": len(classes)},
            )
        except Exception as e:
            return SyncResult(
                success=False, direction="code_to_diagram", output="", error=str(e)
            )


class DiagramToCodeConverter:
    """Convert UML diagrams to code."""

    @classmethod
    def parse_uml_class(cls, plantuml_text: str) -> SyncResult:
        lines = []
        classes = {}

        current_class = None

        for line in plantuml_text.split("\n"):
            line = line.strip()

            if not line or line.startswith("@") or line.startswith("skinparam"):
                continue

            if "class " in line and "{" in line:
                match = re.search(r"class\s+(\w+)", line)
                if match:
                    current_class = match.group(1)
                    classes[current_class] = {"attributes": [], "methods": []}
            elif current_class and line == "}":
                current_class = None
            elif current_class and line:
                vis = "+" if line.startswith("+") else "-"
                clean = line.lstrip("+- ").strip()
                if ":" in clean:
                    name, atype = clean.split(":", 1)
                    classes[current_class]["attributes"].append(
                        {"name": name.strip(), "type": atype.strip(), "visibility": vis}
                    )
                elif "()" in clean:
                    classes[current_class]["methods"].append(
                        {"name": clean.replace("()", "").strip(), "visibility": vis}
                    )

        for cls_name, cls_data in classes.items():
            lines.append(f"class {cls_name}:")
            for attr in cls_data["attributes"]:
                lines.append(f"    {attr['visibility']} {attr['name']}: {attr['type']}")
            for method in cls_data["methods"]:
                lines.append(f"    {method['visibility']} {method['name']}(): pass")

        return SyncResult(
            success=True,
            direction="diagram_to_code",
            output="\n".join(lines),
            metadata={"classes": len(classes)},
        )


class BidirectionalSync:
    """Main sync orchestrator."""

    @classmethod
    def convert(
        cls,
        input_data: str,
        target_format: str = "python",
        source_type: str = "code",
    ) -> SyncResult:
        if source_type == "code" and target_format in ["plantuml", "mermaid"]:
            return CodeToDiagramConverter.parse_python_class(input_data)
        elif source_type == "uml" and target_format == "python":
            return DiagramToCodeConverter.parse_uml_class(input_data)
        else:
            return SyncResult(
                success=False,
                direction=f"{source_type}_to_{target_format}",
                output="",
                error=f"Unsupported conversion: {source_type} → {target_format}",
            )


def sync_code_diagram(
    code: Optional[str] = None,
    diagram: Optional[str] = None,
    target: str = "python",
) -> SyncResult:
    if code:
        return CodeToDiagramConverter.parse_python_class(code)
    elif diagram:
        return DiagramToCodeConverter.parse_uml_class(diagram)
    return SyncResult(
        success=False, direction="unknown", output="", error="No input provided"
    )
