"""
Regression tests for Phase 1-6 architectural fixes.
Each test verifies a specific fix is in place.
"""
import inspect
import pytest


# Phase 1.1: Lazy imports (no cascading dependency loading)
def test_agents_init_lazy():
    """agents/__init__.py should use __getattr__ for lazy loading."""
    import agents
    assert hasattr(agents, "__getattr__"), "agents/__init__.py is not lazy"


def test_retrieval_init_lazy():
    """retrieval/__init__.py should use __getattr__ for lazy loading."""
    import retrieval
    assert hasattr(retrieval, "__getattr__"), "retrieval/__init__.py is not lazy"


def test_documents_init_lazy():
    """documents/__init__.py should use __getattr__ for lazy loading."""
    import documents
    assert hasattr(documents, "__getattr__"), "documents/__init__.py is not lazy"


# Phase 1.2: Lazy handler instantiation
def test_handlers_lazy():
    """unified_ingestion/handlers/__init__.py should not instantiate handlers at import."""
    import unified_ingestion.handlers as h
    assert not hasattr(h, '_document_handler'), "Handlers still instantiated at module level"
    assert hasattr(h, '_get_or_create'), "No _get_or_create lazy factory"


# Phase 1.3: Semaphore is lazy
def test_semaphore_lazy():
    """retrieval/code_graph.py semaphore should be lazy (not module-level)."""
    import retrieval.code_graph as cg
    source = inspect.getsource(cg)
    assert "_get_cli_semaphore" in source, "No _get_cli_semaphore function"
    # The module-level variable should be None, not an active Semaphore
    assert cg._cli_semaphore is None, "Semaphore still created at module level"


# Phase 1.4: Lifespan starts HttpPool
def test_lifespan_starts_pool():
    """api/main.py lifespan should start and stop HttpPool."""
    import api.main as api_module
    source = inspect.getsource(api_module.lifespan)
    assert "get_http_pool().start()" in source, "Lifespan doesn't start HttpPool"
    assert "get_http_pool().stop()" in source, "Lifespan doesn't stop HttpPool"


# Phase 1.5: close() methods on cached clients
def test_close_methods_exist():
    """Files with cached _client should have close() methods."""
    from retrieval.docs import QdrantDocsBackend
    from retrieval.code import CodeRetriever
    assert hasattr(QdrantDocsBackend, "close"), "QdrantDocsBackend has no close()"
    assert hasattr(CodeRetriever, "close"), "CodeRetriever has no close()"


# Phase 2.2: Exponential backoff with jitter
def test_retry_is_exponential():
    """Orchestration retry should use exponential backoff, not linear."""
    from agents.orchestration import OrchestrationEngine
    source = inspect.getsource(OrchestrationEngine._execute_step)
    assert "2 ** attempt" in source or "2**attempt" in source, \
        "Retry still uses linear backoff (no 2**attempt)"
    assert "random" in source or "jitter" in source, \
        "Retry doesn't have jitter"


# Phase 2.3: Circuit breaker on LLM router
def test_circuit_breaker_exists():
    """LLMRouter should have circuit breaker fields."""
    from llm.router import LLMRouter
    src = inspect.getsource(LLMRouter)
    assert "_consecutive_failures" in src, "No circuit breaker failure counter"
    assert "_circuit_is_open" in src, "No circuit breaker check method"
    assert "_record_success" in src, "No circuit breaker success recording"


# Phase 2.5: Request body size limit
def test_request_size_limit():
    """Middleware should include body size limiting."""
    import core.middleware as mw
    source = inspect.getsource(mw.setup_middleware)
    assert "body_size_limit" in source or "MAX_BODY_SIZE" in source, \
        "No request body size limit in middleware"


# Phase 3.1: DI container has register_services
def test_di_register_services():
    """DI container should have register_services function."""
    import core.di as di
    assert hasattr(di, "register_services"), "No register_services in DI container"
    assert hasattr(di, "resolve"), "No resolve function in DI container"


# Phase 3.2: OTel wired in lifespan
def test_otel_wired():
    """Lifespan should set up OpenTelemetry if enabled."""
    import api.main as api_module
    source = inspect.getsource(api_module.lifespan)
    assert "setup_otel_tracing" in source or "enable_tracing" in source, \
        "OpenTelemetry not wired in lifespan"


# Phase 4.2: LLM-based branching
def test_branching_uses_llm():
    """Branching should try LLM decomposition first."""
    from agents.orchestration import OrchestrationEngine
    source = inspect.getsource(OrchestrationEngine)
    assert "_decompose_query_branches" in source
    # Check that it's async and tries LLM
    assert "extract_json_from_response" in source or "llm" in source.lower(), \
        "Branching doesn't use LLM"


# Phase 4.3: LLM-based recursive
def test_recursive_uses_llm():
    """Recursive mode should try LLM sub-query extraction."""
    from agents.orchestration import OrchestrationEngine
    source = inspect.getsource(OrchestrationEngine)
    assert "_extract_sub_queries" in source
    # Check for LLM usage in the method
    extract_method = source[source.index("_extract_sub_queries"):]
    assert "llm" in extract_method.lower() or "router" in extract_method.lower(), \
        "Recursive sub-query extraction doesn't use LLM"


# Phase 4.4: LLM-based planner
def test_planner_uses_llm():
    """Planner should try LLM-based planning first."""
    from agents.planner import PlannerAgent
    source = inspect.getsource(PlannerAgent)
    assert "_llm_plan" in source, "No _llm_plan method in PlannerAgent"


# Phase 4.5: Validator LLM faithfulness
def test_validator_llm_faithfulness():
    """Validator should have LLM-based faithfulness check."""
    from agents.validator import ValidatorAgent
    source = inspect.getsource(ValidatorAgent)
    assert "_llm_faithfulness_check" in source, \
        "No LLM faithfulness check in validator"


# Phase 5.1: Shared cypher utils
def test_cypher_utils_exists():
    """core/cypher_utils.py should exist with shared utilities."""
    from core.cypher_utils import safe_identifier, validate_int
    assert safe_identifier("valid_name") == "valid_name"
    assert validate_int(5, "test", 1, 10) == 5


# Phase 5.2: Unified embedding providers
def test_docs_uses_shared_embedder():
    """retrieval/docs.py should use EmbeddingPipeline, not its own providers."""
    import retrieval.docs as docs
    source = inspect.getsource(docs.QdrantDocsBackend.search)
    assert "get_embedding_pipeline" in source or "_embedder" in source, \
        "Docs retriever doesn't use shared EmbeddingPipeline"


# Phase 6.3: Version centralized
def test_version_file_exists():
    """__version__.py should exist with version string."""
    from __version__ import __version__
    assert __version__ == "5.0.0"


# Phase 6.1-6.2: Externalized URLs and timeouts
def test_externalized_config():
    """Config should have externalized API URLs and centralized timeouts."""
    from core.config import get_settings
    s = get_settings()
    assert hasattr(s, "openai_api_url"), "No openai_api_url setting"
    assert hasattr(s, "dashscope_api_url"), "No dashscope_api_url setting"
    assert hasattr(s, "openrouter_api_url"), "No openrouter_api_url setting"
    assert hasattr(s, "timeout_health_check"), "No timeout_health_check setting"
    assert hasattr(s, "timeout_llm"), "No timeout_llm setting"
    assert hasattr(s, "max_request_body_size"), "No max_request_body_size setting"
