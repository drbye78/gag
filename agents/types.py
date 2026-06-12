"""Agent types for centralized registry."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AgentType(str, Enum):
    PLANNER = "planner"
    RETRIEVAL = "retrieval"
    REASONING = "reasoning"
    EXECUTOR = "executor"
    ORCHESTRATION = "orchestration"


class AgentConfig(BaseModel):
    agent_type: AgentType
    name: Optional[str] = None
    config: Dict[str, Any] = {}


class AgentMeta(BaseModel):
    agent_type: AgentType
    name: str
    description: str
    capabilities: List[str]
