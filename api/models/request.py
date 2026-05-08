import base64
from typing import Any

from pydantic import BaseModel, field_validator


class QueryRequest(BaseModel):
    query: str
    sources: list[str] | None = None
    limit: int | None = 10
    temperature: float | None = None

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must not be empty")
        return v.strip()

    @field_validator("temperature")
    @classmethod
    def temperature_valid(cls, v: float | None) -> float | None:
        if v is not None and (v < 0 or v > 2.0):
            raise ValueError("temperature must be between 0 and 2.0")
        return v


class ImageExtractionRequest(BaseModel):
    image_url: str
    prompt: str | None = "Extract all text from this image"

    @field_validator("image_url")
    @classmethod
    def image_url_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("image_url must not be empty")
        return v.strip()


class ReasoningRequest(BaseModel):
    query: str
    facts: list[dict[str, Any]]
    mode: str | None = "chain_of_thoughts"

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must not be empty")
        return v.strip()


class RerankRequest(BaseModel):
    query: str
    results: list[dict[str, Any]]
    provider: str | None = "cohere"
    strategy: str | None = "single"

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must not be empty")
        return v.strip()


class CitationRequest(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    style: str | None = "parenthetical"

    @field_validator("answer")
    @classmethod
    def answer_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("answer must not be empty")
        return v.strip()


class ToolingSearchRequest(BaseModel):
    query: str
    limit: int | None = 10
    entity_type: str | None = None

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must not be empty")
        return v.strip()


class CodeGraphFindRequest(BaseModel):
    query: str
    fuzzy: bool | None = False
    edit_distance: int | None = 2
    repo_path: str | None = None
    limit: int | None = 10


class CodeGraphRelationshipRequest(BaseModel):
    query_type: str
    target: str
    context: str | None = None
    repo_path: str | None = None


class CodeGraphComplexRequest(BaseModel):
    limit: int | None = 10
    repo_path: str | None = None


class CodeGraphRequest(BaseModel):
    repo_path: str | None = None


class CodeGraphDeadCodeRequest(BaseModel):
    exclude_decorated_with: list[str] | None = []
    repo_path: str | None = None


class CodeGraphVisualizeRequest(BaseModel):
    query_type: str
    node_name: str | None = None


class CodeGraphIndexGitRequest(BaseModel):
    url: str
    branch: str | None = "main"
    depth: int | None = 1


class CodeGraphIndexZipRequest(BaseModel):
    content: str
    filename: str | None = None

    @field_validator("content")
    @classmethod
    def content_size_limit(cls, v: str) -> str:
        max_size = 50 * 1024 * 1024
        decoded = base64.b64decode(v)
        if len(decoded) > max_size:
            raise ValueError(f"Content exceeds maximum size of {max_size // (1024*1024)}MB")
        return v


class CodeGraphIndexURLRequest(BaseModel):
    url: str
    url_type: str | None = "zip"


class CodeGraphIndexMarkdownRequest(BaseModel):
    content: str
    source_name: str | None = "document.md"


class CodeGraphIndexConfluenceRequest(BaseModel):
    base_url: str
    page_id: str
    email: str
    api_token: str


class CodeGraphIndexConfluenceSpaceRequest(BaseModel):
    base_url: str
    space_key: str
    email: str
    api_token: str
    include_children: bool = True
    max_depth: int = 3
    include_attachments: bool = False


class CodeGraphIndexConfluenceTreeRequest(BaseModel):
    base_url: str
    page_id: str
    email: str
    api_token: str
    depth: int = 3
    include_attachments: bool = True


class CodeGraphIndexConfluencePageRequest(BaseModel):
    base_url: str
    page_id: str
    email: str
    api_token: str
    include_attachments: bool = False
    include_children: bool = False
    children_depth: int = 1


class ColPALSearchRequest(BaseModel):
    query: str
    limit: int | None = 10


class UISketchSearchRequest(BaseModel):
    sketch_data: str
    limit: int | None = 10


class DiagramExtractRequest(BaseModel):
    content: str | None = None
    image_url: str | None = None
    source: str | None = None
    enrich: bool = False


class DiagramSearchRequest(BaseModel):
    query: str
    limit: int | None = 10
    diagram_types: list[str] | None = None


class EntityCacheInvalidateRequest(BaseModel):
    entity_name: str | None = None
