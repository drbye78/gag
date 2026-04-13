"""
Retrieval Schema - Multi-source retrieval models.

Defines schemas for documents, code, tickets, and telemetry
with embeddings and metadata.
"""

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class RetrievalSource(str, Enum):
    DOCS = "docs"
    CODE = "code"
    GRAPH = "graph"
    TICKETS = "tickets"
    TELEMETRY = "telemetry"


class SearchType(str, Enum):
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


FloatList = List[float]


class DocumentChunk(BaseModel):
    id: str
    doc_id: str
    content: str
    source: str
    chunk_index: int
    start_char: int
    end_char: int
    embedding: Optional[FloatList]
    metadata: dict
    created_at: datetime


class Document(BaseModel):
    id: str
    title: str
    content: str
    doc_type: str
    url: Optional[str]
    file_path: Optional[str]
    language: Optional[str]
    chunks: List[DocumentChunk]
    metadata: dict
    created_at: datetime
    updated_at: datetime


class CodeChunk(BaseModel):
    id: str
    code_id: str
    entity_name: str
    entity_type: str
    content: str
    file_path: str
    start_line: int
    end_line: int
    language: str
    embedding: Optional[FloatList]
    imports: List[str]
    exports: List[str]
    calls: List[str]
    metadata: dict


class CodeEntity(BaseModel):
    id: str
    name: str
    entity_type: str
    file_path: str
    language: str
    repo_url: Optional[str]
    start_line: Optional[int]
    end_line: Optional[int]
    chunks: List[CodeChunk]
    metadata: dict


class Ticket(BaseModel):
    id: str
    title: str
    description: str
    ticket_type: str
    status: str
    priority: Optional[str]
    assignees: List[str]
    labels: List[str]
    component: Optional[str]
    source_url: Optional[str]
    created_at: datetime
    updated_at: datetime


class TelemetryEvent(BaseModel):
    id: str
    event_type: str
    timestamp: datetime
    service: str
    severity: str
    message: str
    trace_id: Optional[str]
    span_id: Optional[str]
    attributes: dict


class Metric(BaseModel):
    id: str
    name: str
    value: float
    unit: str
    service: str
    timestamp: datetime
    labels: dict


class RetrievalResult(BaseModel):
    source: RetrievalSource
    query: str
    results: List[Any]
    scores: List[float]
    total: int
    took_ms: int
    metadata: dict


class RetrievalRequest(BaseModel):
    query: str
    sources: List[RetrievalSource]
    search_type: SearchType
    limit: int
    filters: dict
    score_threshold: Optional[float]


class MergedRetrievalResult(BaseModel):
    query: str
    results: List[RetrievalResult]
    total_results: int
    took_ms: int

    @property
    def all_documents(self) -> List:
        docs = []
        for r in self.results:
            if r.source == RetrievalSource.DOCS:
                docs.extend(r.results)
        return docs

    @property
    def all_code(self) -> List:
        code = []
        for r in self.results:
            if r.source == RetrievalSource.CODE:
                code.extend(r.results)
        return code
