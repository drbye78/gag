from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HandlerResult:
    success: bool
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Handler(ABC):
    @abstractmethod
    async def handle(
        self, content: bytes, source_id: str, metadata: Dict[str, Any]
    ) -> HandlerResult:
        pass


@dataclass
class Chunk:
    id: str
    content: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: Dict[str, Any] = field(default_factory=dict)
