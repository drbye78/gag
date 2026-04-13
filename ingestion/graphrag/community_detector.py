from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json


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


class CommunityDetector:
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

        communities = self._build_communities(entities, relationships)

        for community in communities:
            await self._generate_summary(community)

        took = int((time.time() - start) * 1000)
        return CommunityDetectionResult(
            communities=communities,
            total_communities=len(communities),
            took_ms=took,
        )

    def _build_communities(
        self,
        entities: List[Any],
        relationships: List[Any],
    ) -> List[Community]:
        adjacency = {e.id: set() for e in entities}

        for rel in relationships:
            if rel.source_id in adjacency and rel.target_id in adjacency:
                adjacency[rel.source_id].add(rel.target_id)
                adjacency[rel.target_id].add(rel.source_id)

        visited = set()
        communities = []

        def bfs(start_id: str) -> List[str]:
            queue = [start_id]
            component = []
            visited.add(start_id)

            while queue:
                node = queue.pop(0)
                component.append(node)

                for neighbor in adjacency[node]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            return component

        for entity in entities:
            if entity.id not in visited:
                component = bfs(entity.id)

                if len(component) >= 2:
                    key_entities = [
                        entities[0].name for e in component[:5] if e == entities[0].id
                    ]
                    for e in entities:
                        if e.id in component:
                            key_entities.append(e.name)
                            if len(key_entities) >= 5:
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

    async def _generate_summary(self, community: Community) -> None:
        prompt = f"""Generate a brief summary (2-3 sentences) for this community of entities.

Entities: {", ".join(community.key_entities[:10])}

Summary:"""

        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                max_tokens=200,
                temperature=0.3,
            )
            community.summary = response.text.strip()
        except Exception:
            community.summary = f"Community with {len(community.entity_ids)} entities"


class LightweightCommunityDetector:
    def __init__(self):
        pass

    def detect(
        self,
        entities: List[Any],
        relationships: List[Any],
    ) -> CommunityDetectionResult:
        import time

        start = time.time()

        type_groups = {}
        for entity in entities:
            if entity.entity_type.value not in type_groups:
                type_groups[entity.entity_type.value] = []
            type_groups[entity.entity_type.value].append(entity.id)

        communities = []
        for etype, eids in type_groups.items():
            if len(eids) >= 2:
                communities.append(
                    Community(
                        id=f"community_{etype}",
                        name=f"{etype} cluster",
                        entity_ids=eids,
                        summary=f"Cluster of {len(eids)} {etype} entities",
                        key_entities=[eids[0], eids[-1]]
                        if len(eids) > 1
                        else [eids[0]],
                    )
                )

        took = int((time.time() - start) * 1000)
        return CommunityDetectionResult(
            communities=communities,
            total_communities=len(communities),
            took_ms=took,
        )


def get_community_detector(use_llm: bool = False) -> Any:
    if use_llm:
        return CommunityDetector()
    return LightweightCommunityDetector()
