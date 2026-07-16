from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    CONCEPT = "concept"
    EVENT = "event"
    LOCATION = "location"
    PRODUCT = "product"
    TECHNOLOGY = "technology"
    DOCUMENT = "document"
    PROCESS = "process"


@dataclass
class ExtractedEntity:
    id: str
    name: str
    entity_type: EntityType
    description: str
    mentions: List[Dict[str, Any]] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityExtractionResult:
    source_id: str
    entities: List[ExtractedEntity]
    total_entities: int
    took_ms: int


class DocumentEntityExtractor:
    def __init__(
        self,
        llm_client: Optional[Any] = None,
        batch_size: int = 10,
    ):
        self.llm_client = llm_client
        self.batch_size = batch_size

    async def extract(self, text: str, source_id: str) -> EntityExtractionResult:
        import time

        start = time.time()

        if not self.llm_client:
            from llm.router import get_llm_router

            self.llm_client = get_llm_router()

        chunks = self._split_for_extraction(text)
        all_entities = []

        for chunk in chunks:
            entities = await self._extract_from_chunk(chunk, source_id)
            all_entities.extend(entities)

        merged = self._merge_entities(all_entities)

        took = int((time.time() - start) * 1000)
        return EntityExtractionResult(
            source_id=source_id,
            entities=merged,
            total_entities=len(merged),
            took_ms=took,
        )

    def _split_for_extraction(self, text: str, max_tokens: int = 2000) -> List[str]:
        words = text.split()
        chunks = []
        current = []
        current_len = 0

        for word in words:
            if current_len + len(word) + 1 > max_tokens * 4:
                if current:
                    chunks.append(" ".join(current))
                    current = [word]
                    current_len = len(word)
            else:
                current.append(word)
                current_len += len(word) + 1

        if current:
            chunks.append(" ".join(current))

        return chunks if chunks else [text]

    async def _extract_from_chunk(
        self, chunk: str, source_id: str
    ) -> List[ExtractedEntity]:
        prompt = f"""Extract named entities from the following text. 
Return a JSON array of objects with fields: name, type, description.

Entity types: person, organization, concept, event, location, product, technology, document, process

Text:
{chunk[:3000]}

Return JSON:"""

        try:
            response = await self.llm_client.chat(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.1,
            )

            # If parsing fails, retry with a "return only JSON" reprompt
            entities = self._parse_llm_response(response)
            if not entities:
                logger.info("First entity extraction returned no entities, retrying with JSON-only prompt")
                retry_prompt = prompt + "\n\nIMPORTANT: Return ONLY a valid JSON array. No prose, no markdown fences, no code blocks."
                response = await self.llm_client.chat(
                    prompt=retry_prompt,
                    max_tokens=2000,
                    temperature=0.0,
                )
                entities = self._parse_llm_response(response)

            for e in entities:
                e.id = f"{source_id}:{e.name.lower().replace(' ', '_')}"
                e.mentions = [{"chunk": chunk[:500], "source_id": source_id}]

            return entities

        except Exception as e:
            logger.warning("Entity extraction failed for %s: %s", source_id, e)
            return []

    def _parse_llm_response(self, response: Any) -> List[ExtractedEntity]:
        """Parse LLM response into entities. Handles markdown fences and retries."""
        from core.llm_utils import extract_json_from_response

        data = extract_json_from_response(response)
        if data is None:
            logger.warning("Failed to parse LLM response as JSON, returning empty entities")
            return []

        if not isinstance(data, list):
            return []

        entities = []
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                entity_type = EntityType(item.get("type", "concept").lower())
            except ValueError:
                entity_type = EntityType.CONCEPT

            entities.append(
                ExtractedEntity(
                    id="",
                    name=item.get("name", ""),
                    entity_type=entity_type,
                    description=item.get("description", ""),
                )
            )

        return entities

    def _merge_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        merged = {}

        for entity in entities:
            key = f"{entity.name.lower()}:{entity.entity_type.value}"

            if key in merged:
                merged[key].mentions.extend(entity.mentions)
                if entity.description and not merged[key].description:
                    merged[key].description = entity.description
            else:
                merged[key] = entity

        return list(merged.values())


class LightweightEntityExtractor:
    def __init__(self):
        pass

    def extract(self, text: str, source_id: str) -> EntityExtractionResult:
        import time
        import re
        from collections import defaultdict

        start = time.time()

        person_pattern = r"\b[A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"
        org_pattern = r"\b(?:Corp|Inc|LLC|Ltd|Company|Group|Team|Department)\b"
        tech_pattern = r"\b(?:API|SDK|CLI|JVM|Kubernetes|Docker|AWS|GCP|Azure)\b"

        entities = []

        for match in re.finditer(person_pattern, text):
            entities.append(
                ExtractedEntity(
                    id=f"{source_id}:person_{match.group()}",
                    name=match.group(),
                    entity_type=EntityType.PERSON,
                    description="",
                    mentions=[
                        {
                            "position": match.start(),
                            "context": text[
                                max(0, match.start() - 50) : match.end() + 50
                            ],
                        }
                    ],
                )
            )

        for match in re.finditer(org_pattern, text):
            entities.append(
                ExtractedEntity(
                    id=f"{source_id}:org_{match.group()}",
                    name=match.group(),
                    entity_type=EntityType.ORGANIZATION,
                    description="",
                    mentions=[
                        {
                            "position": match.start(),
                            "context": text[
                                max(0, match.start() - 50) : match.end() + 50
                            ],
                        }
                    ],
                )
            )

        for match in re.finditer(tech_pattern, text):
            entities.append(
                ExtractedEntity(
                    id=f"{source_id}:tech_{match.group()}",
                    name=match.group(),
                    entity_type=EntityType.TECHNOLOGY,
                    description="",
                    mentions=[
                        {
                            "position": match.start(),
                            "context": text[
                                max(0, match.start() - 50) : match.end() + 50
                            ],
                        }
                    ],
                )
            )

        took = int((time.time() - start) * 1000)
        return EntityExtractionResult(
            source_id=source_id,
            entities=entities[:50],
            total_entities=len(entities),
            took_ms=took,
        )


def get_entity_extractor(use_llm: bool = False) -> Any:
    if use_llm:
        return DocumentEntityExtractor()
    return LightweightEntityExtractor()
