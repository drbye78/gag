"""Register all built-in agents with the registry."""

from agents.registry import register_agent
from agents.types import AgentType, AgentMeta
from agents import (
    PlannerAgent,
    RetrievalAgent,
    ReasoningAgent,
    ToolExecutor,
    OrchestrationEngine,
)


@register_agent(
    AgentType.PLANNER,
    AgentMeta(
        agent_type=AgentType.PLANNER,
        name="PlannerAgent",
        description="Plans execution strategies for complex tasks",
        capabilities=["intent_classification", "task_decomposition", "step_ordering"],
    ),
)
def create_planner(**config):
    return PlannerAgent()


@register_agent(
    AgentType.RETRIEVAL,
    AgentMeta(
        agent_type=AgentType.RETRIEVAL,
        name="RetrievalAgent",
        description="Retrieves relevant context from multiple sources",
        capabilities=["semantic_search", "hybrid_search", "graph_retrieval"],
    ),
)
def create_retrieval(**config):
    return RetrievalAgent()


@register_agent(
    AgentType.REASONING,
    AgentMeta(
        agent_type=AgentType.REASONING,
        name="ReasoningAgent",
        description="Performs reasoning and analysis on retrieved context",
        capabilities=["chain_of_thought", "entity_extraction", "causal_analysis"],
    ),
)
def create_reasoning(**config):
    return ReasoningAgent()


@register_agent(
    AgentType.EXECUTOR,
    AgentMeta(
        agent_type=AgentType.EXECUTOR,
        name="ToolExecutor",
        description="Executes tools and returns results",
        capabilities=["tool_selection", "parallel_execution", "error_handling"],
    ),
)
def create_executor(**config):
    return ToolExecutor()


@register_agent(
    AgentType.ORCHESTRATION,
    AgentMeta(
        agent_type=AgentType.ORCHESTRATION,
        name="OrchestrationEngine",
        description="Coordinates multi-agent workflows",
        capabilities=["agent_spawning", "state_management", "result_aggregation"],
    ),
)
def create_orchestration(**config):
    return OrchestrationEngine()
