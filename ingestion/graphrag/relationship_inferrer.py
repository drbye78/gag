from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from ingestion.graphrag.entity_extractor import EntityType


class RelationshipType(str, Enum):
    RELATED_TO = "related_to"
    PART_OF = "part_of"
    WORKS_FOR = "works_for"
    LOCATED_AT = "located_at"
    USES = "uses"
    DEPENDS_ON = "depends_on"
    CREATED_BY = "created_by"
    DEFINED_IN = "defined_in"
    REFERENCES = "references"
    CONTAINS = "contains"
    IMPLEMENTS = "implements"
    MANAGES = "manages"
    INTERACTS_WITH = "interacts_with"


@dataclass
class Relationship:
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    confidence: float
    context: str
    source_doc: str


@dataclass
class RelationshipInferenceResult:
    source_id: str
    relationships: List[Relationship]
    total_relationships: int
    took_ms: int


class RelationshipInferrer:
    def __init__(
        self,
        llm_client: Optional[Any] = None,
    ):
        self.llm_client = llm_client

    async def infer(
        self,
        entities: List[Any],
        text: str,
        source_id: str,
    ) -> RelationshipInferenceResult:
        import time

        start = time.time()

        if not self.llm_client:
            from llm.router import get_llm_router

            self.llm_client = get_llm_router()

        relationships = []

        entity_pairs = self._create_entity_pairs(entities)

        if len(entity_pairs) <= 20:
            for pair in entity_pairs:
                rel = await self._infer_relationship(pair, text)
                if rel:
                    relationships.append(rel)
        else:
            batches = [
                entity_pairs[i : i + 20] for i in range(0, len(entity_pairs), 20)
            ]
            for batch in batches:
                batch_rels = await self._infer_batch_relationships(batch, text)
                relationships.extend(batch_rels)

        took = int((time.time() - start) * 1000)
        return RelationshipInferenceResult(
            source_id=source_id,
            relationships=relationships,
            total_relationships=len(relationships),
            took_ms=took,
        )

    def _create_entity_pairs(self, entities: List[Any]) -> List[tuple]:
        pairs = []
        for i, e1 in enumerate(entities):
            for e2 in entities[i + 1 : i + 10]:
                pairs.append((e1, e2))
        return pairs[:50]

    async def _infer_relationship(
        self,
        entity_pair: tuple,
        text: str,
    ) -> Optional[Relationship]:
        e1, e2 = entity_pair

        prompt = f"""Analyze the relationship between these two entities in the given text.

Entity 1: {e1.name} (type: {e1.entity_type.value})
Entity 2: {e2.name} (type: {e2.entity_type.value})

Return JSON with:
- relationship_type: one of related_to, part_of, works_for, located_at, uses, depends_on, created_by, defined_in, references, contains, implements, manages, interacts_with
- confidence: 0.0 to 1.0
- context: short explanation

Text excerpt: {text[:1000]}

Return JSON only:"""

        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                max_tokens=500,
                temperature=0.1,
            )

            import json

            data = json.loads(response.text)

            return Relationship(
                source_id=e1.id,
                target_id=e2.id,
                relationship_type=RelationshipType(
                    data.get("relationship_type", "related_to")
                ),
                confidence=data.get("confidence", 0.5),
                context=data.get("context", ""),
                source_doc="",
            )

        except Exception:
            return None

    async def _infer_batch_relationships(
        self,
        entity_pairs: List[tuple],
        text: str,
    ) -> List[Relationship]:
        prompt = f"""Analyze relationships between multiple entity pairs. Return a JSON array.

Entity pairs to analyze:
{chr(10).join([f"- {e1.name} <-> {e2.name}" for e1, e2 in entity_pairs])}

For each pair, identify:
- source: first entity name
- target: second entity name  
- relationship_type: related_to, part_of, works_for, located_at, uses, depends_on, created_by, defined_in, references, contains, implements, manages, interacts_with
- confidence: 0.0 to 1.0
- context: brief explanation

Text: {text[:1500]}

Return JSON array:"""

        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                max_tokens=1500,
                temperature=0.1,
            )

            import json

            data = json.loads(response.text)

            relationships = []
            entity_map = {
                e.name: e.id for e in sum([[p[0], p[1]] for p in entity_pairs], [])
            }

            for item in data:
                source_name = item.get("source", "")
                target_name = item.get("target", "")

                if source_name in entity_map and target_name in entity_map:
                    relationships.append(
                        Relationship(
                            source_id=entity_map[source_name],
                            target_id=entity_map[target_name],
                            relationship_type=RelationshipType(
                                item.get("relationship_type", "related_to")
                            ),
                            confidence=item.get("confidence", 0.5),
                            context=item.get("context", ""),
                            source_doc="",
                        )
                    )

            return relationships

        except Exception:
            return []


class LightweightRelationshipInferrer:
    def __init__(self):
        pass

    def infer(
        self,
        entities: List[Any],
        text: str,
        source_id: str,
    ) -> RelationshipInferenceResult:
        import time
        import re
        from collections import defaultdict

        start = time.time()

        relationships = []

        cooccurrence = defaultdict(lambda: {"count": 0, "contexts": []})

        for i, e1 in enumerate(entities):
            for e2 in entities[i + 1 :]:
                if (
                    e1.entity_type == EntityType.TECHNOLOGY
                    and e2.entity_type == EntityType.TECHNOLOGY
                ):
                    if e1.name in text and e2.name in text:
                        pos1 = text.find(e1.name)
                        pos2 = text.find(e2.name)
                        if abs(pos1 - pos2) < 200:
                            key = (e1.id, e2.id)
                            cooccurrence[key]["count"] += 1
                            cooccurrence[key]["contexts"].append(
                                text[min(pos1, pos2) : min(pos1, pos2) + 100]
                            )

        for (e1_id, e2_id), data in cooccurrence.items():
            if data["count"] >= 1:
                relationships.append(
                    Relationship(
                        source_id=e1_id,
                        target_id=e2_id,
                        relationship_type=RelationshipType.RELATED_TO,
                        confidence=min(0.9, data["count"] * 0.3),
                        context="; ".join(data["contexts"][:2]),
                        source_doc=source_id,
                    )
                )

        took = int((time.time() - start) * 1000)
        return RelationshipInferenceResult(
            source_id=source_id,
            relationships=relationships[:20],
            total_relationships=len(relationships),
            took_ms=took,
        )


def get_relationship_inferrer(use_llm: bool = False) -> Any:
    if use_llm:
        return RelationshipInferrer()
    return LightweightRelationshipInferrer()
