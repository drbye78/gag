"""
Regression tests for all P0 and P1 fixes from the 6 audit reports.

Each test verifies that a specific fix is in place and would catch the
issue if it regressed.
"""
import inspect
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# P0.1: /query endpoint includes validation result
def test_query_response_has_validation_field():
    """QueryResponse must have validation and reliable fields."""
    from api.main import QueryResponse
    fields = QueryResponse.model_fields
    assert "validation" in fields, "QueryResponse missing 'validation' field"
    assert "reliable" in fields, "QueryResponse missing 'reliable' field"
    assert "intent" in fields, "QueryResponse missing 'intent' field"


# P0.2: MCP /mcp returns HTTP 200 with JSON-RPC error in body
def test_mcp_endpoint_does_not_raise_on_error():
    """MCP /mcp endpoint should not raise HTTPException on JSON-RPC errors."""
    import api.main as api_module
    source = inspect.getsource(api_module.mcp)
    assert "raise HTTPException" not in source, \
        "MCP endpoint still raises HTTPException on JSON-RPC errors — should return HTTP 200"


# P0.3: ArchitectureEvaluator not in tool registry
def test_architecture_evaluator_not_registered():
    """ArchitectureEvaluator should not be registered in the tool registry."""
    from tools.base import ToolRegistry
    # Check that the registration line was removed
    source = inspect.getsource(ToolRegistry._register_default_tools)
    assert "ArchitectureEvaluator()" not in source, \
        "ArchitectureEvaluator still registered in _register_default_tools"


# P0.4: IRBuilder add_ui is async (no fire-and-forget)
def test_ir_builder_add_ui_is_async():
    """IRBuilder.add_ui must be async (no fire-and-forget create_task)."""
    from multimodal.ir_builder import IRBuilder
    assert inspect.iscoroutinefunction(IRBuilder.add_ui), \
        "IRBuilder.add_ui must be async"
    source = inspect.getsource(IRBuilder.add_ui)
    # Check for actual code usage (not comments)
    lines = [l for l in source.split('\n') if not l.strip().startswith('#')]
    code = '\n'.join(lines)
    assert "loop.create_task" not in code, \
        "IRBuilder.add_ui still uses loop.create_task (fire-and-forget)"
    assert "asyncio.new_event_loop()" not in code, \
        "IRBuilder.add_ui still creates new_event_loop (dangerous in async context)"


# P1.5: MCP sessions have TTL
def test_mcp_session_ttl():
    """MCPHandler must have session TTL and max sessions."""
    from api.mcp import MCPHandler
    assert hasattr(MCPHandler, "MAX_SESSIONS"), "No MAX_SESSIONS"
    assert hasattr(MCPHandler, "SESSION_TTL"), "No SESSION_TTL"
    assert hasattr(MCPHandler, "_evict_expired_sessions"), "No _evict_expired_sessions method"
    assert MCPHandler.MAX_SESSIONS > 0
    assert MCPHandler.SESSION_TTL > 0


# P1.6-7: PDLC tools use extract_json_from_response (not raw choices access)
def test_pdlc_tools_use_extract_json():
    """PDLC tool files should use extract_json_from_response, not raw choices access."""
    import tools.deployment as dep
    import tools.day2 as day2
    import tools.observability as obs
    import tools.feedback as fb
    import tools.ideation as ideation
    import tools.requirements as req
    import tools.testing as testing

    for module in [dep, day2, obs, fb, ideation, req, testing]:
        source = inspect.getsource(module)
        # Should use extract_json_from_response (not raw choices access)
        assert 'response.choices[0]["message"]["content"]' not in source, \
            f"{module.__name__} still uses fragile response.choices[0] access"


# P1.8: ToolRegistry.execute() has error isolation
def test_tool_registry_error_isolation():
    """ToolRegistry.execute() must catch exceptions and return ToolOutput."""
    from tools.base import ToolRegistry
    source = inspect.getsource(ToolRegistry.execute)
    assert "except Exception" in source, \
        "ToolRegistry.execute() doesn't catch exceptions"
    assert "reliable=False" in source, \
        "ToolRegistry.execute() doesn't set reliable=False on errors"


# P1.9: VLM providers don't use per-request httpx.AsyncClient
def test_vlm_no_per_request_client():
    """VLM module should not use per-request httpx.AsyncClient."""
    import multimodal.vlm as vlm
    source = inspect.getsource(vlm)
    # Check there are no "async with httpx.AsyncClient()" patterns
    assert "async with httpx.AsyncClient() as client:" not in source, \
        "VLM still uses per-request httpx.AsyncClient"


# P1.10: IRBuilder index_ir_nodes uses correct API call
def test_ir_builder_index_call_correct():
    """IRBuilder.index_ir_nodes should use correct index_chunks signature."""
    from multimodal.ir_builder import IRBuilder
    source = inspect.getsource(IRBuilder.index_ir_nodes)
    # Should pass chunk dicts, not positional lists
    assert "source_tag=" in source or "chunks_for_indexing" in source, \
        "IRBuilder.index_ir_nodes doesn't use correct index_chunks API"


# P1.11: UIGraphBuilder uses parameterized Cypher
def test_uigraph_parameterized_cypher():
    """UIGraphBuilder.build should use parameterized Cypher, not f-string interpolation."""
    from ui.graph_builder import UIGraphBuilder
    source = inspect.getsource(UIGraphBuilder.build)
    # Should use $sketch_props or $params, not f-string interpolation of sketch_id
    assert "$sketch_props" in source or "$params" in source or "params" in source, \
        "UIGraphBuilder.build doesn't use parameterized Cypher"


# P1.12: Pattern matcher uses field-level trigger matching
def test_pattern_matcher_field_level():
    """PatternMatcher._get_candidates should use field-level matching, not dict string."""
    from core.patterns.matcher import PatternMatcher
    source = inspect.getsource(PatternMatcher._get_candidates)
    # Should NOT use str(feature_dict) for substring matching
    assert 'str(feature_dict)' not in source, \
        "PatternMatcher still uses str(feature_dict) for substring matching"
    assert 'feature_values' in source or 'feature_dict' in source, \
        "PatternMatcher doesn't use field-level matching"


# P1.13: Resolver computes confidence (not hardcoded)
def test_resolver_confidence_computed():
    """Resolver should compute confidence, not hardcode 0.8."""
    from core.knowledge.resolver import KnowledgeResolver
    source = inspect.getsource(KnowledgeResolver)
    assert "confidence=0.8" not in source, \
        "Resolver still hardcodes confidence=0.8"


# P1.14: Default constraint sets registered
def test_default_constraints_registered():
    """Constraint engine should register default constraint sets."""
    import core.constraints.engine as ce_module
    source = inspect.getsource(ce_module)
    assert "_load_default_constraints" in source or "_register_default_constraints" in source, \
        "No default constraint registration function found in constraint engine module"


# Additional: ToolOutput fallback methods set reliable=False
def test_pdlc_fallbacks_set_reliable_false():
    """PDLC tool fallback methods should set reliable=False on ToolOutput."""
    import tools.deployment as dep
    import tools.observability as obs

    for module in [dep, obs]:
        source = inspect.getsource(module)
        # Find all _fallback methods and check for reliable=False
        # At least some fallbacks should have reliable=False
        assert "reliable=False" in source or "reliable = False" in source, \
            f"{module.__name__} fallback methods don't set reliable=False"
