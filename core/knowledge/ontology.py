from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class EntityRole(str, Enum):
    SUBJECT = "subject"
    OBJECT = "object"
    ACTION = "action"
    CONSTRAINT = "constraint"
    QUALIFIER = "qualifier"


class IntentType(str, Enum):
    DESIGN = "design"
    ANALYZE = "analyze"
    TROUBLESHOOT = "troubleshoot"
    MIGRATE = "migrate"
    OPTIMIZE = "optimize"
    EXPLAIN = "explain"


class ExtractedEntity(BaseModel):
    id: str = Field(...)
    name: str = Field(...)
    type: str = Field(...)
    role: EntityRole = Field(EntityRole.SUBJECT)
    confidence: float = Field(ge=0.0, le=1.0)
    relationships: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)


class QueryIntent(BaseModel):
    primary: IntentType = Field(...)
    confidence: float = Field(ge=0.0, le=1.0)
    secondary: List[IntentType] = Field(default_factory=list)
    entities: List[ExtractedEntity] = Field(default_factory=list)
    quality_requirements: Dict[str, Any] = Field(default_factory=dict)


class IRFeatureV2(BaseModel):
    intent: QueryIntent = Field(...)
    platforms: List[ExtractedEntity] = Field(default_factory=list)
    services: List[ExtractedEntity] = Field(default_factory=list)
    technologies: List[ExtractedEntity] = Field(default_factory=list)
    patterns: List[ExtractedEntity] = Field(default_factory=list)
    performance_requirements: Dict[str, Any] = Field(default_factory=dict)
    security_requirements: Dict[str, Any] = Field(default_factory=dict)
    scalability_requirements: Dict[str, Any] = Field(default_factory=dict)
    raw_query: str = Field("")

    @property
    def all_entities(self) -> List[ExtractedEntity]:
        return self.platforms + self.services + self.technologies + self.patterns
