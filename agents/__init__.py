"""
Agents Module - Agent system components.

Exports: PlannerAgent, RetrievalAgent, ReasoningAgent,
ToolExecutor, OrchestrationEngine, ValidatorAgent, and system prompts.

All imports are lazy to avoid cascading dependency loading.
"""

# Lazy imports — only load when actually accessed
from agents.types import AgentType, AgentConfig, AgentMeta

__all__ = [
    "PlannerAgent", "ExecutionPlan", "ExecutionStep",
    "RetrievalAgent", "RetrievalStrategy", "RetrievalResult",
    "ReasoningAgent", "ReasonMode",
    "ToolExecutor", "ToolStatus", "ToolResult",
    "OrchestrationEngine", "ExecutionState",
    "ValidatorAgent", "ValidationResult", "ValidationIssue",
    "get_agent", "list_agents", "register_agent", "AgentRegistry",
    "AgentType", "AgentConfig", "AgentMeta",
]

def __getattr__(name):
    """Lazy-load agent components on first access."""
    if name in ("PlannerAgent", "ExecutionPlan", "ExecutionStep"):
        from agents.planner import PlannerAgent, ExecutionPlan, ExecutionStep
        return locals()[name]
    if name in ("RetrievalAgent", "RetrievalStrategy", "RetrievalResult"):
        from agents.retrieval import RetrievalAgent, RetrievalStrategy, RetrievalResult
        return locals()[name]
    if name in ("ReasoningAgent", "ReasonMode"):
        from agents.reasoning import ReasoningAgent, ReasonMode
        return locals()[name]
    if name in ("ToolExecutor", "ToolStatus", "ToolResult"):
        from agents.executor import ToolExecutor, ToolStatus, ToolResult
        return locals()[name]
    if name in ("OrchestrationEngine", "ExecutionState"):
        from agents.orchestration import OrchestrationEngine, ExecutionState
        return locals()[name]
    if name in ("ValidatorAgent", "ValidationResult", "ValidationIssue"):
        from agents.validator import ValidatorAgent, ValidationResult, ValidationIssue
        return locals()[name]
    if name in ("get_agent", "list_agents", "register_agent", "AgentRegistry"):
        from agents.registry import get_agent, list_agents, register_agent, AgentRegistry
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _ensure_agents_registered():
    """Lazily register built-in agents. Called from OrchestrationEngine.__init__."""
    import agents._register  # noqa: F401
