"""
Specialized Diagram Parser - UML, C4, Architecture Diagrams.

Supports extraction from:
- UML Class, Component, Package, Deployment, Object, Use Case
- C4 (Context, Container, Component, Code)
- Sequence Diagrams

Features:
- Automatic diagram type detection
- Entity and relationship extraction
- Code generation from diagrams
"""

import base64
import io
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from PIL import Image


class DiagramType(str, Enum):
    UNKNOWN = "unknown"
    UML_CLASS = "uml_class"
    UML_COMPONENT = "uml_component"
    UML_PACKAGE = "uml_package"
    UML_DEPLOYMENT = "uml_deployment"
    UML_OBJECT = "uml_object"
    UML_USECASE = "uml_usecase"
    UML_SEQUENCE = "uml_sequence"
    UML_ACTIVITY = "uml_activity"
    UML_STATE = "uml_state"
    C4_CONTEXT = "c4_context"
    C4_CONTAINER = "c4_container"
    C4_COMPONENT = "c4_component"
    C4_CODE = "c4_code"
    ARCHITECTURE = "architecture"
    FLOWCHART = "flowchart"


@dataclass
class UMLClass:
    name: str
    attributes: List[Dict[str, Any]] = field(default_factory=list)
    methods: List[Dict[str, Any]] = field(default_factory=list)
    visibility: str = "public"
    abstract: bool = False
    stereotype: str = ""


@dataclass
class UMLRelationship:
    source: str
    target: str
    type: str
    label: str = ""
    source_multiplicity: str = ""
    target_multiplicity: str = ""


@dataclass
class SequenceMessage:
    from_lifeline: str
    to_lifeline: str
    message: str
    type: str = "sync"
    order: int = 0


@dataclass
class C4Container:
    name: str
    technology: str = ""
    description: str = ""
    responsibilities: List[str] = field(default_factory=list)


@dataclass
class DiagramExtractionResult:
    diagram_type: DiagramType
    entities: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    generated_code: str = ""
    confidence: float = 0.0
    error: Optional[str] = None


class DiagramTypeDetector:
    VISUAL_INDICATORS = {
        DiagramType.UML_CLASS: [
            r"class\s+\w+",
            r"^\+\w+\(\)",
            r"-\w+\(\)",
            r"#\w+\(\)",
            r"<<\w+>>",
            r"interface",
            r"abstract",
        ],
        DiagramType.UML_COMPONENT: [
            r"<<component>>",
            r"<<service>>",
            r"<<library>>",
            r"\[\]",
            r"component",
            r"provided interface",
            r"required interface",
        ],
        DiagramType.UML_PACKAGE: [
            r"package",
            r"folder",
            r"namespace",
            r"::",
            r"package",
        ],
        DiagramType.UML_DEPLOYMENT: [
            r"node",
            r"artifact",
            r"deployment",
            r"server",
            r"database",
            r"execution environment",
            r"device",
        ],
        DiagramType.UML_OBJECT: [r"object", r":", r"instance", r":\w+\(\)"],
        DiagramType.UML_USECASE: [
            r"actor",
            r"use case",
            r"ellipse",
            r"stick figure",
            r"system boundary",
        ],
        DiagramType.UML_SEQUENCE: [
            r"lifeline",
            r"participant",
            r"activate",
            r"deactivate",
            r"->>",
            r"-->",
            r"loop",
            r"alt",
            r"opt",
            r"ref",
        ],
        DiagramType.C4_CONTEXT: [
            r"C4",
            r"Context",
            r"person",
            r"external system",
            r"software system",
            r"context",
        ],
        DiagramType.C4_CONTAINER: [
            r"C4",
            r"Container",
            r"database",
            r"service",
            r"app",
            r"SPA",
            r"container",
        ],
        DiagramType.C4_COMPONENT: [r"C4", r"Component", r"inside container"],
    }

    @classmethod
    def detect(cls, image: Any, extracted_text: str) -> DiagramType:
        text = extracted_text.lower()

        for diag_type, patterns in cls.VISUAL_INDICATORS.items():
            matches = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
            if matches >= 2:
                return diag_type

        if "sequence" in text:
            return DiagramType.UML_SEQUENCE
        if "class" in text and "diagram" in text:
            return DiagramType.UML_CLASS
        if "c4" in text:
            return DiagramType.C4_CONTAINER
        if "container" in text:
            return DiagramType.C4_CONTAINER

        return DiagramType.UNKNOWN


class UMLClassExtractor:
    @classmethod
    def extract(cls, text: str) -> DiagramExtractionResult:
        entities = []
        relationships = []

        class_pattern = r"(\w+)\s*\{([^}]+)\}"
        for match in re.finditer(class_pattern, text):
            class_name = match.group(1).strip()
            class_body = match.group(2)

            attributes = []
            for line in class_body.split("\n"):
                line = line.strip()
                if not line or "(" in line:
                    continue

                vis = (
                    "+"
                    if line.startswith("+")
                    else "-"
                    if line.startswith("-")
                    else "#"
                )
                name = re.sub(r"^[+\-#]\s*", "", line).split(":")[0].strip()
                atype = line.split(":")[-1].strip() if ":" in line else "unknown"
                if atype == line:
                    atype = "unknown"

                if "(" in line:
                    continue

                attributes.append({"name": name, "type": atype, "visibility": vis})

            methods = []
            for line in class_body.split("\n"):
                if "(" not in line:
                    continue
                line = line.strip()
                vis = (
                    "+"
                    if line.startswith("+")
                    else "-"
                    if line.startswith("-")
                    else "#"
                )
                clean = re.sub(r"^[+\-#]\s*", "", line)

                if "(" in clean:
                    name = clean.split("(")[0].strip()
                    params = clean.split("(")[1].split(")")[0] if "(" in clean else ""
                    ret = "void"
                    if ":" in clean:
                        ret = clean.split(":")[-1].strip()

                    methods.append(
                        {
                            "name": name,
                            "params": params,
                            "return": ret,
                            "visibility": vis,
                        }
                    )

            if class_name:
                entities.append(
                    {
                        "type": "class",
                        "name": class_name,
                        "attributes": attributes,
                        "methods": methods,
                    }
                )

        rel_pattern = r"(\w+)\s*(--|->|<-||<--|>\||<\|>)\s*(\w+)"
        for match in re.finditer(rel_pattern, text):
            src = match.group(1)
            tgt = match.group(3)
            arrow = match.group(2)

            rtype = "association"
            if arrow in ["--", "->"]:
                rtype = "dependency"
            elif arrow in ["<-", "<--"]:
                rtype = "dependency"
            elif arrow == ">|" or arrow == "<|":
                rtype = "composition" if arrow == ">|" else "aggregation"

            if src and tgt:
                relationships.append({"from": src, "to": tgt, "type": rtype})

        generated = []
        for ent in entities:
            name = ent.get("name", "Unknown")
            attrs = ent.get("attributes", [])
            generated.append(f"class {name}:")
            for attr in attrs[:3]:
                generated.append(f"    {attr.get('name')}: {attr.get('type')}")

        return DiagramExtractionResult(
            diagram_type=DiagramType.UML_CLASS,
            entities=entities,
            relationships=relationships,
            generated_code="\n".join(generated),
            confidence=0.8 if entities else 0.3,
        )


class UMLSequenceExtractor:
    @classmethod
    def extract(cls, text: str) -> DiagramExtractionResult:
        lifelines = []
        messages = []

        for line in text.split("\n"):
            if ":" in line and "->" not in line:
                name = line.split(":")[0].strip()
                if name and name not in [l.get("name") for l in lifelines]:
                    lifelines.append({"name": name, "type": "object"})

        message_pattern = r"(\w+)\s*(->>|-->|->)\s*(\w+):?\s*([^\n]+)"
        order = 0
        for match in re.finditer(message_pattern, text):
            msg_from = match.group(1).strip()
            msg_to = match.group(3).strip()
            content = match.group(4).strip() if match.group(4) else ""
            arrow = match.group(2)

            mtype = "sync" if "->>" in arrow else "async" if "-->" in arrow else "sync"

            if msg_from and msg_to:
                order += 1
                messages.append(
                    {
                        "from": msg_from,
                        "to": msg_to,
                        "message": content,
                        "type": mtype,
                        "order": order,
                    }
                )

        return DiagramExtractionResult(
            diagram_type=DiagramType.UML_SEQUENCE,
            entities=lifelines,
            relationships=messages,
            confidence=0.7 if messages else 0.3,
        )


class C4ContainerExtractor:
    @classmethod
    def extract(cls, text: str) -> DiagramExtractionResult:
        containers = []
        relationships = []

        for line in text.split("\n"):
            line = line.strip()
            if "[" in line and "]" in line:
                name = line.split("[")[1].split("]")[0].strip()
                tech = ""
                if "(" in line:
                    tech = line.split("(")[1].split(")")[0].strip()

                if name:
                    containers.append(
                        {"name": name, "technology": tech, "type": "container"}
                    )

        rel_patterns = [
            r"(\w+)\s*->\s*(\w+)",
            r"(\w+)\s*--\s*(\w+)",
        ]

        for pattern in rel_patterns:
            for match in re.finditer(pattern, text):
                src = match.group(1).strip()
                tgt = match.group(2).strip()
                if src and tgt and src != tgt:
                    relationships.append({"from": src, "to": tgt, "type": "uses"})

        code_parts = ["# C4 Container Architecture"]
        for c in containers:
            code_parts.append(f"# {c.get('name')} ({c.get('technology')})")

        return DiagramExtractionResult(
            diagram_type=DiagramType.C4_CONTAINER,
            entities=containers,
            relationships=relationships,
            generated_code="\n".join(code_parts),
            confidence=0.75 if containers else 0.3,
        )


class UMLComponentExtractor:
    @classmethod
    def extract(cls, text: str) -> DiagramExtractionResult:
        components = []
        for line in text.split("\n"):
            if "<<" in line and ">>" in line:
                name = line.split(">>")[1].strip().split("{")[0].strip()
                if name:
                    components.append({"name": name, "type": "component"})

        return DiagramExtractionResult(
            diagram_type=DiagramType.UML_COMPONENT,
            entities=components,
            relationships=[],
            confidence=0.7 if components else 0.3,
        )


class UMLDeploymentExtractor:
    @classmethod
    def extract(cls, text: str) -> DiagramExtractionResult:
        nodes = []
        for line in text.split("\n"):
            if "[node]" in line or "node" in line.lower():
                name = line.split("[")[0].strip() if "[" in line else line.strip()
                if name:
                    nodes.append({"name": name, "type": "node"})

        return DiagramExtractionResult(
            diagram_type=DiagramType.UML_DEPLOYMENT,
            entities=nodes,
            relationships=[],
            confidence=0.6 if nodes else 0.3,
        )


class UnifiedDiagramParser:
    EXTRACTORS = {
        DiagramType.UML_CLASS: UMLClassExtractor,
        DiagramType.UML_SEQUENCE: UMLSequenceExtractor,
        DiagramType.C4_CONTAINER: C4ContainerExtractor,
        DiagramType.UML_COMPONENT: UMLComponentExtractor,
        DiagramType.UML_DEPLOYMENT: UMLDeploymentExtractor,
    }

    def __init__(self):
        self._vision_parser = None

    def _get_vision_parser(self):
        if self._vision_parser is None:
            from documents.multimodal import get_multimodal_parser

            self._vision_parser = get_multimodal_parser()
        return self._vision_parser

    async def parse_image(
        self,
        image_source: Any,
        detect_type: bool = True,
    ) -> DiagramExtractionResult:
        parser = self._get_vision_parser()

        if hasattr(image_source, "read"):
            image_source = image_source.read()

        from PIL import Image

        if isinstance(image_source, bytes):
            image = Image.open(io.BytesIO(image_source))
        elif isinstance(image_source, str):
            image = Image.open(image_source)
        elif hasattr(image_source, "read"):
            image = Image.open(image_source)
        else:
            image = None

        if image is None:
            return DiagramExtractionResult(
                diagram_type=DiagramType.UNKNOWN, error="Could not load image"
            )

        text_result = await parser.parse(
            str(image), "Describe the diagram elements in detail."
        )
        text = text_result.text if hasattr(text_result, "text") else str(text_result)

        detected = DiagramType.UNKNOWN
        if detect_type:
            detected = DiagramTypeDetector.detect(image, text)

        extractor = self.EXTRACTORS.get(detected)
        if extractor:
            return extractor.extract(text)

        return DiagramExtractionResult(
            diagram_type=detected,
            entities=[],
            relationships=[],
            metadata={"raw_text": text[:500]},
            confidence=0.3,
        )

    async def parse_from_text(
        self,
        text: str,
        diagram_type: Optional[DiagramType] = None,
    ) -> DiagramExtractionResult:
        detected = diagram_type or DiagramTypeDetector.detect(None, text)
        extractor = self.EXTRACTORS.get(detected)

        if extractor:
            return extractor.extract(text)

        return DiagramExtractionResult(
            diagram_type=detected, error="No extractor available"
        )


def get_diagram_parser() -> UnifiedDiagramParser:
    return UnifiedDiagramParser()


def detect_diagram_type(image: Any, text: str) -> DiagramType:
    return DiagramTypeDetector.detect(image, text)
