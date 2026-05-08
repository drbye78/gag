from typing import Any

from pydantic import BaseModel


class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: list[dict[str, Any]]
    metadata: dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    version: str


class ImageExtractionResponse(BaseModel):
    text: str
    metadata: dict[str, Any]


class ReasoningResponse(BaseModel):
    query: str
    answer: str
    reasoning_mode: str
    confidence: float
    steps: list[dict[str, Any]]


class RerankResponse(BaseModel):
    query: str
    results: list[dict[str, Any]]
    reranked: bool


class CitationResponse(BaseModel):
    answer: str
    citations: list[dict[str, Any]]
    sources: list[dict[str, Any]]


class ToolingSearchResponse(BaseModel):
    query: str
    results: Any
    tool: str
    count: int


class CodeGraphResponse(BaseModel):
    query: str
    results: Any
    method: str
    count: int


class CodeGraphIndexResponse(BaseModel):
    source: str
    success: bool
    error: str | None = None
    url: str | None = None
    branch: str | None = None
    filename: str | None = None


class CodeGraphIndexConfluenceSpaceResponse(BaseModel):
    source: str
    space_key: str
    success: bool
    pages_indexed: int = 0
    errors: list[str] = []


class CodeGraphIndexConfluenceTreeResponse(BaseModel):
    source: str
    root_page_id: str
    success: bool
    pages_indexed: int = 0
    attachments_indexed: int = 0


class CodeGraphIndexConfluencePageResponse(BaseModel):
    source: str
    page_id: str
    success: bool
    indexed: bool = False
    attachments_count: int = 0
    children_count: int = 0


class ColPALSearchResponse(BaseModel):
    query: str
    results: Any
    method: str = "colpal"
    count: int


class UISketchSearchResponse(BaseModel):
    results: Any
    method: str = "ui_sketch"
    count: int


class DiagramExtractResponse(BaseModel):
    diagram_id: str
    diagram_type: str
    title: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    extraction_confidence: float


class DiagramSearchResponse(BaseModel):
    results: list[dict[str, Any]]
    count: int


class EntityCacheStatsResponse(BaseModel):
    size: int
    capacity: int
    hit_rate: float
    hits: int
    misses: int
    utilization_pct: float
    oldest_entry: dict[str, Any] | None


class EntityCacheInvalidateResponse(BaseModel):
    invalidated: bool
    entity_name: str | None = None
    message: str
