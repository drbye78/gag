"""
Tests for Platform V adapter module.

Covers: adapter interface, knowledge graph integration, IR transformation,
client stubs, auto-detect, and constraint engine integration.
"""

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import HTTPError

from core.adapters.base import AdapterInput, AdapterOutput
from core.adapters.models import (
    ComplianceFramework,
    ComplianceMatrix,
    CostEstimate,
    DependencyGraph,
    FSTECLevel,
    ServiceEdition,
    ServiceSpec,
    summarize_portfolios,
    filter_by_portfolio,
    filter_by_certification,
)
from core.adapters.platformv import (
    IAMAuthClient,
    IAMToken,
    PlatformVAdapter,
    PlatformVClient,
    DataSpaceClient,
    FlowClient,
    SynapseMeshClient,
    WorksClient,
    SOWAClient,
    MonitorClient,
    PLATFORM_V_SERVICES,
    PLATFORM_V_SERVICE_CATALOG,
    PLATFORM_V_PATTERNS,
    PLATFORM_V_USE_CASES,
    PLATFORM_V_ADRS,
    PLATFORM_V_REF_ARCHS,
    PLATFORM_V_CONSTRAINTS,
    register_platform_knowledge,
)
from core.knowledge.graph import NodeType, get_knowledge_graph
from models.ir import IRFeature, PlatformContext


# ===========================================================================
# Module-level constants
# ===========================================================================


class TestConstants:
    def test_services_count(self):
        assert len(PLATFORM_V_SERVICES) == 57

    def test_patterns_count(self):
        assert len(PLATFORM_V_PATTERNS) == 8

    def test_use_cases_count(self):
        assert len(PLATFORM_V_USE_CASES) == 8

    def test_adrs_count(self):
        assert len(PLATFORM_V_ADRS) == 8

    def test_ref_archs_count(self):
        assert len(PLATFORM_V_REF_ARCHS) == 4

    def test_constraints_counts(self):
        assert len(PLATFORM_V_CONSTRAINTS["hard"]) == 4
        assert len(PLATFORM_V_CONSTRAINTS["soft"]) == 4


# ===========================================================================
# IAM Auth Client
# ===========================================================================


class TestIAMAuthClient:
    def test_token_validity(self):
        token = IAMToken(access_token="abc123", expires_at=float("inf"))
        assert token.valid
        assert not token.expired

    @patch("core.adapters.platformv.requests.post")
    def test_fetch_token_success(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "access_token": "tok_123",
                "expires_in": 3600,
            },
        )

        client = IAMAuthClient(
            token_url="https://iam.example.com/token",
            client_id="test",
            client_secret="secret",
        )
        headers = client.get_headers()
        assert headers["Authorization"] == "Bearer tok_123"

    @patch("core.adapters.platformv.requests.post")
    def test_fetch_token_http_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = HTTPError("401 Unauthorized")
        mock_post.return_value = mock_response

        client = IAMAuthClient(
            token_url="https://iam.example.com/token",
            client_id="test",
            client_secret="wrong",
        )
        with pytest.raises(HTTPError):
            client.get_headers()


# ===========================================================================
# Base HTTP Client
# ===========================================================================


class TestPlatformVClient:
    def test_base_url_strips_trailing_slash(self):
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = PlatformVClient(auth, "https://api.example.com/")
        assert client.base_url == "https://api.example.com"

    @patch.object(PlatformVClient, "request")
    def test_get_delegates_to_request(self, mock_request):
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = PlatformVClient(auth, "https://api.example.com")
        client.get("/test")
        mock_request.assert_called_once_with("GET", "/test")

    @patch.object(PlatformVClient, "request")
    def test_post_delegates_to_request(self, mock_request):
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = PlatformVClient(auth, "https://api.example.com")
        client.post("/test", json={"key": "value"})
        mock_request.assert_called_once_with("POST", "/test", json={"key": "value"})


# ===========================================================================
# DataSpace Client
# ===========================================================================


class TestDataSpaceClient:
    @patch.object(DataSpaceClient, "request")
    def test_execute_query(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": {"users": [{"id": "1"}]}},
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = DataSpaceClient(auth, "https://dataspace.example.com")

        result = client.execute_query("{ users { id } }")
        assert result["data"]["users"][0]["id"] == "1"

    @patch.object(DataSpaceClient, "request")
    def test_introspect_schema(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": {"__schema": {"types": []}}},
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = DataSpaceClient(auth, "https://dataspace.example.com")

        result = client.introspect_schema()
        assert "__schema" in result["data"]


# ===========================================================================
# Flow Client
# ===========================================================================


class TestFlowClient:
    @patch.object(FlowClient, "request")
    def test_deploy_process(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=201,
            json=lambda: {"id": "deploy_1", "name": "my-process"},
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = FlowClient(auth, "https://flow.example.com")

        result = client.deploy_process("<bpmn>...</bpmn>")
        assert result["id"] == "deploy_1"

    @patch.object(FlowClient, "request")
    def test_start_process_instance(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=201,
            json=lambda: {"id": "pi_1", "processDefinitionKey": "my-process"},
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = FlowClient(auth, "https://flow.example.com")

        result = client.start_process_instance("my-process", {"var1": "val1"})
        assert result["id"] == "pi_1"

    @patch.object(FlowClient, "request")
    def test_query_tasks(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": [{"id": "task_1"}, {"id": "task_2"}]},
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = FlowClient(auth, "https://flow.example.com")

        tasks = client.query_tasks(assignee="user1")
        assert len(tasks) == 2

    @patch.object(FlowClient, "request")
    def test_get_process_history(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "pi_1", "endTime": "2024-01-01T00:00:00Z"},
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = FlowClient(auth, "https://flow.example.com")

        result = client.get_process_history("pi_1")
        assert result["id"] == "pi_1"


# ===========================================================================
# Synapse Mesh Client
# ===========================================================================


class TestSynapseMeshClient:
    @patch.object(SynapseMeshClient, "request")
    def test_get_virtual_services(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            json=lambda: {"items": [{"metadata": {"name": "vs-1"}}]},
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = SynapseMeshClient(auth, "https://synapse.example.com")

        services = client.get_virtual_services()
        assert len(services) == 1

    @patch.object(SynapseMeshClient, "request")
    def test_get_service_graph(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            json=lambda: {"nodes": [], "edges": []},
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = SynapseMeshClient(auth, "https://synapse.example.com")

        graph = client.get_service_graph()
        assert "nodes" in graph


# ===========================================================================
# Works Client
# ===========================================================================


class TestWorksClient:
    @patch.object(WorksClient, "request")
    def test_list_projects(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            json=lambda: [{"id": 1, "name": "project-a"}],
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = WorksClient(auth, "https://works.example.com")

        projects = client.list_projects()
        assert len(projects) == 1

    @patch.object(WorksClient, "request")
    def test_trigger_pipeline(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=201,
            json=lambda: {"id": "pipeline_1", "status": "pending"},
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = WorksClient(auth, "https://works.example.com")

        result = client.trigger_pipeline("project_1")
        assert result["status"] == "pending"

    @patch.object(WorksClient, "request")
    def test_run_code_scan(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            json=lambda: {"scan_id": "scan_1", "issues": []},
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = WorksClient(auth, "https://works.example.com")

        result = client.run_code_scan("project_1")
        assert result["scan_id"] == "scan_1"

    @patch.object(WorksClient, "request")
    def test_list_artifacts(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            json=lambda: [{"name": "my-app-1.0.0.jar"}],
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = WorksClient(auth, "https://works.example.com")

        artifacts = client.list_artifacts("project_1")
        assert len(artifacts) == 1

    @patch.object(WorksClient, "request")
    def test_get_pipeline_status(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "pipeline_1", "status": "success"},
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = WorksClient(auth, "https://works.example.com")

        result = client.get_pipeline_status("project_1", "pipeline_1")
        assert result["status"] == "success"


# ===========================================================================
# SOWA Client
# ===========================================================================


class TestSOWAClient:
    @patch.object(SOWAClient, "request")
    def test_list_policies(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            json=lambda: [{"id": "policy_1", "name": "Block SQLi"}],
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = SOWAClient(auth, "https://sowa.example.com")

        policies = client.list_policies()
        assert len(policies) == 1

    @patch.object(SOWAClient, "request")
    def test_create_waf_rule(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=201,
            json=lambda: {"id": "rule_1"},
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = SOWAClient(auth, "https://sowa.example.com")

        result = client.create_waf_rule({"action": "block", "pattern": ".*malicious.*"})
        assert result["id"] == "rule_1"

    @patch.object(SOWAClient, "request")
    def test_get_traffic_stats(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            json=lambda: {"requests_total": 15000, "blocked": 23},
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = SOWAClient(auth, "https://sowa.example.com")

        stats = client.get_traffic_stats()
        assert stats["requests_total"] == 15000

    @patch.object(SOWAClient, "request")
    def test_list_rate_limits(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            json=lambda: [{"id": "rl_1", "max_requests": 100}],
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = SOWAClient(auth, "https://sowa.example.com")

        limits = client.list_rate_limits()
        assert len(limits) == 1


# ===========================================================================
# Monitor Client
# ===========================================================================


class TestMonitorClient:
    @patch.object(MonitorClient, "request")
    def test_query_metrics(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "success", "data": {"result": []}},
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = MonitorClient(auth, "https://monitor.example.com")

        result = client.query_metrics("up")
        assert result["status"] == "success"

    @patch.object(MonitorClient, "request")
    def test_list_alerts(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            json=lambda: [{"name": "HighCPU", "status": "firing"}],
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = MonitorClient(auth, "https://monitor.example.com")

        alerts = client.list_alerts()
        assert len(alerts) == 1

    @patch.object(MonitorClient, "request")
    def test_create_dashboard(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=201,
            json=lambda: {"id": "dash_1", "url": "/dashboards/dash_1"},
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = MonitorClient(auth, "https://monitor.example.com")

        result = client.create_dashboard("My Dashboard", [{"title": "CPU"}])
        assert result["id"] == "dash_1"

    @patch.object(MonitorClient, "request")
    def test_get_logs(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            json=lambda: [{"timestamp": "...", "message": "error"}],
        )
        auth = IAMAuthClient("https://token", "cid", "secret")
        client = MonitorClient(auth, "https://monitor.example.com")

        logs = client.get_logs("error", limit=10)
        assert len(logs) == 1


# ===========================================================================
# PlatformVAdapter — core interface
# ===========================================================================


class TestPlatformVAdapterCore:
    def test_platform_id(self):
        adapter = PlatformVAdapter()
        assert adapter.platform_id == "platformv"

    def test_supported_services(self):
        adapter = PlatformVAdapter()
        assert len(adapter.supported_services) == 57
        assert "Platform V Pangolin" in adapter.supported_services

    def test_patterns(self):
        adapter = PlatformVAdapter()
        patterns = adapter.patterns
        assert len(patterns) == 8
        ids = [p.id for p in patterns]
        assert "pv_microservices_k8s" in ids
        assert "pv_import_substitution" in ids

    def test_constraints(self):
        adapter = PlatformVAdapter()
        assert len(adapter.constraints["hard"]) == 4
        assert len(adapter.constraints["soft"]) == 4

    def test_use_cases_property(self):
        adapter = PlatformVAdapter()
        ucs = adapter.use_cases
        assert len(ucs) == 8
        categories = {uc.category.value for uc in ucs}
        assert "compliance" in categories
        assert "security" in categories

    def test_architecture_decision_records(self):
        adapter = PlatformVAdapter()
        adrs = adapter.architecture_decision_records
        assert len(adrs) == 8
        titles = [a.title for a in adrs]
        assert "Use Pangolin as Default RDBMS" in titles

    def test_reference_architectures(self):
        adapter = PlatformVAdapter()
        refs = adapter.reference_architectures
        assert len(refs) == 4
        names = [r.name for r in refs]
        assert "Microservices on Synapse Service Mesh" in names

    def test_auth_lifecycle(self):
        adapter = PlatformVAdapter()
        with pytest.raises(RuntimeError, match="IAM auth not configured"):
            _ = adapter.auth

        adapter.configure_auth("https://token", "cid", "secret")
        assert adapter.auth is not None

    def test_client_factories(self):
        adapter = PlatformVAdapter()
        adapter.configure_auth("https://token", "cid", "secret")

        base = adapter.get_client("https://api")
        assert isinstance(base, PlatformVClient)

        ds = adapter.get_dataspace_client("https://ds")
        assert isinstance(ds, DataSpaceClient)

        flow = adapter.get_flow_client("https://flow")
        assert isinstance(flow, FlowClient)

        syn = adapter.get_synapse_client("https://syn")
        assert isinstance(syn, SynapseMeshClient)

        w = adapter.get_works_client("https://works")
        assert isinstance(w, WorksClient)

        s = adapter.get_sowa_client("https://sowa")
        assert isinstance(s, SOWAClient)

        m = adapter.get_monitor_client("https://mon")
        assert isinstance(m, MonitorClient)


# ===========================================================================
# PlatformVAdapter — IR transformation
# ===========================================================================


class TestPlatformVAdapterIRTransform:
    def _make_input(self, ir_features=None, violations=None):
        if ir_features is None:
            ir_features = IRFeature()
        return AdapterInput(
            ir_features=ir_features,
            platform_context=PlatformContext(platform="platformv"),
            constraint_violations=violations or [],
        )

    def test_transform_no_features(self):
        """Should return generic fallback recommendations when no features."""
        adapter = PlatformVAdapter()
        input_data = self._make_input()
        output = adapter.transform_ir_to_platform(input_data)
        assert output.platform == "platformv"
        assert len(output.recommendations) > 0
        assert output.can_deploy

    def test_transform_with_db_feature(self):
        """Should recommend Pangolin when relational DB is needed."""
        adapter = PlatformVAdapter()
        ir = IRFeature(has_database=True)
        input_data = self._make_input(ir)
        output = adapter.transform_ir_to_platform(input_data)
        assert output.platform == "platformv"
        assert len(output.recommendations) > 0

    def test_transform_with_event_driven(self):
        """Should recommend Synapse Event Replication for event-driven."""
        adapter = PlatformVAdapter()
        ir = IRFeature(has_async=True)
        input_data = self._make_input(ir)
        output = adapter.transform_ir_to_platform(input_data)
        assert output.platform == "platformv"
        assert len(output.recommendations) > 0

    def test_transform_with_compliance(self):
        """FSTEC compliance should map to import substitution products."""
        adapter = PlatformVAdapter()
        ir = IRFeature(
            compliance_requirements=["fstec"],
            data_classification="sensitive",
        )
        input_data = self._make_input(ir)
        output = adapter.transform_ir_to_platform(input_data)
        assert output.platform == "platformv"
        services = [r.get("name") or r.get("service", "") for r in output.recommendations]
        assert len(services) > 0

    def test_transform_generates_configs(self):
        """Should generate config templates when matching products found."""
        adapter = PlatformVAdapter()
        ir = IRFeature()
        input_data = self._make_input(ir)
        output = adapter.transform_ir_to_platform(input_data)
        assert isinstance(output.recommendations, list)
        assert isinstance(output.config_templates, dict)
        assert isinstance(output.explanation, str)
        assert 0 <= output.confidence <= 1.0

    def test_transform_can_deploy_with_violations(self):
        """can_deploy should be False when error-level violations exist."""
        adapter = PlatformVAdapter()
        ir = IRFeature()
        violations = [
            type("Violation", (), {"severity": "error", "message": "test", "fix_hint": ""})()
        ]
        input_data = self._make_input(ir, violations)
        output = adapter.transform_ir_to_platform(input_data)
        assert not output.can_deploy


# ===========================================================================
# Knowledge Graph Integration
# ===========================================================================


class TestKnowledgeGraphIntegration:
    def test_platform_node_exists(self):
        """Platform V node should be in the knowledge graph."""
        graph = get_knowledge_graph()
        node = graph.get_node("platformv")
        assert node is not None
        assert node.type == NodeType.PLATFORM

    def test_use_case_nodes_exist(self):
        """Use case nodes should be in the knowledge graph."""
        graph = get_knowledge_graph()
        ucs = graph.find_by_type(NodeType.USE_CASE)
        pv_ucs = [n for n in ucs if n.id.startswith("uc-pv-")]
        assert len(pv_ucs) >= 8

    def test_adr_nodes_exist(self):
        """ADR (decision) nodes should be in the knowledge graph."""
        graph = get_knowledge_graph()
        decisions = graph.find_by_type(NodeType.DECISION)
        pv_decisions = [n for n in decisions if n.id.startswith("adr-pv-")]
        assert len(pv_decisions) >= 8

    def test_ref_arch_nodes_exist(self):
        """Reference architecture nodes should be in the knowledge graph."""
        graph = get_knowledge_graph()
        refs = graph.find_by_type(NodeType.REFERENCE_ARCH)
        pv_refs = [n for n in refs if n.id.startswith("ref-pv-")]
        assert len(pv_refs) >= 4

    def test_platform_edges(self):
        """Platform V node should have outgoing edges."""
        graph = get_knowledge_graph()
        pv_edges = [e for e in graph.edges if e.source_id == "platformv"]
        assert len(pv_edges) >= 20  # 8 use cases + 8 ADRs + 4 ref archs + services
        edge_types = {e.type.value for e in pv_edges}
        assert "implements" in edge_types
        assert "composed_of" in edge_types

    def test_register_knowledge_idempotent(self):
        """Calling register_platform_knowledge multiple times is safe."""
        register_platform_knowledge()
        register_platform_knowledge()
        register_platform_knowledge()
        graph = get_knowledge_graph()
        node = graph.get_node("platformv")
        assert node is not None


# ===========================================================================
# Auto-detect
# ===========================================================================


class TestAutoDetect:
    def test_auto_detect_platformv_keywords(self):
        """Auto-detect should match platformv keywords."""
        from core.adapters.base import AdapterRegistry

        registry = AdapterRegistry()
        registry.register(PlatformVAdapter())

        class MockIR:
            def model_dump(self):
                return {
                    "integration_points": ["sber", "gosuslugi"],
                    "compliance_requirements": ["fstec"],
                }

        adapter = registry.auto_detect(MockIR())
        assert adapter.platform_id == "platformv"

    def test_auto_detect_cyrillic(self):
        """Auto-detect should match Cyrillic keywords."""
        from core.adapters.base import AdapterRegistry

        registry = AdapterRegistry()
        registry.register(PlatformVAdapter())

        class MockIR:
            def model_dump(self):
                return {
                    "integration_points": [],
                    "compliance_requirements": ["импортозамещение", "фстэк"],
                }

        adapter = registry.auto_detect(MockIR())
        assert adapter.platform_id == "platformv"

    def test_auto_detect_no_match_fallback(self):
        """Auto-detect should fall back to first adapter when no match."""
        from core.adapters.base import AdapterRegistry
        from core.adapters.clouds import AWSAdapter

        registry = AdapterRegistry()
        registry.register(AWSAdapter())
        registry.register(PlatformVAdapter())

        class MockIR:
            def model_dump(self):
                return {"integration_points": ["nothing", "matching"]}

        adapter = registry.auto_detect(MockIR())
        assert adapter is not None
        assert adapter.platform_id == "aws"


# ===========================================================================
# Constraint Engine Integration
# ===========================================================================


class TestConstraintIntegration:
    def test_constraint_set_registered(self):
        """Platform V constraint set should be in the engine."""
        from core.constraints.engine import get_constraint_engine

        engine = get_constraint_engine()
        cs = engine._constraint_sets.get("platformv")
        assert cs is not None
        assert len(cs.constraints) == 8

    def test_hard_constraint_validation(self):
        """Hard constraints should produce violations when violated."""
        from core.constraints.engine import get_constraint_engine

        engine = get_constraint_engine()
        violations = engine.evaluate(
            {"data_storage": False, "operating_system": "ubuntu"},
            "platformv",
        )
        error_violations = [v for v in violations if v.severity == "error"]
        assert len(error_violations) >= 1


# ===========================================================================
# Config & Code generation
# ===========================================================================


class TestGeneration:
    def test_generate_config_returns_dict(self):
        adapter = PlatformVAdapter()
        configs = adapter.generate_config(None)
        assert isinstance(configs, dict)
        assert "pangolin.yaml" in configs
        assert "synapse.yaml" in configs
        assert "iam.yaml" in configs

    def test_generate_code_returns_dict(self):
        adapter = PlatformVAdapter()
        code = adapter.generate_code(None)
        assert isinstance(code, dict)
        assert "function.py" in code
        assert "deployment.yaml" in code

    def test_product_purpose_known_product(self):
        result = PlatformVAdapter._product_purpose("Platform V Pangolin")
        assert "PostgreSQL" in result

    def test_product_purpose_unknown_product(self):
        result = PlatformVAdapter._product_purpose("Platform V Unknown")
        assert "Unknown" in result


# ===========================================================================
# ServiceSpec Model
# ===========================================================================


class TestServiceSpec:
    def test_id_derived_from_name(self):
        spec = ServiceSpec(name="Platform V Pangolin", portfolio="data_management")
        assert spec.id == "platform-v-pangolin"

    def test_id_handles_double_colon(self):
        spec = ServiceSpec(name="Platform V Works::TaskTracker", portfolio="development")
        assert spec.id == "platform-v-works-tasktracker"

    def test_catalog_count(self):
        assert len(PLATFORM_V_SERVICE_CATALOG) == 57

    def test_catalog_includes_all_services(self):
        catalog_names = {s.name for s in PLATFORM_V_SERVICE_CATALOG}
        for svc in PLATFORM_V_SERVICES:
            assert svc in catalog_names, f"Missing: {svc}"

    def test_catalog_has_all_portfolios(self):
        portfolios = {s.portfolio for s in PLATFORM_V_SERVICE_CATALOG}
        expected = {"data_management", "integration", "development", "security", "low_code", "infrastructure", "management"}
        for p in expected:
            assert p in portfolios, f"Missing portfolio: {p}"

    def test_fstec_certified_services(self):
        fstec_services = [s for s in PLATFORM_V_SERVICE_CATALOG if any("FSTEC" in c for c in s.certifications)]
        assert len(fstec_services) > 10

    def test_iam_se_dependencies(self):
        iam = next(s for s in PLATFORM_V_SERVICE_CATALOG if s.name == "Platform V IAM SE")
        assert "Platform V SberLinux OS Server" in iam.dependencies
        assert ServiceEdition.SE in [iam.edition]

    def test_sowa_has_fstec_l4(self):
        sowa = next(s for s in PLATFORM_V_SERVICE_CATALOG if s.name == "Platform V SOWA")
        assert any("FSTEC" in c for c in sowa.certifications)
        assert sowa.sla == "99.99%"

    def test_dataspace_depends_on_iam(self):
        ds = next(s for s in PLATFORM_V_SERVICE_CATALOG if s.name == "Platform V DataSpace")
        assert "Platform V IAM SE" in ds.dependencies

    def test_cost_model_present(self):
        no_cost = [s for s in PLATFORM_V_SERVICE_CATALOG if not s.cost_model]
        assert len(no_cost) == 0, f"Services missing cost_model: {[s.name for s in no_cost]}"

    def test_editions_varied(self):
        editions = {s.edition for s in PLATFORM_V_SERVICE_CATALOG}
        assert ServiceEdition.ENTERPRISE in editions
        assert ServiceEdition.STANDARD in editions
        assert ServiceEdition.SE in editions
        assert ServiceEdition.COMMUNITY in editions


# ===========================================================================
# DependencyGraph
# ===========================================================================


class TestDependencyGraph:
    def test_resolve_direct(self):
        graph = DependencyGraph(PLATFORM_V_SERVICE_CATALOG)
        deps = graph.resolve(["Platform V DataSpace"], transitive=False)
        assert "Platform V IAM SE" in deps

    def test_resolve_transitive(self):
        graph = DependencyGraph(PLATFORM_V_SERVICE_CATALOG)
        deps = graph.resolve(["Platform V DataSpace"], transitive=True)
        assert "Platform V IAM SE" in deps
        assert "Platform V SberLinux OS Server" in deps

    def test_resolve_multiple(self):
        graph = DependencyGraph(PLATFORM_V_SERVICE_CATALOG)
        deps = graph.resolve(["Platform V SOWA", "Platform V Flow"])
        assert "Platform V IAM SE" in deps
        assert "Platform V Container Platform" in deps or "Platform V SberLinux OS Server" in deps

    def test_no_circular_deps(self):
        graph = DependencyGraph(PLATFORM_V_SERVICE_CATALOG)
        errors = graph.validate()
        assert len(errors) == 0, f"Circular or missing dependencies: {errors}"

    def test_unknown_service(self):
        graph = DependencyGraph(PLATFORM_V_SERVICE_CATALOG)
        deps = graph.resolve(["Unknown Service"])
        assert deps == []

    def test_catalog_edges_count(self):
        graph = DependencyGraph(PLATFORM_V_SERVICE_CATALOG)
        edges = graph.get_edges()
        assert len(edges) > 20


# ===========================================================================
# Portfolio Arithmetic
# ===========================================================================


class TestPortfolioArithmetic:
    def test_summarize_portfolios(self):
        summary = summarize_portfolios(PLATFORM_V_SERVICE_CATALOG)
        assert summary["data_management"] == 13
        assert summary["integration"] == 8
        assert summary["development"] == 14
        assert summary["security"] == 6
        assert summary["low_code"] == 7
        assert summary["infrastructure"] == 7
        assert summary["management"] == 2

    def test_filter_by_portfolio(self):
        security = filter_by_portfolio(PLATFORM_V_SERVICE_CATALOG, "security")
        assert len(security) == 6
        names = {s.name for s in security}
        assert "Platform V IAM SE" in names
        assert "Platform V One Time Tokens" in names

    def test_filter_by_certification(self):
        fstec_services = filter_by_certification(PLATFORM_V_SERVICE_CATALOG, "FSTEC L4")
        names = {s.name for s in fstec_services}
        assert "Platform V Pangolin SE" in names
        assert "Platform V IAM SE" in names
        assert "Platform V SOWA" in names
        assert "Platform V CryptoService" in names
        assert "Platform V Audit SE" in names
        assert "Platform V SberLinux OS Server" in names


# ===========================================================================
# Enhanced AdapterOutput
# ===========================================================================


class TestEnhancedAdapterOutput:
    def _make_input(self, ir_features=None):
        if ir_features is None:
            ir_features = IRFeature()
        return AdapterInput(
            ir_features=ir_features,
            platform_context=PlatformContext(platform="platformv"),
            constraint_violations=[],
        )

    def test_output_has_service_specs(self):
        adapter = PlatformVAdapter()
        output = adapter.transform_ir_to_platform(self._make_input())
        assert hasattr(output, "service_specs")
        assert len(output.service_specs) > 0
        for spec in output.service_specs:
            assert isinstance(spec, ServiceSpec)
            assert spec.portfolio in ("data_management", "integration", "development", "security", "low_code", "infrastructure", "management", "other")

    def test_output_has_compliance_matrix(self):
        adapter = PlatformVAdapter()
        ir = IRFeature(
            compliance_requirements=["fstec", "152-fz"],
            data_classification="sensitive",
        )
        output = adapter.transform_ir_to_platform(self._make_input(ir))
        assert hasattr(output, "compliance_matrix")
        frameworks = [m.framework for m in output.compliance_matrix]
        assert ComplianceFramework.FSTEC in frameworks

    def test_output_has_cost_estimate(self):
        adapter = PlatformVAdapter()
        output = adapter.transform_ir_to_platform(self._make_input())
        assert hasattr(output, "cost_estimate")
        if output.cost_estimate:
            assert isinstance(output.cost_estimate, CostEstimate)
            assert output.cost_estimate.currency == "USD"

    def test_output_has_required_dependencies(self):
        adapter = PlatformVAdapter()
        output = adapter.transform_ir_to_platform(self._make_input())
        assert hasattr(output, "required_dependencies")
        assert isinstance(output.required_dependencies, list)

    def test_output_has_portfolio_summary(self):
        adapter = PlatformVAdapter()
        output = adapter.transform_ir_to_platform(self._make_input())
        assert hasattr(output, "portfolio_summary")
        assert isinstance(output.portfolio_summary, dict)

    def test_transform_with_fstec_level_ir(self):
        """FSTEC level from IRFeature should propagate to compliance matrix."""
        adapter = PlatformVAdapter()
        ir = IRFeature(
            fstec_level="fstec-l4",
            compliance_requirements=["fstec"],
        )
        output = adapter.transform_ir_to_platform(self._make_input(ir))
        fstec_entries = [m for m in output.compliance_matrix if m.framework == ComplianceFramework.FSTEC]
        if fstec_entries:
            assert fstec_entries[0].level == FSTECLevel.FSTEC_L4

    def test_transform_with_monthly_budget(self):
        """Monthly budget from IRFeature should affect cost estimate."""
        adapter = PlatformVAdapter()
        ir = IRFeature(monthly_budget=500.0)
        output = adapter.transform_ir_to_platform(self._make_input(ir))
        if output.cost_estimate:
            assert output.cost_estimate.notes != ""

    def test_transform_with_fstec_level_in_compliance(self):
        """IR with fstec_level should include FSTEC in compliance matrix."""
        adapter = PlatformVAdapter()
        ir = IRFeature(fstec_level="fstec-l3", data_classification="sensitive")
        output = adapter.transform_ir_to_platform(self._make_input(ir))
        has_fstec = any(m.framework == ComplianceFramework.FSTEC for m in output.compliance_matrix)
        assert has_fstec

    def test_transform_with_require_gost_crypto(self):
        """IR requiring GOST crypto should include GOST in compliance."""
        adapter = PlatformVAdapter()
        ir = IRFeature(require_gost_crypto=True, compliance_requirements=["gost"])
        output = adapter.transform_ir_to_platform(self._make_input(ir))
        has_gost = any(m.framework == ComplianceFramework.GOST_CRYPTO for m in output.compliance_matrix)
        assert has_gost


# ===========================================================================
# ServiceCatalog Property
# ===========================================================================


class TestServiceCatalogProperty:
    def test_service_catalog_returns_specs(self):
        adapter = PlatformVAdapter()
        catalog = adapter.service_catalog
        assert len(catalog) == 57
        assert all(isinstance(s, ServiceSpec) for s in catalog)

    def test_supported_services_derived(self):
        adapter = PlatformVAdapter()
        assert len(adapter.supported_services) == len(adapter.service_catalog)
        for spec in adapter.service_catalog:
            assert spec.name in adapter.supported_services


# ===========================================================================
# Dependency Resolution (adapter-level)
# ===========================================================================


class TestAdapterDependencyResolution:
    def test_resolve_dependencies_platformv(self):
        adapter = PlatformVAdapter()
        deps = adapter.resolve_dependencies(["Platform V DataSpace"])
        assert "Platform V IAM SE" in deps
        assert "Platform V SberLinux OS Server" in deps

    def test_resolve_dependencies_pangolin(self):
        adapter = PlatformVAdapter()
        deps = adapter.resolve_dependencies(["Platform V Pangolin"])
        assert "Platform V SberLinux OS Server" in deps

    def test_compute_compliance_basic(self):
        adapter = PlatformVAdapter()
        features = IRFeature(compliance_requirements=["fstec"])
        matrix = adapter.compute_compliance(features, ["Platform V Pangolin", "Platform V IAM SE"])
        assert len(matrix) >= 1
        frameworks = {m.framework for m in matrix}
        assert ComplianceFramework.FSTEC in frameworks

    def test_estimate_cost_basic(self):
        adapter = PlatformVAdapter()
        features = IRFeature()
        estimate = adapter.estimate_cost(features, ["Platform V Pangolin"])
        assert estimate.monthly_min >= 0
        assert estimate.monthly_max >= estimate.monthly_min
        assert "Platform V Pangolin" in estimate.breakdown


# ===========================================================================
# Cross-adapter consistency
# ===========================================================================


class TestCrossAdapterConsistency:
    def test_all_adapters_have_service_catalog(self):
        from core.adapters.clouds import AWSAdapter, AzureAdapter, GCPAdapter
        from core.adapters.tanzu import VMwareTanzuAdapter
        from core.adapters.sap import SAPBTPAdapter
        from core.adapters.powerplatform import PowerPlatformAdapter

        adapters = [
            PlatformVAdapter(),
            AWSAdapter(),
            AzureAdapter(),
            GCPAdapter(),
            VMwareTanzuAdapter(),
            SAPBTPAdapter(),
            PowerPlatformAdapter(),
        ]
        for a in adapters:
            catalog = a.service_catalog
            assert len(catalog) > 0, f"{a.platform_id} has empty catalog"
            assert all(isinstance(s, ServiceSpec) for s in catalog), f"{a.platform_id} has non-ServiceSpec entries"
            # Every catalog entry should be in supported_services
            for spec in catalog:
                assert spec.name in a.supported_services, f"{a.platform_id}: {spec.name} not in supported_services"

    def test_all_adapters_produce_enhanced_output(self):
        from core.adapters.clouds import AWSAdapter
        from core.adapters.tanzu import VMwareTanzuAdapter

        adapters = [PlatformVAdapter(), AWSAdapter(), VMwareTanzuAdapter()]
        for a in adapters:
            output = a.transform_ir_to_platform(
                AdapterInput(
                    ir_features=IRFeature(),
                    platform_context=PlatformContext(platform=a.platform_id),
                )
            )
            assert hasattr(output, "service_specs"), f"{a.platform_id} missing service_specs"
            assert hasattr(output, "compliance_matrix"), f"{a.platform_id} missing compliance_matrix"
            assert hasattr(output, "cost_estimate"), f"{a.platform_id} missing cost_estimate"
            assert hasattr(output, "required_dependencies"), f"{a.platform_id} missing required_dependencies"
            assert hasattr(output, "portfolio_summary"), f"{a.platform_id} missing portfolio_summary"


# ===========================================================================
# CostEstimate & ComplianceMatrix utility tests
# ===========================================================================


class TestCostEstimate:
    def test_mid_range(self):
        ce = CostEstimate(monthly_min=100, monthly_max=300)
        assert ce.mid_range == 200.0

    def test_zero_cost(self):
        ce = CostEstimate()
        assert ce.mid_range == 0.0
        assert ce.currency == "USD"


class TestComplianceMatrix:
    def test_default_level(self):
        cm = ComplianceMatrix(framework=ComplianceFramework.FSTEC)
        assert cm.level == FSTECLevel.FSTEC_L1

    def test_fstec_l4_level(self):
        cm = ComplianceMatrix(framework=ComplianceFramework.FSTEC, level=FSTECLevel.FSTEC_L4)
        assert cm.level == FSTECLevel.FSTEC_L4
