import pytest
from multimodal.diagram_ir import (
    DiagramEdge,
    DiagramEdgeType,
    DiagramFormat,
    DiagramIR,
    DiagramIRBuilder,
    DiagramNode,
    DiagramNodeType,
)


class TestDiagramNode:
    def test_node_creation(self):
        node = DiagramNode(id="n1", type=DiagramNodeType.SERVICE, name="user-service")
        assert node.id == "n1"
        assert node.type == DiagramNodeType.SERVICE
        assert node.name == "user-service"

    def test_node_to_dict(self):
        node = DiagramNode(
            id="n1",
            type=DiagramNodeType.DATABASE,
            name="postgres",
            label="PostgreSQL DB",
        )
        d = node.to_dict()
        assert d["id"] == "n1"
        assert d["type"] == "database"
        assert d["name"] == "postgres"
        assert d["label"] == "PostgreSQL DB"

    def test_node_type_inference(self):
        from multimodal.diagram_ir import _NodeFactory

        factory = _NodeFactory()
        assert factory.infer_type("api") == DiagramNodeType.API
        assert factory.infer_type("SERVICE") == DiagramNodeType.SERVICE
        assert factory.infer_type("lambda function") == DiagramNodeType.SERVICE
        assert factory.infer_type("redis cache") == DiagramNodeType.DATABASE
        assert factory.infer_type("unknown") == DiagramNodeType.UNKNOWN


class TestDiagramEdge:
    def test_edge_creation(self):
        edge = DiagramEdge(
            id="e1",
            source="n1",
            target="n2",
            type=DiagramEdgeType.CALLS,
            label="GET /users",
        )
        assert edge.id == "e1"
        assert edge.source == "n1"
        assert edge.target == "n2"
        assert edge.type == DiagramEdgeType.CALLS

    def test_edge_to_dict(self):
        edge = DiagramEdge(
            id="e1",
            source="n1",
            target="n2",
            type=DiagramEdgeType.PUBLISHES,
            protocol="http",
        )
        d = edge.to_dict()
        assert d["id"] == "e1"
        assert d["source"] == "n1"
        assert d["target"] == "n2"
        assert d["type"] == "publishes"
        assert d["protocol"] == "http"

    def test_edge_type_inference(self):
        from multimodal.diagram_ir import _EdgeFactory

        factory = _EdgeFactory()
        assert factory.infer_type("calls") == DiagramEdgeType.CALLS
        assert factory.infer_type("http request") == DiagramEdgeType.CALLS
        assert factory.infer_type("publishes") == DiagramEdgeType.PUBLISHES
        assert factory.infer_type("event emit") == DiagramEdgeType.PUBLISHES


class TestDiagramIR:
    def test_diagram_ir_creation(self):
        ir = DiagramIR(id="d1", diagram_type="sequence", title="User Flow")
        assert ir.id == "d1"
        assert ir.diagram_type == "sequence"
        assert ir.title == "User Flow"
        assert len(ir.nodes) == 0
        assert len(ir.edges) == 0

    def test_diagram_ir_with_nodes(self):
        ir = DiagramIR(id="d1", diagram_type="sequence", title="User Flow")
        ir.nodes = [
            DiagramNode(id="n1", type=DiagramNodeType.SERVICE, name="svc1"),
            DiagramNode(id="n2", type=DiagramNodeType.DATABASE, name="db1"),
        ]
        ir.edges = [
            DiagramEdge(id="e1", source="n1", target="n2", type=DiagramEdgeType.CALLS),
        ]
        assert len(ir.nodes) == 2
        assert len(ir.edges) == 1

    def test_get_node(self):
        ir = DiagramIR(id="d1", diagram_type="class")
        node = DiagramNode(id="n1", type=DiagramNodeType.API, name="user-api")
        ir.nodes.append(node)

        found = ir.get_node("n1")
        assert found is not None
        assert found.name == "user-api"

        not_found = ir.get_node("nonexistent")
        assert not_found is None

    def test_get_neighbors(self):
        ir = DiagramIR(id="d1", diagram_type="class")
        ir.nodes = [
            DiagramNode(id="n1", type=DiagramNodeType.SERVICE, name="svc1"),
            DiagramNode(id="n2", type=DiagramNodeType.SERVICE, name="svc2"),
            DiagramNode(id="n3", type=DiagramNodeType.DATABASE, name="db1"),
        ]
        ir.edges = [
            DiagramEdge(id="e1", source="n1", target="n2", type=DiagramEdgeType.CALLS),
            DiagramEdge(id="e2", source="n2", target="n3", type=DiagramEdgeType.CALLS),
        ]

        neighbors = ir.get_neighbors("n2")
        neighbor_ids = {n.id for n in neighbors}
        assert "n1" in neighbor_ids
        assert "n3" in neighbor_ids

    def test_to_dict(self):
        ir = DiagramIR(
            id="d1",
            diagram_type="sequence",
            title="Test",
            nodes=[
                DiagramNode(id="n1", type=DiagramNodeType.SERVICE, name="svc1"),
            ],
            edges=[
                DiagramEdge(id="e1", source="n1", target="n2", type=DiagramEdgeType.CALLS),
            ],
            extraction_confidence=0.85,
        )
        d = ir.to_dict()
        assert d["id"] == "d1"
        assert d["diagram_type"] == "sequence"
        assert len(d["nodes"]) == 1
        assert len(d["edges"]) == 1
        assert d["extraction_confidence"] == 0.85


class TestDiagramIRBuilder:
    @pytest.mark.asyncio
    async def test_from_text_empty(self):
        builder = DiagramIRBuilder()
        ir = await builder.from_text("")
        assert ir.id
        assert ir.diagram_type == "unknown"

    @pytest.mark.asyncio
    async def test_from_text_plantuml(self):
        content = """
@startuml
actor User
participant "API Service" as API
database DB
User -> API: GET /data
API -> DB: SELECT
@enduml
"""
        builder = DiagramIRBuilder()
        ir = await builder.from_text(content)
        assert ir.diagram_type in ("sequence", "plantuml")
        assert ir.source_format == DiagramFormat.PLANTUML

    @pytest.mark.asyncio
    async def test_from_text_mermaid(self):
        content = """
graph TD
    A[Client] --> B[API Gateway]
    B --> C[Service]
    C --> D[Database]
"""
        builder = DiagramIRBuilder()
        ir = await builder.from_text(content)
        assert ir.diagram_type in ("mermaid", "flowchart")

    @pytest.mark.asyncio
    async def test_detect_format(self):
        builder = DiagramIRBuilder()
        assert builder._detect_format("@startuml participant") == DiagramFormat.PLANTUML
        assert builder._detect_format("graph TD") == DiagramFormat.MERMAID
        assert builder._detect_format("flowchart TD") == DiagramFormat.MERMAID
        assert builder._detect_format('{"openapi": "3.0"}') == DiagramFormat.OPENAPI
        assert builder._detect_format("<mxfile>") == DiagramFormat.DRAW_IO

    @pytest.mark.asyncio
    async def test_enrich_returns_original(self):
        ir = DiagramIR(
            id="d1",
            diagram_type="class",
            nodes=[
                DiagramNode(id="n1", type=DiagramNodeType.UNKNOWN, name="unknown-node"),
            ],
        )
        builder = DiagramIRBuilder()
        enriched = await builder.enrich(ir)
        assert enriched.id == ir.id
        assert len(enriched.nodes) > 0


class TestDiagramFormat:
    def test_format_enum(self):
        assert DiagramFormat.PLANTUML.value == "plantuml"
        assert DiagramFormat.MERMAID.value == "mermaid"
        assert DiagramFormat.DRAW_IO.value == "drawio"
        assert DiagramFormat.OPENAPI.value == "openapi"
        assert DiagramFormat.BPMN.value == "bpmn"
        assert DiagramFormat.IMAGE.value == "image"
        assert DiagramFormat.UNKNOWN.value == "unknown"


class TestDiagramNodeType:
    def test_node_type_enum(self):
        assert DiagramNodeType.SERVICE.value == "service"
        assert DiagramNodeType.DATABASE.value == "database"
        assert DiagramNodeType.API.value == "api"
        assert DiagramNodeType.USER.value == "user"
        assert DiagramNodeType.COMPONENT.value == "component"
        assert DiagramNodeType.QUEUE.value == "queue"
        assert DiagramNodeType.STORAGE.value == "storage"
        assert DiagramNodeType.GATEWAY.value == "gateway"
        assert DiagramNodeType.EXTERNAL.value == "external"
        assert DiagramNodeType.UNKNOWN.value == "unknown"


class TestDiagramEdgeType:
    def test_edge_type_enum(self):
        assert DiagramEdgeType.CALLS.value == "calls"
        assert DiagramEdgeType.READS.value == "reads"
        assert DiagramEdgeType.WRITES.value == "writes"
        assert DiagramEdgeType.PUBLISHES.value == "publishes"
        assert DiagramEdgeType.SUBSCRIBES.value == "subscribes"
        assert DiagramEdgeType.CONTAINS.value == "contains"
        assert DiagramEdgeType.DEPLOYS.value == "deploys"
        assert DiagramEdgeType.AUTHENTICATES.value == "authenticates"
        assert DiagramEdgeType.UNKNOWN.value == "unknown"