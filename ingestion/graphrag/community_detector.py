from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class Community:
    id: str
    name: str
    entity_ids: List[str]
    summary: str
    key_entities: List[str]
    subgraph: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommunityDetectionResult:
    communities: List[Community]
    total_communities: int
    took_ms: int
    modularity: float = 0.0
    algorithm: str = "louvain"


class CommunityDetector:
    """Detects communities using the Louvain algorithm via python-louvain.

    Falls back to connected-components BFS only if networkx/python-louvain
    are unavailable. The LLM is used only for generating community summaries,
    not for the community detection itself.
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
    ):
        self.llm_client = llm_client

    async def detect(
        self,
        entities: List[Any],
        relationships: List[Any],
    ) -> CommunityDetectionResult:
        import time

        start = time.time()

        if not self.llm_client:
            from llm.router import get_llm_router

            self.llm_client = get_llm_router()

        communities, modularity, algorithm = self._build_communities(entities, relationships)

        for community in communities:
            await self._generate_summary(community)

        took = int((time.time() - start) * 1000)
        return CommunityDetectionResult(
            communities=communities,
            total_communities=len(communities),
            took_ms=took,
            modularity=modularity,
            algorithm=algorithm,
        )

    def _build_communities(
        self,
        entities: List[Any],
        relationships: List[Any],
    ) -> tuple:
        """Build communities using Louvain algorithm.

        Returns:
            Tuple of (communities, modularity_score, algorithm_name)
        """
        try:
            import networkx as nx
            import community as community_louvain
        except ImportError:
            logger.warning(
                "networkx/python-louvain not installed — falling back to "
                "BFS connected components. Install with: pip install networkx python-louvain"
            )
            communities = self._build_communities_bfs_fallback(entities, relationships)
            return communities, 0.0, "bfs_fallback"

        # Build a networkx graph from entities and relationships
        graph = nx.Graph()

        # Add all entity nodes (isolated nodes are included)
        entity_map = {e.id: e for e in entities}
        for entity in entities:
            graph.add_node(entity.id)

        # Add edges from relationships
        for rel in relationships:
            if rel.source_id in entity_map and rel.target_id in entity_map:
                # Use confidence as weight if available, default to 1.0
                weight = getattr(rel, "confidence", 1.0)
                if graph.has_edge(rel.source_id, rel.target_id):
                    # Accumulate weight for multi-edges
                    graph[rel.source_id][rel.target_id]["weight"] += weight
                else:
                    graph.add_edge(rel.source_id, rel.target_id, weight=weight)

        # If no edges, fall back to type-based grouping
        if graph.number_of_edges() == 0:
            communities = self._build_communities_by_type(entities)
            return communities, 0.0, "type_grouping"

        # Run Louvain community detection
        partition = community_louvain.best_partition(graph, weight="weight")

        # Group entities by their community assignment
        community_groups: Dict[int, List[str]] = {}
        for entity_id, comm_id in partition.items():
            community_groups.setdefault(comm_id, []).append(entity_id)

        # Calculate modularity
        modularity = community_louvain.modularity(partition, graph, weight="weight")

        # Build Community objects
        communities = []
        for comm_id, entity_ids in sorted(community_groups.items()):
            if len(entity_ids) < 1:
                continue

            # Get entity names for key entities
            key_entity_names = []
            for eid in entity_ids[:5]:
                entity = entity_map.get(eid)
                if entity:
                    key_entity_names.append(entity.name)

            # Determine a meaningful name from the dominant entity type
            entity_types = [
                entity_map[eid].entity_type.value
                for eid in entity_ids
                if eid in entity_map
            ]
            dominant_type = max(set(entity_types), key=entity_types.count) if entity_types else "mixed"

            communities.append(
                Community(
                    id=f"community_{comm_id}",
                    name=f"{dominant_type.capitalize()} Community {comm_id}",
                    entity_ids=entity_ids,
                    summary="",
                    key_entities=key_entity_names,
                    subgraph={
                        "size": len(entity_ids),
                        "modularity_contribution": modularity / max(len(community_groups), 1),
                    },
                )
            )

        return communities, modularity, "louvain"

    def _build_communities_bfs_fallback(
        self,
        entities: List[Any],
        relationships: List[Any],
    ) -> List[Community]:
        """Fallback: BFS connected components (used only if networkx unavailable)."""
        from collections import deque

        adjacency = {e.id: set() for e in entities}

        for rel in relationships:
            if rel.source_id in adjacency and rel.target_id in adjacency:
                adjacency[rel.source_id].add(rel.target_id)
                adjacency[rel.target_id].add(rel.source_id)

        visited = set()
        communities = []

        for entity in entities:
            if entity.id not in visited:
                # BFS
                queue = deque([entity.id])
                component = []
                visited.add(entity.id)

                while queue:
                    node = queue.popleft()
                    component.append(node)
                    for neighbor in adjacency.get(node, set()):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)

                if len(component) >= 1:
                    key_entities = []
                    for eid in component[:5]:
                        for e in entities:
                            if e.id == eid:
                                key_entities.append(e.name)
                                break

                    communities.append(
                        Community(
                            id=f"community_{len(communities)}",
                            name=f"Community {len(communities)}",
                            entity_ids=component,
                            summary="",
                            key_entities=key_entities,
                        )
                    )

        return communities

    def _build_communities_by_type(
        self,
        entities: List[Any],
    ) -> List[Community]:
        """Group entities by type when no relationships exist."""
        type_groups: Dict[str, List[str]] = {}
        entity_map = {e.id: e for e in entities}

        for entity in entities:
            etype = entity.entity_type.value
            type_groups.setdefault(etype, []).append(entity.id)

        communities = []
        for etype, eids in type_groups.items():
            key_entities = [
                entity_map[eid].name for eid in eids[:5] if eid in entity_map
            ]
            communities.append(
                Community(
                    id=f"community_{etype}",
                    name=f"{etype.capitalize()} cluster",
                    entity_ids=eids,
                    summary="",
                    key_entities=key_entities,
                )
            )

        return communities

    async def _generate_summary(self, community: Community) -> None:
        prompt = f"""Generate a brief summary (2-3 sentences) for this community of entities.

Entities: {", ".join(community.key_entities[:10])}

Summary:"""

        try:
            response = await self.llm_client.chat(
                prompt=prompt,
                max_tokens=200,
                temperature=0.3,
            )
            from core.llm_utils import extract_text
            summary = extract_text(response)
            community.summary = summary if summary else f"Community with {len(community.entity_ids)} entities"
        except Exception:
            community.summary = f"Community with {len(community.entity_ids)} entities"


class LightweightCommunityDetector:
    """Deprecated: use CommunityDetector instead.

    This class is kept for backward compatibility but now delegates to
    the same Louvain-based detection as CommunityDetector.
    """

    def __init__(self):
        pass

    def detect(
        self,
        entities: List[Any],
        relationships: List[Any],
    ) -> CommunityDetectionResult:
        import time

        start = time.time()

        # Use the same Louvain-based detection
        detector = CommunityDetector()
        communities, modularity, algorithm = detector._build_communities(entities, relationships)

        took = int((time.time() - start) * 1000)
        return CommunityDetectionResult(
            communities=communities,
            total_communities=len(communities),
            took_ms=took,
            modularity=modularity,
            algorithm=algorithm,
        )


def get_community_detector(use_llm: bool = False) -> Any:
    if use_llm:
        return CommunityDetector()
    return LightweightCommunityDetector()
