"""
Specialized Diagram Format Parsers.

Parsers for:
- Draw.io XML (mxGraph)
- PlantUML
- BPMN 2.0
- OpenAPI/Swagger specs
"""

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from documents.diagram_parser import DiagramType, DiagramExtractionResult


@dataclass
class DrawIOElement:
    element_id: str
    type: str
    value: str
    style: Dict[str, Any] = field(default_factory=dict)
    geometry: Optional[Dict[str, Any]] = field(default_factory=dict)
    source_id: Optional[str] = None
    target_id: Optional[str] = None


@dataclass
class DrawIOParseResult:
    elements: List[DrawIOElement] = field(default_factory=list)
    connections: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DrawIOParser:
    MXGRAPH_NS = {"mx": "http://www.drawio.com/mxGraph"}

    def parse(self, xml_content: str) -> DrawIOParseResult:
        elements = []
        connections = []
        metadata = {}

        try:
            root = ET.fromstring(xml_content)

            if root.tag.endswith("mxfile"):
                metadata = {
                    "generator": root.get("generator", ""),
                    "modified": root.get("modified", ""),
                    "version": root.get("version", ""),
                }

                for diagram in root.findall(".//mxGraphModel"):
                    di = diagram.find("diagram")
                    if di is not None and di.text:
                        model_root = ET.fromstring(f"<root>{di.text}</root>")

                        for cell in model_root.findall(".//cell"):
                            el = self._parse_cell(cell)
                            if el:
                                if el.type in ("edge", "endArrow"):
                                    connections.append(
                                        {
                                            "source": el.source_id,
                                            "target": el.target_id,
                                            "value": el.value,
                                            "style": el.style,
                                        }
                                    )
                                else:
                                    elements.append(el)

        except ET.ParseError:
            pass

        return DrawIOParseResult(
            elements=elements,
            connections=connections,
            metadata=metadata,
        )

    def _parse_cell(self, cell: ET.Element) -> Optional[DrawIOElement]:
        cell_id = cell.get("id", "")
        cell_type = cell.get("type", "")
        value = cell.get("value", "")

        style_str = cell.get("style", "")
        style = self._parse_style(style_str)

        geometry = None
        geo_elem = cell.find("mxGeometry")
        if geo_elem is not None:
            geometry = {
                "x": float(geo_elem.get("x", 0)),
                "y": float(geo_elem.get("y", 0)),
                "width": float(geo_elem.get("width", 0)),
                "height": float(geo_elem.get("height", 0)),
            }

        source_id = None
        target_id = None
        if cell_type in ("edge", "endArrow"):
            source_id = cell.get("source", "")
            target_id = cell.get("target", "")

        return DrawIOElement(
            element_id=cell_id,
            type=cell_type,
            value=self._strip_xml_tags(value),
            style=style,
            geometry=geometry,
            source_id=source_id,
            target_id=target_id,
        )

    def _parse_style(self, style_str: str) -> Dict[str, Any]:
        style = {}
        for part in style_str.split(";"):
            if "=" in part:
                key, val = part.split("=", 1)
                style[key] = val
        return style

    def _strip_xml_tags(self, text: str) -> str:
        import re

        return re.sub(r"<[^>]+>", "", text).strip()


@dataclass
class PlantUMLParseResult:
    diagram_type: str
    participants: List[str] = field(default_factory=list)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[Dict[str, Any]] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PlantUMLParser:
    DIAGRAM_TYPES = [
        "sequence",
        "class",
        "use_case",
        "activity",
        "component",
        "state",
        "object",
        "deployment",
        "package",
    ]

    def parse(self, text: str) -> PlantUMLParseResult:
        text = text.strip()

        diagram_type = self._detect_type(text)
        result = PlantUMLParseResult(diagram_type=diagram_type)

        lines = text.split("\n")
        in_block = False
        block_type = ""
        current_entity = {}

        for line in lines:
            line = line.strip()

            if line.startswith("@startuml"):
                result.metadata["title"] = line.replace("@startuml", "").strip()
                continue
            if line.startswith("@enduml"):
                continue

            if line.startswith("=="):
                block_type = "participant"
                in_block = True
                continue

            if in_block and line == "":
                in_block = False
                if current_entity:
                    result.participants.append(current_entity.get("name", ""))
                    current_entity = {}
                continue

            if in_block:
                current_entity["name"] = line
                continue

            if diagram_type == "sequence":
                msg = self._parse_sequence_message(line)
                if msg:
                    result.messages.append(msg)
            elif diagram_type == "class":
                entity = self._parse_class_element(line)
                if entity:
                    result.entities.append(entity)
                    rel = self._parse_class_relationship(line)
                    if rel:
                        result.relationships.append(rel)
            else:
                msg = self._parse_generic_message(line)
                if msg:
                    result.messages.append(msg)

            note_match = self._parse_note(line)
            if note_match:
                result.notes.append(note_match)

        return result

    def _detect_type(self, text: str) -> str:
        lower = text.lower()
        if "participant" in lower or "actor" in lower or "->" in lower:
            if "participant" in lower or "actor" in lower:
                return "sequence"
            return "sequence"
        if "class" in lower and "interface" not in lower:
            return "class"
        if "usecase" in lower or "use case" in lower:
            return "use_case"
        if "state" in lower:
            return "state"
        if "component" in lower:
            return "component"
        if "package" in lower:
            return "package"
        if "activity" in lower:
            return "activity"
        return "sequence"

    def _parse_sequence_message(self, line: str) -> Optional[Dict[str, Any]]:
        if "->" not in line:
            return None

        parts = line.split("->")
        if len(parts) >= 2:
            source = parts[0].strip()
            rest = "->".join(parts[1:]).strip()

            target = rest
            message = ""
            if ":" in rest:
                target_parts = rest.split(":", 1)
                target = target_parts[0].strip()
                message = target_parts[1].strip() if len(target_parts) > 1 else ""

            return {"source": source, "target": target, "message": message}

        return None

    def _parse_class_element(self, line: str) -> Optional[Dict[str, Any]]:
        line = line.strip()

        if line.startswith("class ") or line.startswith("interface "):
            name = line.split()[-1].rstrip("{")
            return {"type": "class", "name": name}

        if line.startswith("enum "):
            name = line.split()[1].rstrip("{")
            return {"type": "enum", "name": name}

        return None

    def _parse_class_relationship(self, line: str) -> Optional[Dict[str, Any]]:
        line = line.strip()

        for rel_type in ["--", "..", "<|", "|>", "*--", "o--", "^--"]:
            if rel_type in line:
                parts = line.split(rel_type)
                if len(parts) == 2:
                    return {
                        "source": parts[0].strip(),
                        "target": parts[1].strip(),
                        "type": rel_type,
                    }

        return None

    def _parse_generic_message(self, line: str) -> Optional[Dict[str, Any]]:
        parts = line.split(":", 1)
        if len(parts) == 2:
            return {"from": parts[0].strip(), "message": parts[1].strip()}
        return None

    def _parse_note(self, line: str) -> Optional[Dict[str, Any]]:
        if line.startswith("note over"):
            parts = line.replace("note over", "").split(":")
            return {
                "type": "over",
                "target": parts[0].strip(),
                "text": parts[1].strip() if len(parts) > 1 else "",
            }

        if line.startswith("note left of"):
            parts = line.replace("note left of", "").split(":")
            return {
                "type": "left",
                "target": parts[0].strip(),
                "text": parts[1].strip() if len(parts) > 1 else "",
            }

        if line.startswith("note right of"):
            parts = line.replace("note right of", "").split(":")
            return {
                "type": "right",
                "target": parts[0].strip(),
                "text": parts[1].strip() if len(parts) > 1 else "",
            }

        return None


@dataclass
class OpenAPIParseResult:
    openapi_version: str
    info: Dict[str, Any] = field(default_factory=dict)
    servers: List[Dict[str, Any]] = field(default_factory=list)
    paths: List[Dict[str, Any]] = field(default_factory=list)
    components: Dict[str, Any] = field(default_factory=dict)
    security: List[Dict[str, Any]] = field(default_factory=list)


class OpenAPIParser:
    def parse(self, content: str) -> OpenAPIParseResult:
        data = json.loads(content) if isinstance(content, str) else content

        result = OpenAPIParseResult(
            openapi_version=data.get("openapi", ""),
            info=data.get("info", {}),
            servers=data.get("servers", []),
            components=data.get("components", {}),
            security=data.get("security", []),
        )

        for path, methods in data.get("paths", {}).items():
            for method, spec in methods.items():
                if method.lower() in [
                    "get",
                    "post",
                    "put",
                    "patch",
                    "delete",
                    "options",
                    "head",
                ]:
                    result.paths.append(
                        {
                            "path": path,
                            "method": method.upper(),
                            "summary": spec.get("summary", ""),
                            "description": spec.get("description", ""),
                            "operation_id": spec.get("operationId", ""),
                            "parameters": spec.get("parameters", []),
                            "request_body": spec.get("requestBody", {}),
                            "responses": spec.get("responses", {}),
                        }
                    )

        return result

    def extract_endpoints(self, content: str) -> List[Dict[str, Any]]:
        result = self.parse(content)
        return result.paths

    def extract_schemas(self, content: str) -> Dict[str, Any]:
        result = self.parse(content)
        return result.components.get("schemas", {})

    def extract_security(self, content: str) -> List[Dict[str, Any]]:
        result = self.parse(content)
        return result.security


def parse_drawio(xml_content: str) -> DrawIOParseResult:
    parser = DrawIOParser()
    return parser.parse(xml_content)


def parse_plantuml(text: str) -> PlantUMLParseResult:
    parser = PlantUMLParser()
    return parser.parse(text)


def parse_openapi(content: str) -> OpenAPIParseResult:
    parser = OpenAPIParser()
    return parser.parse(content)


def detect_format(content: str, filename: str = "") -> DiagramType:
    content = content.strip()

    if filename.endswith(".drawio") or filename.endswith(".dio"):
        return DiagramType.DRAW_IO

    if filename.endswith(".puml") or filename.endswith(".plantuml"):
        return DiagramType.PLANTUML

    if filename.endswith((".bpmn", ".xml")) and "bpmn" in content.lower():
        if _is_bpmn_content(content):
            return DiagramType.BPMN

    if (
        filename.endswith((".yaml", ".yml"))
        or "openapi" in content.lower()
        or "swagger" in content.lower()
    ):
        try:
            data = json.loads(content) if content.startswith("{") else {}
            if "openapi" in data or "swagger" in data:
                return DiagramType.OPENAPI
        except (json.JSONDecodeError, ValueError):
            pass

    if content.startswith("@startuml"):
        return DiagramType.PLANTUML

    if "<mxfile" in content or 'xmlns="http://www.drawio.com' in content:
        return DiagramType.DRAW_IO

    if _is_bpmn_content(content):
        return DiagramType.BPMN

    if content.startswith("{") or content.startswith("openapi:"):
        return DiagramType.OPENAPI

    return DiagramType.UNKNOWN


BPMN_NS = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
    "dc": "http://www.omg.org/spec/DD/20100524/DC",
    "di": "http://www.omg.org/spec/DD/20100524/DI",
}


@dataclass
class BPMNElement:
    element_id: str
    name: str
    element_type: str
    documentation: str = ""
    incoming: List[Optional[str]] = field(default_factory=list)
    outgoing: List[Optional[str]] = field(default_factory=list)
    extension_elements: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BPMNGateWay:
    element_id: str
    name: str
    gateway_type: str
    gateway_direction: str = "diverging"


@dataclass
class BPMNParseResult:
    processes: List[Dict[str, Any]] = field(default_factory=list)
    lanes: List[Dict[str, Any]] = field(default_factory=list)
    tasks: List[BPMNElement] = field(default_factory=list)
    events: List[BPMNElement] = field(default_factory=list)
    gateways: List[BPMNElement] = field(default_factory=list)
    flows: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BPMNParser:
    def parse(self, xml_content: str) -> BPMNParseResult:
        result = BPMNParseResult()

        try:
            root = ET.fromstring(xml_content)
            ns = self._extract_ns(root)
            self._register_ns(ns)

            result.metadata = {
                "target_namespace": root.get("targetNamespace", ""),
                "expression_language": root.get("expressionLanguage", ""),
                "type_language": root.get("typeLanguage", ""),
            }

            for process in root.findall(self._tag("process"), ns):
                result.processes.append(self._parse_process(process, ns))

            for data_object in root.findall(self._tag("dataObject"), ns):
                result.artifacts.append(
                    {
                        "id": data_object.get("id", ""),
                        "name": data_object.get("name", ""),
                        "type": "dataObject",
                    }
                )

            for data_store in root.findall(self._tag("dataStore"), ns):
                result.artifacts.append(
                    {
                        "id": data_store.get("id", ""),
                        "name": data_store.get("name", ""),
                        "type": "dataStore",
                    }
                )

        except ET.ParseError:
            pass

        return result

    def _extract_ns(self, root: ET.Element) -> Dict[str, str]:
        ns = {}
        for key, val in root.attrib.items():
            if key.startswith("{"):
                uri = key[1:].split("}")[0]
                prefix = key.split("}")[1].replace("xmlns", "")
                if prefix:
                    ns[prefix] = uri
                elif "bpmn" in uri.lower():
                    ns["bpmn"] = uri
        return ns

    def _register_ns(self, ns: Dict[str, str]):
        for prefix, uri in ns.items():
            ET.register_namespace(prefix, uri)

    def _tag(self, tag: str, prefix: str = "bpmn") -> str:
        return f"{{{BPMN_NS.get(prefix, f'http://www.omg.org/spec/BPMN/20100524/MODEL')}}}{tag}"

    def _parse_process(self, process: ET.Element, ns: Dict[str, str]) -> Dict[str, Any]:
        result = BPMNParseResult()

        process_id = process.get("id", "")
        process_name = process.get("name", "")
        is_executable = process.get("isExecutable", "false") == "true"

        result.metadata = {
            "id": process_id,
            "name": process_name,
            "is_executable": is_executable,
        }

        for lane_set in process.findall(self._tag("laneSet"), ns):
            for lane in lane_set.findall(self._tag("lane"), ns):
                result.lanes.append(
                    {
                        "id": lane.get("id", ""),
                        "name": lane.get("name", ""),
                        "flow_node_refs": [
                            ref.text
                            for ref in lane.findall(self._tag("flowNodeRef"), ns)
                        ],
                    }
                )

        for elem in process:
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

            if tag == "startEvent":
                result.events.append(self._parse_event(elem, "start", ns))
            elif tag == "endEvent":
                result.events.append(self._parse_event(elem, "end", ns))
            elif tag == "intermediateThrowEvent":
                result.events.append(self._parse_event(elem, "intermediate_throw", ns))
            elif tag == "intermediateCatchEvent":
                result.events.append(self._parse_event(elem, "intermediate_catch", ns))
            elif tag == "task":
                result.tasks.append(self._parse_task(elem, ns))
            elif tag == "userTask":
                result.tasks.append(self._parse_task(elem, ns, task_type="user"))
            elif tag == "serviceTask":
                result.tasks.append(self._parse_task(elem, ns, task_type="service"))
            elif tag == "scriptTask":
                result.tasks.append(self._parse_task(elem, ns, task_type="script"))
            elif tag == "manualTask":
                result.tasks.append(self._parse_task(elem, ns, task_type="manual"))
            elif tag == "sendTask":
                result.tasks.append(self._parse_task(elem, ns, task_type="send"))
            elif tag == "receiveTask":
                result.tasks.append(self._parse_task(elem, ns, task_type="receive"))
            elif tag == "exclusiveGateway":
                result.gateways.append(self._parse_gateway(elem, "exclusive", ns))
            elif tag == "inclusiveGateway":
                result.gateways.append(self._parse_gateway(elem, "inclusive", ns))
            elif tag == "parallelGateway":
                result.gateways.append(self._parse_gateway(elem, "parallel", ns))
            elif tag == "complexGateway":
                result.gateways.append(self._parse_gateway(elem, "complex", ns))
            elif tag == "eventGateway":
                result.gateways.append(self._parse_gateway(elem, "event", ns))
            elif tag in ("sequenceFlow", "messageFlow"):
                result.flows.append(self._parse_flow(elem, ns))

        return result

    def _parse_event(
        self, elem: ET.Element, trigger_type: str, ns: Dict[str, str]
    ) -> BPMNElement:
        docs = elem.find(self._tag("documentation"), ns)
        documentation = docs.text if docs is not None else ""

        incoming = [ref.text for ref in elem.findall(self._tag("incoming"), ns)]
        outgoing = [ref.text for ref in elem.findall(self._tag("outgoing"), ns)]

        return BPMNElement(
            element_id=elem.get("id", ""),
            name=elem.get("name", ""),
            element_type=f"event_{trigger_type}",
            documentation=documentation,
            incoming=incoming,
            outgoing=outgoing,
        )

    def _parse_task(
        self, elem: ET.Element, ns: Dict[str, str], task_type: str = "task"
    ) -> BPMNElement:
        docs = elem.find(self._tag("documentation"), ns)
        documentation = docs.text if docs is not None else ""

        incoming = [ref.text for ref in elem.findall(self._tag("incoming"), ns)]
        outgoing = [ref.text for ref in elem.findall(self._tag("outgoing"), ns)]

        io_spec = elem.find(self._tag("ioSpecification"), ns)
        extension_elements = {}
        if io_spec is not None:
            extension_elements["io_specification"] = True

        return BPMNElement(
            element_id=elem.get("id", ""),
            name=elem.get("name", ""),
            element_type=task_type,
            documentation=documentation,
            incoming=incoming,
            outgoing=outgoing,
            extension_elements=extension_elements,
        )

    def _parse_gateway(
        self, elem: ET.Element, gateway_type: str, ns: Dict[str, str]
    ) -> BPMNElement:
        docs = elem.find(self._tag("documentation"), ns)
        documentation = docs.text if docs is not None else ""

        incoming = [ref.text for ref in elem.findall(self._tag("incoming"), ns)]
        outgoing = [ref.text for ref in elem.findall(self._tag("outgoing"), ns)]

        gateway_direction = elem.get("gatewayDirection", "diverging")

        return BPMNElement(
            element_id=elem.get("id", ""),
            name=elem.get("name", ""),
            element_type=f"gateway_{gateway_type}",
            documentation=documentation,
            incoming=incoming,
            outgoing=outgoing,
        )

    def _parse_flow(self, elem: ET.Element, ns: Dict[str, str]) -> Dict[str, Any]:
        source_ref = elem.get("sourceRef", "")
        target_ref = elem.get("targetRef", "")
        condition = elem.get("conditionExpression", "")

        return {
            "id": elem.get("id", ""),
            "name": elem.get("name", ""),
            "type": elem.tag.split("}")[-1],
            "source": source_ref,
            "target": target_ref,
            "condition": condition,
        }


def parse_bpmn(xml_content: str) -> BPMNParseResult:
    parser = BPMNParser()
    return parser.parse(xml_content)
