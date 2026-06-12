"""
Unified Diagram Intermediate Representation (DiagramIR).

Provides:
- DiagramIR: Unified representation for all diagram types
- DiagramNode: Typed nodes (service, database, api, user, component)
- DiagramEdge: Typed relationships with protocol support
- DiagramIRBuilder: Build DiagramIR from text or images

Supports: PlantUML, Mermaid, Draw.io, OpenAPI, BPMN, and images via VLM.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DiagramNodeType(str, Enum):
    """Semantic types for diagram nodes."""

    SERVICE = "service"  # Microservice, lambda, function
    DATABASE = "database"  # SQL, NoSQL, cache
    API = "api"  # REST, GraphQL endpoint
    USER = "user"  # Actor, person, system
    COMPONENT = "component"  # Generic component
    CONTAINER = "container"  # Docker, K8s pod
    QUEUE = "queue"  # Message queue
    STORAGE = "storage"  # S3, blob storage
    GATEWAY = "gateway"  # API gateway, load balancer
    EXTERNAL = "external"  # External service
    UNKNOWN = "unknown"


class DiagramEdgeType(str, Enum):
    """Semantic types for diagram edges."""

    CALLS = "calls"  # HTTP, RPC
    READS = "reads"  # Data read
    WRITES = "writes"  # Data write
    PUBLISHES = "publishes"  # Event publish
    SUBSCRIBES = "subscribes"  # Event subscribe
    CONTAINS = "contains"  # Containment
    DEPLOYS = "deploys"  # Deployment
    AUTHENTICATES = "authenticates"  # Auth flow
    UNKNOWN = "unknown"


class DiagramFormat(str, Enum):
    """Supported diagram input formats."""

    PLANTUML = "plantuml"
    MERMAID = "mermaid"
    DRAW_IO = "drawio"
    OPENAPI = "openapi"
    BPMN = "bpmn"
    IMAGE = "image"  # VLM-extracted
    UNKNOWN = "unknown"


@dataclass
class DiagramNode:
    """Represents a single node in a diagram."""

    id: str
    type: DiagramNodeType
    name: str
    label: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "label": self.label,
            "properties": self.properties,
        }


@dataclass
class DiagramEdge:
    """Represents a relationship between two nodes."""

    id: str
    source: str  # DiagramNode.id
    target: str  # DiagramNode.id
    type: DiagramEdgeType
    label: str = ""
    protocol: str = ""  # http, grpc, mqtt, jdbc
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "type": self.type.value,
            "label": self.label,
            "protocol": self.protocol,
            "properties": self.properties,
        }


@dataclass
class DiagramIR:
    """Unified Intermediate Representation for all diagram types.

    NOTE: Serialization via to_dict() does not preserve node insertion order.
    Python dicts maintain insertion order (3.7+), but consumers should not
    rely on node ordering being preserved across serialization boundaries
    (e.g., JSON parsing in JavaScript may not guarantee order). If strict
    ordering is required, add an explicit `order` field to DiagramNode.
    """

    id: str
    diagram_type: str  # From DiagramType enum
    title: str = ""
    nodes: List[DiagramNode] = field(default_factory=list)
    edges: List[DiagramEdge] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None  # VLM-generated vector
    raw_content: str = ""
    source_format: DiagramFormat = DiagramFormat.UNKNOWN
    extraction_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "diagram_type": self.diagram_type,
            "title": self.title,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "metadata": self.metadata,
            "extraction_confidence": self.extraction_confidence,
            "source_format": self.source_format.value,
        }

    def get_node(self, node_id: str) -> Optional[DiagramNode]:
        """Get node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def validate_edge(self, edge: DiagramEdge) -> bool:
        """Validate that edge source and target node IDs exist.

        Returns True if both source and target reference existing nodes.
        Logs a warning and returns False if either reference is missing.
        """
        node_ids = {n.id for n in self.nodes}
        if edge.source not in node_ids:
            logger.warning(
                "Edge '%s' references non-existent source node '%s'",
                edge.id,
                edge.source,
            )
            return False
        if edge.target not in node_ids:
            logger.warning(
                "Edge '%s' references non-existent target node '%s'",
                edge.id,
                edge.target,
            )
            return False
        return True

    def add_edge(self, edge: DiagramEdge) -> bool:
        """Add an edge after validating source and target references.

        Returns True if the edge was added, False if validation failed.
        """
        if not self.validate_edge(edge):
            return False
        self.edges.append(edge)
        return True

    def get_neighbors(self, node_id: str) -> List[DiagramNode]:
        """Get all nodes connected to given node."""
        neighbor_ids = set()
        for edge in self.edges:
            if edge.source == node_id:
                neighbor_ids.add(edge.target)
            elif edge.target == node_id:
                neighbor_ids.add(edge.source)
        return [n for n in self.nodes if n.id in neighbor_ids]


class DiagramIRBuilder:
    """Build unified DiagramIR from any source."""

    def __init__(self):
        self._node_factory = _NodeFactory()
        self._edge_factory = _EdgeFactory()
        self._parsers = _DiagramParsers()

    def _generate_id(self, content: str, prefix: str = "diag") -> str:
        """Generate deterministic ID from content."""
        hash_str = hashlib.sha256(content.encode()).hexdigest()[:12]
        return f"{prefix}_{hash_str}"

    async def from_text(
        self,
        content: str,
        format: Optional[DiagramFormat] = None,
        source: Optional[str] = None,
    ) -> DiagramIR:
        """Build DiagramIR from text content.

        Args:
            content: Raw diagram text (PlantUML, Mermaid, etc.)
            format: Known format, or auto-detect if None
            source: Optional source identifier (URL, repo, etc.)

        Returns:
            Parsed DiagramIR with nodes and edges
        """
        content = content.strip()
        if not content:
            return DiagramIR(
                id=self._generate_id("empty"),
                diagram_type="unknown",
            )

        # Auto-detect format
        if format is None or format == DiagramFormat.UNKNOWN:
            format = self._detect_format(content)

        diagram_id = self._generate_id(content)
        title = source or f"Diagram {diagram_id[-6:]}"

        # Parse using appropriate parser
        if format == DiagramFormat.PLANTUML:
            nodes, edges, diagram_type = self._parsers.parse_plantuml(content)
        elif format == DiagramFormat.MERMAID:
            nodes, edges, diagram_type = self._parsers.parse_mermaid(content)
        elif format == DiagramFormat.DRAW_IO:
            nodes, edges, diagram_type = self._parsers.parse_drawio(content)
        elif format == DiagramFormat.OPENAPI:
            nodes, edges, diagram_type = self._parsers.parse_openapi(content)
        elif format == DiagramFormat.BPMN:
            nodes, edges, diagram_type = self._parsers.parse_bpmn(content)
        else:
            nodes, edges, diagram_type = [], [], "unknown"

        # Create DiagramIR
        ir = DiagramIR(
            id=diagram_id,
            diagram_type=diagram_type,
            title=title,
            nodes=nodes,
            edges=edges,
            raw_content=content,
            source_format=format,
            extraction_confidence=0.9 if nodes else 0.0,
            metadata={"source": source} if source else {},
        )

        return ir

    async def from_image(
        self,
        image_url: str,
        source: Optional[str] = None,
    ) -> DiagramIR:
        """Build DiagramIR from image URL via VLM.

        Args:
            image_url: URL to diagram image
            source: Optional source identifier

        Returns:
            VLM-extracted DiagramIR
        """
        try:
            from multimodal.vlm import QwenVLProvider

            client = QwenVLProvider()
            if not client.api_key:
                logger.warning("VLM not available for diagram extraction")
                return DiagramIR(
                    id=self._generate_id(image_url),
                    diagram_type="unknown",
                )

            result = await client.analyze_image(
                image_url, "Extract all entities and relationships from this architecture diagram."
            )
            result_text = (
                result.get("output", {}).get("text", "") if isinstance(result, dict) else ""
            )
            if not result_text:
                return DiagramIR(
                    id=self._generate_id(image_url),
                    diagram_type="unknown",
                )

            # Parse VLM response into DiagramIR
            return await self._parse_vlm_response(result_text, image_url, source)

        except Exception as e:
            logger.warning("VLM diagram extraction failed: %s", e)
            return DiagramIR(
                id=self._generate_id(image_url),
                diagram_type="unknown",
            )

    async def enrich(
        self,
        ir: DiagramIR,
        vlm_model: Optional[str] = None,
    ) -> DiagramIR:
        """Enrich DiagramIR with VLM embeddings and semantic typing.

        Args:
            ir: Existing DiagramIR to enrich
            vlm_model: Optional VLM model override

        Returns:
            Enriched DiagramIR with embeddings
        """
        if not ir.nodes:
            return ir

        try:
            from llm.router import get_llm_router

            router = get_llm_router()

            diagram_text = self._ir_to_text(ir)
            embedding = await router.embed_batch([diagram_text])
            if embedding and len(embedding) > 0:
                ir.embedding = embedding[0]

            # Infer node types via LLM
            ir.nodes = await self._infer_node_types(ir.nodes)
            ir.edges = await self._infer_edge_types(ir.edges)

            # Update confidence
            ir.extraction_confidence = min(1.0, ir.extraction_confidence + 0.1)

        except Exception as e:
            logger.warning("DiagramIR enrichment failed: %s", e)

        return ir

    def _detect_format(self, content: str) -> DiagramFormat:
        """Auto-detect diagram format from content."""
        content_lower = content.lower().strip()

        # PlantUML markers
        if "@startuml" in content_lower or "@enduml" in content_lower:
            if any(kw in content_lower for kw in ["participant", "actor", "->"]):
                return DiagramFormat.PLANTUML

        # Mermaid markers
        if content_lower.startswith("classdiagram") or content_lower.startswith("sequencediagram"):
            return DiagramFormat.MERMAID
        if content_lower.startswith("flowchart") or content_lower.startswith("graph"):
            return DiagramFormat.MERMAID
        if "graph TD" in content_lower or "graph LR" in content_lower:
            return DiagramFormat.MERMAID

        # Draw.io XML
        if "<mxfile" in content_lower or "<diagram" in content_lower:
            return DiagramFormat.DRAW_IO

        # OpenAPI
        if '"openapi"' in content_lower or "openapi:" in content_lower:
            return DiagramFormat.OPENAPI

        # BPMN
        if "bpmn:definitions" in content_lower or "bpmn:process" in content_lower:
            return DiagramFormat.BPMN

        return DiagramFormat.UNKNOWN

    def _ir_to_text(self, ir: DiagramIR) -> str:
        """Convert DiagramIR to text for embedding."""
        lines = [f"Diagram: {ir.title} ({ir.diagram_type})"]
        lines.append(f"Nodes: {len(ir.nodes)}")
        for node in ir.nodes:
            lines.append(f"  - {node.name} ({node.type.value})")
        lines.append(f"Relationships: {len(ir.edges)}")
        for edge in ir.edges:
            lines.append(f"  - {edge.source} --[{edge.type.value}]--> {edge.target}")
        return "\n".join(lines)

    async def _parse_vlm_response(
        self,
        response: str,
        image_url: str,
        source: Optional[str],
    ) -> DiagramIR:
        """Parse VLM JSON response into DiagramIR."""
        import json

        diagram_id = self._generate_id(image_url)

        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re

            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    data = {}
            else:
                data = {}

        nodes = []
        edges = []

        # Parse entities
        for i, ent in enumerate(data.get("entities", [])):
            node = DiagramNode(
                id=f"node_{i}",
                type=self._node_factory.infer_type(ent.get("type", "")),
                name=ent.get("name", ""),
                label=ent.get("label", ""),
                properties=ent,
            )
            nodes.append(node)

        # Parse relationships
        for i, rel in enumerate(data.get("relationships", [])):
            edge = DiagramEdge(
                id=f"edge_{i}",
                source=rel.get("from", rel.get("source", "")),
                target=rel.get("to", rel.get("target", "")),
                type=self._edge_factory.infer_type(rel.get("type", "")),
                label=rel.get("label", ""),
                protocol=rel.get("protocol", ""),
            )
            edges.append(edge)

        return DiagramIR(
            id=diagram_id,
            diagram_type="vlm_extracted",
            title=source or f"VLM {diagram_id[-6:]}",
            nodes=nodes,
            edges=edges,
            raw_content=response,
            source_format=DiagramFormat.IMAGE,
            extraction_confidence=0.85 if nodes else 0.0,
            metadata={"image_url": image_url},
        )

    async def _infer_node_types(
        self,
        nodes: List[DiagramNode],
    ) -> List[DiagramNode]:
        """Infer node types via LLM."""
        if not nodes:
            return nodes

        try:
            from llm.router import get_llm_router

            router = get_llm_router()
            names = [n.name for n in nodes]
            prompt = f"""For each name, infer its type from: service, database, api, user, component, queue, storage, gateway, external.
Input: {", ".join(names)}
Output: JSON array of {{name, type}}."""

            result = await router.chat(prompt)
            if result and result.text:
                import json

                try:
                    types = json.loads(result.text)
                    for t in types:
                        for node in nodes:
                            if node.name == t.get("name"):
                                node.type = self._node_factory.infer_type(t.get("type", ""))
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            logger.debug("Node type inference failed: %s", e)

        return nodes

    async def _infer_edge_types(
        self,
        edges: List[DiagramEdge],
    ) -> List[DiagramEdge]:
        """Infer edge types and protocols via LLM."""
        if not edges:
            return edges

        try:
            from llm.router import get_llm_router

            router = get_llm_router()
            pairs = [(e.source, e.target) for e in edges]
            prompt = f"""For each pair (source -> target), infer relationship type from: calls, reads, writes, publishes, subscribes, contains, deploys.
Also identify protocol if apparent: http, grpc, mqtt, jdbc, websocket.
Input: {pairs}
Output: JSON array of {{source, target, type, protocol}}."""

            result = await router.chat(prompt)
            if result and result.text:
                import json

                try:
                    rels = json.loads(result.text)
                    for r in rels:
                        for edge in edges:
                            if edge.source == r.get("source") and edge.target == r.get("target"):
                                edge.type = self._edge_factory.infer_type(r.get("type", ""))
                                edge.protocol = r.get("protocol", "")
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            logger.debug("Edge type inference failed: %s", e)

        return edges


class _NodeFactory:
    """Factory for creating typed DiagramNodes."""

    TYPE_KEYWORDS = {
        DiagramNodeType.SERVICE: ["service", "microservice", "lambda", "function", "worker"],
        DiagramNodeType.DATABASE: ["db", "database", "sql", "nosql", "redis", "cache"],
        DiagramNodeType.API: ["api", "endpoint", "rest", "graphql"],
        DiagramNodeType.USER: ["user", "actor", "person", "admin", "customer"],
        DiagramNodeType.COMPONENT: ["component", "module", "package"],
        DiagramNodeType.CONTAINER: ["container", "pod", "docker", "kubernetes"],
        DiagramNodeType.QUEUE: ["queue", "kafka", "rabbitmq", "sqs", "pubsub"],
        DiagramNodeType.STORAGE: ["s3", "storage", "blob", "bucket"],
        DiagramNodeType.GATEWAY: ["gateway", "load balancer", "nginx", "api gateway"],
        DiagramNodeType.EXTERNAL: ["external", "3rd party", "third-party"],
    }

    def infer_type(self, type_str: str) -> DiagramNodeType:
        """Infer node type from string."""
        if not type_str:
            return DiagramNodeType.UNKNOWN

        type_lower = type_str.lower()
        for ntype, keywords in self.TYPE_KEYWORDS.items():
            if any(kw in type_lower for kw in keywords):
                return ntype

        # Try direct match
        for ntype in DiagramNodeType:
            if ntype.value == type_lower:
                return ntype

        return DiagramNodeType.UNKNOWN


class _EdgeFactory:
    """Factory for creating typed DiagramEdges."""

    TYPE_KEYWORDS = {
        DiagramEdgeType.CALLS: ["call", "http", "rpc", "request", "invoke"],
        DiagramEdgeType.READS: ["read", "query", "get", "select"],
        DiagramEdgeType.WRITES: ["write", "insert", "update", "post", "put"],
        DiagramEdgeType.PUBLISHES: ["publish", "event", "emit", "produce"],
        DiagramEdgeType.SUBSCRIBES: ["subscribe", "consume", "listen"],
        DiagramEdgeType.CONTAINS: ["contain", "include", "has"],
        DiagramEdgeType.DEPLOYS: ["deploy", "host", "run"],
        DiagramEdgeType.AUTHENTICATES: ["auth", "login", "jwt", "oauth"],
    }

    def infer_type(self, type_str: str) -> DiagramEdgeType:
        """Infer edge type from string."""
        if not type_str:
            return DiagramEdgeType.UNKNOWN

        type_lower = type_str.lower()
        for etype, keywords in self.TYPE_KEYWORDS.items():
            if any(kw in type_lower for kw in keywords):
                return etype

        # Try direct match
        for etype in DiagramEdgeType:
            if etype.value == type_lower:
                return etype

        return DiagramEdgeType.UNKNOWN


class _DiagramParsers:
    """Parsers for each supported format."""

    def parse_plantuml(self, content: str) -> tuple:
        """Parse PlantUML text into nodes and edges."""
        from documents.diagram_formats import PlantUMLParser

        parser = PlantUMLParser()
        result = parser.parse(content)

        nodes = []
        edges = []

        # Convert participants to nodes
        for i, name in enumerate(result.participants):
            nodes.append(
                DiagramNode(
                    id=f"node_{i}",
                    type=DiagramNodeType.UNKNOWN,
                    name=name,
                )
            )

        # Convert messages to edges
        for i, msg in enumerate(result.messages):
            source = self._find_node_by_name(nodes, msg.get("source", ""))
            target = self._find_node_by_name(nodes, msg.get("target", ""))
            if source and target:
                edges.append(
                    DiagramEdge(
                        id=f"edge_{i}",
                        source=source.id,
                        target=target.id,
                        type=DiagramEdgeType.CALLS,
                        label=msg.get("message", ""),
                    )
                )

        # Convert entities
        for i, ent in enumerate(result.entities):
            name = ent.get("name", "")
            if not self._find_node_by_name(nodes, name):
                nodes.append(
                    DiagramNode(
                        id=f"node_{len(nodes) + i}",
                        type=DiagramNodeType.COMPONENT,
                        name=name,
                    )
                )

        # Convert relationships
        for i, rel in enumerate(result.relationships):
            source = self._find_node_by_name(nodes, rel.get("source", ""))
            target = self._find_node_by_name(nodes, rel.get("target", ""))
            if source and target:
                edges.append(
                    DiagramEdge(
                        id=f"edge_{len(edges) + i}",
                        source=source.id,
                        target=target.id,
                        type=DiagramEdgeType.CALLS,
                        label=rel.get("type", ""),
                    )
                )

        return nodes, edges, result.diagram_type or "plantuml"

    def parse_mermaid(self, content: str) -> tuple:
        """Parse Mermaid text into nodes and edges."""
        from documents.diagram_formats import MermaidParser

        parser = MermaidParser()
        result = parser.parse(content)

        nodes = []
        edges = []

        # Convert entities to nodes
        for i, ent in enumerate(result.entities):
            name = ent.get("name", "")
            nodes.append(
                DiagramNode(
                    id=f"node_{i}",
                    type=DiagramNodeType.UNKNOWN,
                    name=name,
                )
            )

        # Convert relationships to edges
        for i, rel in enumerate(result.relationships):
            source = self._find_node_by_name(nodes, rel.get("from", rel.get("source", "")))
            target = self._find_node_by_name(nodes, rel.get("to", rel.get("target", "")))
            if source and target:
                edges.append(
                    DiagramEdge(
                        id=f"edge_{i}",
                        source=source.id,
                        target=target.id,
                        type=DiagramEdgeType.CALLS,
                        label=rel.get("type", ""),
                    )
                )

        return nodes, edges, result.diagram_type or "mermaid"

    def parse_drawio(self, content: str) -> tuple:
        """Parse Draw.io XML into nodes and edges."""
        from documents.diagram_formats import DrawIOParser

        parser = DrawIOParser()
        result = parser.parse(content)

        nodes = []
        edges = []

        # Convert elements to nodes
        for i, el in enumerate(result.elements):
            nodes.append(
                DiagramNode(
                    id=f"node_{i}",
                    type=DiagramNodeType.COMPONENT,
                    name=el.value or el.element_id,
                )
            )

        # Convert connections to edges
        for i, conn in enumerate(result.connections):
            edges.append(
                DiagramEdge(
                    id=f"edge_{i}",
                    source=conn.get("source", ""),
                    target=conn.get("target", ""),
                    type=DiagramEdgeType.CALLS,
                    label=conn.get("value", ""),
                )
            )

        return nodes, edges, "drawio"

    def parse_openapi(self, content: str) -> tuple:
        """Parse OpenAPI spec into nodes and edges."""
        from documents.diagram_formats import OpenAPIParser

        parser = OpenAPIParser()
        result = parser.parse(content)

        nodes = []
        edges = []

        # Add server nodes
        for i, server in enumerate(result.servers):
            nodes.append(
                DiagramNode(
                    id=f"node_{i}",
                    type=DiagramNodeType.API,
                    name=server.get("url", ""),
                )
            )

        # Convert paths to edges
        base_idx = len(nodes)
        for i, path in enumerate(result.paths):
            path_item = path.get("path", "")
            methods = [m for m in path.get("methods", [])]
            for method in methods:
                nodes.append(
                    DiagramNode(
                        id=f"node_{base_idx + i}",
                        type=DiagramNodeType.API,
                        name=f"{method.upper()} {path_item}",
                    )
                )

        return nodes, edges, "openapi"

    def parse_bpmn(self, content: str) -> tuple:
        """Parse BPMN XML into nodes and edges."""
        from documents.diagram_formats import BPMNParser

        parser = BPMNParser()
        result = parser.parse(content)

        nodes = []
        edges = []

        # Convert processes to nodes
        for i, proc in enumerate(result.processes):
            nodes.append(
                DiagramNode(
                    id=f"node_{i}",
                    type=DiagramNodeType.SERVICE,
                    name=proc.get("name", proc.get("id", "")),
                )
            )

        # Convert flows to edges
        for i, flow in enumerate(result.flows):
            edges.append(
                DiagramEdge(
                    id=f"edge_{i}",
                    source=flow.get("source", ""),
                    target=flow.get("target", ""),
                    type=DiagramEdgeType.CALLS,
                    label=flow.get("name", ""),
                )
            )

        return nodes, edges, "bpmn"

    def _find_node_by_name(
        self,
        nodes: List[DiagramNode],
        name: str,
    ) -> Optional[DiagramNode]:
        """Find node by name (case-insensitive)."""
        name_lower = name.lower()
        for node in nodes:
            if node.name.lower() == name_lower:
                return node
        return None


# Module-level builder instance
_diagram_ir_builder: Optional[DiagramIRBuilder] = None


def get_diagram_ir_builder() -> DiagramIRBuilder:
    """Get the global DiagramIRBuilder instance."""
    global _diagram_ir_builder
    if _diagram_ir_builder is None:
        _diagram_ir_builder = DiagramIRBuilder()
    return _diagram_ir_builder
