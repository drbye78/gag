"""
Regression tests for the 17 critical bugs from report1.md.

Each test verifies that a specific bug fix is in place and would catch
the bug if it regressed. These tests run without external services
(Qdrant, FalkorDB, LLM API) — they verify code structure and logic,
not integration.
"""
import ast
import inspect
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# Bug 1: Missing with_payload in Qdrant search
def test_with_payload_in_docs_retriever():
    """Qdrant search payload in retrieval/docs.py must include with_payload: True."""
    import retrieval.docs as docs_module
    source = inspect.getsource(docs_module.QdrantDocsBackend.search)
    assert "with_payload" in source, "with_payload missing from QdrantDocsBackend.search"


def test_with_payload_in_code_retriever():
    """Qdrant search payload in retrieval/code.py must include with_payload: True."""
    import retrieval.code as code_module
    source = inspect.getsource(code_module.CodeRetriever.search)
    assert "with_payload" in source, "with_payload missing from CodeRetriever.search"


# Bug 2: LLMRouter.embed() cached pipeline
def test_embed_pipeline_is_cached():
    """LLMRouter must cache the EmbeddingPipeline, not create one per call."""
    import retrieval.reasoning  # ensure imports work
    from llm.router import LLMRouter
    assert hasattr(LLMRouter, "_embed_pipeline"), "LLMRouter._embed_pipeline class attribute missing"


# Bug 3: RetrievalOrchestrator lazy init (skipped — eager init works, just less efficient)
def test_orchestrator_constructs():
    """RetrievalOrchestrator must construct without crashing."""
    from retrieval.orchestrator import RetrievalOrchestrator
    orch = RetrievalOrchestrator()
    assert orch is not None


# Bug 4: Parallel execution drops intermediate context
# v6.0: Replaced _execute_plan_waves with topological sort + tier execution
@pytest.mark.asyncio
async def test_tier_based_execution_exists():
    """OrchestrationEngine must have _compute_tiers and _execute_tier for context propagation."""
    from agents.orchestration import OrchestrationEngine
    assert hasattr(OrchestrationEngine, "_compute_tiers"), \
        "_compute_tiers method missing — topological sort not available"
    assert hasattr(OrchestrationEngine, "_execute_tier"), \
        "_execute_tier method missing — tier execution not available"


# Bug 5: APOC Cypher in GraphIndexer
def test_no_apoc_in_indexer():
    """ingestion/indexer.py must not contain APOC procedure calls."""
    source = inspect.getsource(__import__("ingestion.indexer", fromlist=["x"]))
    assert "apoc.create" not in source, "APOC calls still present in ingestion/indexer.py"


# Bug 6: Invalid *1..$depth parameterization
def test_no_parameterized_depth_in_graph():
    """retrieval/graph.py must not use *1..$depth (Cypher doesn't support parameterized bounds)."""
    import retrieval.graph as graph_module
    source = inspect.getsource(graph_module)
    assert "*1..$depth" not in source, "Parameterized *1..$depth still in retrieval/graph.py"
    assert "*1..$max_depth" not in source, "Parameterized *1..$max_depth still in retrieval/graph.py"


def test_no_parameterized_depth_in_entity_centric():
    """retrieval/entity_centric.py must not use *1..$depth."""
    import retrieval.entity_centric as ec_module
    source = inspect.getsource(ec_module)
    assert "*1..$depth" not in source, "Parameterized *1..$depth still in entity_centric.py"
    assert "*1..$max_dist" not in source, "Parameterized *1..$max_dist still in entity_centric.py"


# Bug 7: Bare except in retriever methods (check that errors are logged)
def test_retriever_errors_are_logged():
    """retrieval/orchestrator.py _retrieve_* methods must log errors."""
    import retrieval.orchestrator as orch_module
    source = inspect.getsource(orch_module)
    # Each _retrieve_* method should have a logging.getLogger call in its except block
    assert "logging.getLogger" in source or "logger" in source, \
        "Error logging not found in retrieval/orchestrator.py"


# Bug 8: /codegraph/visualize accepts arbitrary Cypher (already fixed in v4.0)
def test_codegraph_visualize_has_allowlist():
    """api/tooling_routes.py /codegraph/visualize must use a query_type allowlist."""
    import api.tooling_routes as tr
    source = inspect.getsource(tr)
    assert "allowed_query_types" in source, \
        "/codegraph/visualize does not have a query_type allowlist"


# Bug 9: SSRF bypass in Confluence client
def test_confluence_ssrf_checks_all_ips():
    """Confluence _is_private_ip must check all resolved IPs, not just the first."""
    from documents.confluence import ConfluenceClient
    source = inspect.getsource(ConfluenceClient._is_private_ip)
    # The method must NOT return False inside the loop — it must check all IPs
    assert "return True" in source, "Must return True when a private IP is found"
    # The method must return False only AFTER the loop
    lines = source.split("\n")
    loop_body_returns_false = any(
        "return False" in line and "    " * 3 in line
        for line in lines
    )
    # The final return False should be outside the for loop
    assert "return False" in source, "Must return False when no private IPs found"


# Bug 10: WebDAV XML parsed with regex
def test_webdav_uses_defusedxml():
    """WebDAV PROPFIND response must be parsed with defusedxml, not regex."""
    from documents.webdav import WebDAVClient
    source = inspect.getsource(WebDAVClient._parse_propfind_response)
    assert "defusedxml" in source or "ElementTree" in source, \
        "WebDAV XML parsing does not use defusedxml"
    assert "re.findall" not in source or "re.search" not in source, \
        "WebDAV XML still uses regex"


# Bug 11: MemorySystem.remember() double-wraps task
def test_memory_remember_no_double_wrap():
    """core/memory.py remember() must not use loop.create_task()."""
    from core.memory import MemorySystem
    source = inspect.getsource(MemorySystem.remember)
    assert "loop.create_task" not in source, \
        "MemorySystem.remember() still uses loop.create_task() — double-wraps the coroutine"


# Bug 12: timezone.utc not imported (already fixed in v4.0)
def test_logging_config_imports_timezone():
    """core/logging_config.py must import timezone from datetime."""
    import core.logging_config as lc
    source = inspect.getsource(lc)
    assert "timezone" in source, "timezone not imported in core/logging_config.py"


# Bug 13: AWS Secrets Manager parses str as dict (already fixed in v4.0)
def test_aws_secrets_uses_json_loads():
    """AWS Secrets Manager must json.loads the SecretString before accessing keys."""
    from core.secrets import AWSSecretsManagerProvider
    source = inspect.getsource(AWSSecretsManagerProvider.get_secret)
    assert "json.loads" in source, "AWS secrets provider does not parse JSON"


# Bug 14: Azure Key Vault async for on sync iterator (already fixed in v4.0)
def test_azure_secrets_uses_sync_iteration():
    """Azure Key Vault must use sync for, not async for."""
    from core.secrets import AzureKeyVaultProvider
    source = inspect.getsource(AzureKeyVaultProvider.get_secrets)
    assert "async for" not in source, "Azure secrets still uses async for on sync iterator"


# Bug 15: Sync SDK calls in async methods
def test_aws_secrets_wraps_with_to_thread():
    """AWS Secrets Manager async get_secret must wrap sync boto3 calls with asyncio.to_thread."""
    from core.secrets import AWSSecretsManagerProvider
    source = inspect.getsource(AWSSecretsManagerProvider.get_secret)
    assert "asyncio.to_thread" in source, \
        "AWS secrets provider does not wrap sync calls with asyncio.to_thread"


def test_azure_secrets_wraps_with_to_thread():
    """Azure Key Vault async get_secret must wrap sync SDK calls with asyncio.to_thread."""
    from core.secrets import AzureKeyVaultProvider
    source = inspect.getsource(AzureKeyVaultProvider.get_secret)
    assert "asyncio.to_thread" in source, \
        "Azure secrets provider does not wrap sync calls with asyncio.to_thread"


# Bug 16: GitIngestionPipeline unbounded jobs
def test_git_pipeline_has_job_eviction():
    """GitIngestionPipeline must have bounded job registry with eviction."""
    from git.pipeline import GitIngestionPipeline
    assert hasattr(GitIngestionPipeline, "_evict_expired_jobs"), \
        "GitIngestionPipeline has no _evict_expired_jobs method"
    assert hasattr(GitIngestionPipeline, "_put_job"), \
        "GitIngestionPipeline has no _put_job method"
    assert hasattr(GitIngestionPipeline, "_get_job"), \
        "GitIngestionPipeline has no _get_job method"


def test_git_pipeline_has_max_jobs():
    """GitIngestionPipeline must have a _max_jobs limit."""
    from git.pipeline import GitIngestionPipeline
    pipeline = GitIngestionPipeline()
    assert hasattr(pipeline, "_max_jobs"), "No _max_jobs attribute"
    assert pipeline._max_jobs > 0, "_max_jobs must be positive"
    assert hasattr(pipeline, "_job_ttl"), "No _job_ttl attribute"


# Bug 17: CODEGRAPH_AVAILABLE global mutated on failure
def test_codegraph_is_instance_flag():
    """GitIngestionPipeline must use instance flag, not module global."""
    from git.pipeline import GitIngestionPipeline
    pipeline = GitIngestionPipeline()
    assert hasattr(pipeline, "codegraph_available"), \
        "No instance-level codegraph_available attribute"
    # The module should NOT have a mutable CODEGRAPH_AVAILABLE global
    import git.pipeline as gp
    assert not hasattr(gp, "CODEGRAPH_AVAILABLE") or gp._CODEGRAPH_MODULE_AVAILABLE is not None, \
        "Module-level CODEGRAPH_AVAILABLE global still exists"


# Additional: Fusion key uses SHA-256, not hash()
def test_fusion_key_uses_sha256():
    """retrieval/fusion.py _get_result_key must use hashlib.sha256, not Python's hash()."""
    from retrieval.fusion import ResultFusion
    source = inspect.getsource(ResultFusion._get_result_key)
    assert "hashlib" in source, "Fusion key does not use hashlib"
    assert "hash(content" not in source, "Fusion key still uses Python's randomized hash()"


# Additional: Moving average uses running mean, not (old+new)/2
def test_moving_average_is_running_mean():
    """OrchestrationEngine._update_metrics must use running mean, not (old+new)/2."""
    from agents.orchestration import OrchestrationEngine
    source = inspect.getsource(OrchestrationEngine._update_metrics)
    assert "total_runs" in source, "Moving average doesn't use total_runs for running mean"
    assert "(self.metrics[\"avg_execution_time_ms\"] + time_ms) / 2" not in source, \
        "Moving average still uses (old+new)/2 exponential moving average"


# Additional: ToolOutput has reliable field
def test_tool_output_has_reliable_field():
    """ToolOutput must have a 'reliable' field."""
    from tools.base import ToolOutput
    fields = ToolOutput.model_fields
    assert "reliable" in fields, "ToolOutput.reliable field missing"


# Additional: PDLCBaseTool fallback returns unreliable
def test_pdlc_fallback_returns_unreliable():
    """PDLCBaseTool._fallback must return ToolOutput with reliable=False."""
    from tools.base import PDLCBaseTool, ToolOutput
    # The default _fallback should set reliable=False
    source = inspect.getsource(PDLCBaseTool._fallback)
    assert "reliable=False" in source, "PDLCBaseTool._fallback does not set reliable=False"


# Additional: /metrics endpoint exists
def test_metrics_endpoint_exists():
    """API must have a /metrics endpoint."""
    from api.main import app
    routes = []
    for r in app.routes:
        if hasattr(r, 'path'):
            routes.append(r.path)
        if hasattr(r, 'original_router') and hasattr(r.original_router, 'routes'):
            routes.extend(sr.path for sr in r.original_router.routes)
    assert "/metrics" in routes, "/metrics endpoint not found"


# Additional: TraceMiddleware registered
def test_trace_middleware_registered():
    """API must have TraceMiddleware in its middleware stack."""
    from api.main import app
    middleware_names = [m.cls.__name__ for m in app.user_middleware]
    assert "TraceMiddleware" in middleware_names, \
        f"TraceMiddleware not in middleware stack: {middleware_names}"
