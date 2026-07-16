"""Centralized agent registry."""

from typing import Dict, Callable, List, Optional
from agents.types import AgentType, AgentConfig, AgentMeta


class AgentRegistry:
    def __init__(self):
        self._factories: Dict[AgentType, Callable] = {}
        self._metadata: Dict[AgentType, AgentMeta] = {}

    def register(self, agent_type: AgentType, factory: Callable, meta: AgentMeta):
        self._factories[agent_type] = factory
        self._metadata[agent_type] = meta

    def get_factory(self, agent_type: AgentType) -> Callable:
        if agent_type not in self._factories:
            raise KeyError(f"No agent registered for type: {agent_type}")
        return self._factories[agent_type]

    def create(self, config: AgentConfig):
        factory = self.get_factory(config.agent_type)
        return factory(**config.config)

    def list_agents(self) -> List[AgentMeta]:
        return list(self._metadata.values())

    def get_meta(self, agent_type: AgentType) -> Optional[AgentMeta]:
        return self._metadata.get(agent_type)


_registry = AgentRegistry()


def get_agent(agent_type: AgentType, **kwargs):
    return _registry.create(AgentConfig(agent_type=agent_type, config=kwargs))


def list_agents() -> List[AgentMeta]:
    return _registry.list_agents()


def get_agent_meta(agent_type: AgentType) -> Optional[AgentMeta]:
    return _registry.get_meta(agent_type)


def register_agent(agent_type: AgentType, meta: AgentMeta):
    def decorator(factory: Callable):
        _registry.register(agent_type, factory, meta)
        return factory
    return decorator
