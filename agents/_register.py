"""Register all built-in agents with the registry."""

from agents.executor import ToolExecutor
from agents.orchestration import OrchestrationEngine
from agents.planner import PlannerAgent
from agents.reasoning import ReasoningAgent
from agents.registry import register_agent
from agents.retrieval import RetrievalAgent
from agents.types import AgentMeta, AgentType


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
    return PlannerAgent(**{k: v for k, v in config.items() if k in ("default_sources",)})


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
    return RetrievalAgent(
        **{k: v for k, v in config.items() if k in ("max_sources", "default_limit")}
    )


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
    allowed = {"mode", "max_retries", "temperature"}
    return ReasoningAgent(**{k: v for k, v in config.items() if k in allowed})


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
    allowed = {"max_concurrent", "default_timeout", "max_retries"}
    return ToolExecutor(**{k: v for k, v in config.items() if k in allowed})


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
    allowed = {"max_iterations", "max_retries", "parallel_execution", "orchestration_mode"}
    return OrchestrationEngine(**{k: v for k, v in config.items() if k in allowed})
