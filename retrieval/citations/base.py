from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class CitationStyle(str, Enum):
    VERBATIM = "verbatim"
    PARENTHETICAL = "parenthetical"
    FOOTNOTE = "footnote"
    HIGHLIGHT = "highlight"
    STRUCTURED = "structured"
    DIAGRAM = "diagram"


@dataclass
class CitationSource:
    source_id: str
    content: str
    source_type: str
    source_name: str
    url: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    page: Optional[int] = None
    chunk_index: Optional[int] = None
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    accessed_at: datetime = field(default_factory=datetime.now)


@dataclass
class Citation:
    id: str
    source: CitationSource
    spans: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class AnnotatedAnswer:
    answer: str
    citations: List[Citation]
    sources: List[CitationSource]
    style: CitationStyle
    metadata: Dict[str, Any] = field(default_factory=dict)
