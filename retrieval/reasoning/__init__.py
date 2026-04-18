"""
Entity-Aware Reasoning Module.

Provides reasoning capabilities that leverage entity graphs and
relationship information for context-aware answer synthesis.
"""

import sys


class ReasoningMode:
    DIRECT = "direct"
    CHAIN_OF_THOUGHTS = "chain_of_thoughts"
    TREE_OF_THOUGHTS = "tree_of_thoughts"
    REFLECT = "reflect"
    CRITIQUE = "critique"


_reasoning_engine_cls = None


def _load_reasoning_engine():
    global _reasoning_engine_cls
    if _reasoning_engine_cls is not None:
        return _reasoning_engine_cls
    
    reasoning_file = None
    for path in sys.path:
        import os
        candidate = os.path.join(path, "retrieval", "reasoning.py")
        if os.path.exists(candidate):
            reasoning_file = candidate
            break
    
    if reasoning_file:
        import importlib.util
        spec = importlib.util.spec_from_file_location("retrieval.reasoning_impl", reasoning_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules["retrieval.reasoning_impl"] = module
        spec.loader.exec_module(module)
        _reasoning_engine_cls = module.ReasoningEngine
        return _reasoning_engine_cls
    
    return None


def get_reasoning_engine(mode=ReasoningMode.CHAIN_OF_THOUGHTS):
    cls = _load_reasoning_engine()
    if cls is None:
        raise RuntimeError("Could not load ReasoningEngine")
    return cls(mode=mode)


def __getattr__(name):
    if name == "ReasoningEngine":
        cls = _load_reasoning_engine()
        if cls is not None:
            return cls
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


from retrieval.reasoning.entity_aware import (
    EntityAwareReasoningEngine,
    GraphPathType,
    EntityRelation,
)


__all__ = [
    "EntityAwareReasoningEngine",
    "GraphPathType",
    "EntityRelation",
    "ReasoningMode",
    "get_reasoning_engine",
]
