"""
Entity-Aware Reasoning Module.

Provides reasoning capabilities that leverage entity graphs and
relationship information for context-aware answer synthesis.
"""

from retrieval.reasoning.entity_aware import (
    EntityAwareReasoningEngine,
    GraphPathType,
    EntityRelation,
)

_reasoning_engine_module = None


def _get_reasoning_engine_module():
    global _reasoning_engine_module
    if _reasoning_engine_module is None:
        import retrieval.reasoning as _module

        _reasoning_engine_module = _module
    return _reasoning_engine_module


class ReasoningMode:
    DIRECT = "direct"
    CHAIN_OF_THOUGHTS = "chain_of_thoughts"
    TREE_OF_THOUGHTS = "tree_of_thoughts"
    REFLECT = "reflect"
    CRITIQUE = "critique"


class ReasoningEngine:
    def __init__(self, mode=ReasoningMode.CHAIN_OF_THOUGHTS):
        self.mode = mode


def get_reasoning_engine(mode=ReasoningMode.CHAIN_OF_THOUGHTS):
    return ReasoningEngine(mode=mode)


__all__ = [
    "EntityAwareReasoningEngine",
    "GraphPathType",
    "EntityRelation",
    "ReasoningEngine",
    "ReasoningMode",
    "get_reasoning_engine",
]
