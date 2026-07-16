"""
Entity-Aware Reasoning - Leverages entity graphs for context-aware reasoning.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class GraphPathType(str, Enum):
    DIRECT = "direct"
    TRANSITIVE = "transitive"
    CYCLIC = "cyclic"
    BI_DIRECTIONAL = "bi_directional"


@dataclass
class EntityRelation:
    source: str
    target: str
    relation_type: str
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityContext:
    entities: Set[str] = field(default_factory=set)
    relations: List[EntityRelation] = field(default_factory=list)
    graph_paths: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class ReasoningStepEnhanced:
    step_id: str
    thought: str
    action: str
    observation: str
    score: float = 0.0
    entities_involved: List[str] = field(default_factory=list)
    graph_paths_used: List[str] = field(default_factory=list)
    children: List["ReasoningStepEnhanced"] = field(default_factory=list)
    parent_id: Optional[str] = None


class EntityAwareReasoningEngine:
    def __init__(
        self,
        max_hops: int = 3,
        path_types: Optional[List[GraphPathType]] = None,
    ):
        self.max_hops = max_hops
        default_types: List[GraphPathType] = [
            GraphPathType.DIRECT,
            GraphPathType.TRANSITIVE,
        ]
        self.path_types = path_types if path_types else default_types
        self._entity_cache: Dict[str, EntityContext] = {}
        self._steps: Dict[str, ReasoningStepEnhanced] = {}

    async def reason(
        self,
        query: str,
        retrieved_facts: List[Dict[str, Any]],
        entity_graph: Optional[Dict[str, List[EntityRelation]]] = None,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)

        query_entities = self._extract_entities_from_query(query)
        context = self._build_entity_context(query_entities, entity_graph or {})

        relevant_facts = self._filter_facts_by_entities(retrieved_facts, query_entities)

        graph_paths = self._find_relevant_paths(query_entities, context)

        steps = self._build_reasoning_steps(query, relevant_facts, graph_paths)

        answer = self._synthesize_answer(
            query, relevant_facts, graph_paths, query_entities
        )

        return {
            "query": query,
            "answer": answer,
            "reasoning_mode": "entity_aware",
            "steps": steps,
            "entities": list(query_entities),
            "graph_paths": graph_paths,
            "confidence": self._calculate_confidence(relevant_facts, graph_paths),
            "sources": [f.get("source", "") for f in relevant_facts[:3]],
            "duration_ms": int(time.time() * 1000) - start,
        }

    def _extract_entities_from_query(self, query: str) -> Set[str]:
        entities = set()
        words = query.split()

        for word in words:
            # Remove punctuation for cleaner entity matching
            clean_word = word.rstrip(".,!?;:()[]{}\"'")
            if clean_word and clean_word[0].isupper() and len(clean_word) > 1:
                entities.add(clean_word)

        return entities

    def _build_entity_context(
        self,
        query_entities: Set[str],
        entity_graph: Dict[str, List[EntityRelation]],
    ) -> EntityContext:
        context = EntityContext(entities=query_entities)

        for entity in query_entities:
            if entity in entity_graph:
                context.relations.extend(entity_graph[entity])
                context.graph_paths[entity] = [r.target for r in entity_graph[entity]]

        return context

    def _filter_facts_by_entities(
        self,
        facts: List[Dict[str, Any]],
        entities: Set[str],
    ) -> List[Dict[str, Any]]:
        if not entities:
            return facts[:10]

        filtered = []
        for fact in facts:
            content = fact.get("content", "").lower()
            for entity in entities:
                if entity.lower() in content:
                    filtered.append(fact)
                    break

        return filtered[:10] if filtered else facts[:10]

    def _find_relevant_paths(
        self,
        entities: Set[str],
        context: EntityContext,
    ) -> Dict[str, List[str]]:
        paths = {}

        for entity in entities:
            if entity in context.graph_paths:
                paths[entity] = self._traverse_paths(
                    entity,
                    context.graph_paths,
                    set(),
                    0,
                )

        return paths

    def _traverse_paths(
        self,
        current: str,
        graph: Dict[str, List[str]],
        visited: Set[str],
        depth: int,
    ) -> List[str]:
        if depth >= self.max_hops or current in visited:
            return []

        visited.add(current)
        paths = [current]

        neighbors = graph.get(current, [])
        for neighbor in neighbors[:3]:
            sub_paths = self._traverse_paths(neighbor, graph, visited.copy(), depth + 1)
            if sub_paths:
                paths.extend(sub_paths)

        return paths[: self.max_hops]

    def _build_reasoning_steps(
        self,
        query: str,
        facts: List[Dict[str, Any]],
        graph_paths: Dict[str, List[str]],
    ) -> List[ReasoningStepEnhanced]:
        steps = []

        analyze_step = ReasoningStepEnhanced(
            step_id="0",
            thought=f"Analyzing query: {query}",
            action="analyze",
            observation=f"Identified {len(graph_paths)} graph paths",
        )
        steps.append(analyze_step)

        for i, (entity, paths) in enumerate(graph_paths.items()):
            step = ReasoningStepEnhanced(
                step_id=str(i + 1),
                thought=f"Entity: {entity}",
                action="traverse",
                observation=f"Path length: {len(paths)}",
                entities_involved=[entity],
                graph_paths_used=paths,
                parent_id="0",
            )
            steps.append(step)

        return steps

    def _synthesize_answer(
        self,
        query: str,
        facts: List[Dict[str, Any]],
        graph_paths: Dict[str, List[str]],
        entities: Set[str],
    ) -> str:
        if not facts:
            return "No relevant information found."

        parts = []
        for fact in facts[:3]:
            content = fact.get("content", "")
            if content:
                parts.append(content)

        if parts:
            return " | ".join(parts[:2])

        return "Insufficient information to answer the query."

    def _calculate_confidence(
        self,
        facts: List[Dict[str, Any]],
        graph_paths: Dict[str, List[str]],
    ) -> float:
        fact_score = (
            sum(f.get("score", 0) for f in facts) / max(len(facts), 1) if facts else 0.0
        )

        path_score = (
            (sum(len(p) for p in graph_paths.values())) / max(len(graph_paths), 1) * 0.2
        )

        return min(fact_score + path_score, 1.0)


_entity_aware_engine: Optional[EntityAwareReasoningEngine] = None


def get_entity_aware_reasoning_engine(
    max_hops: int = 3,
) -> EntityAwareReasoningEngine:
    global _entity_aware_engine
    if _entity_aware_engine is None:
        _entity_aware_engine = EntityAwareReasoningEngine(max_hops=max_hops)
    return _entity_aware_engine
