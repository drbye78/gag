"""
README claim: "30+ tools exposed via Model Context Protocol"
Source: README.md line 128
"""
import pytest
import inspect


@pytest.mark.claim
def test_tool_count_at_least_thirty():
    from tools.base import get_tool_registry
    registry = get_tool_registry()
    tools = registry.list_tools()
    assert len(tools) >= 30, f"Expected 30+ tools, got {len(tools)}"


@pytest.mark.claim
def test_no_fabricated_fallback_methods():
    import tools.day2 as day2_module
    import tools.feedback as feedback_module
    import tools.observability as obs_module

    modules = [day2_module, feedback_module, obs_module]
    fabricated_patterns = []

    for mod in modules:
        source = inspect.getsource(mod)
        lines = source.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "return" in stripped and "{" in stripped:
                hardcoded_indicators = [
                    '"churn_probability": 0.15',
                    "'churn_probability': 0.15",
                    '"action": "scale_up"',
                    "'action': 'scale_up'",
                    '"root_cause": "memory_leak"',
                    "'root_cause': 'memory_leak'",
                    '"http_requests_total": 1000',
                    "'http_requests_total': 1000",
                    '"current": 99.5',
                    "'current': 99.5",
                    '"status": "success"',
                    "'status': 'success'",
                ]
                for pattern in hardcoded_indicators:
                    if pattern in stripped:
                        fabricated_patterns.append(f"{mod.__name__}:{i}: {stripped}")

    assert len(fabricated_patterns) == 0, \
        f"Found {len(fabricated_patterns)} fabricated fallback patterns: {fabricated_patterns[:5]}"
