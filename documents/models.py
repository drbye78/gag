"""
Documents Models - Document schemas with versioning.

Provides Document and DocumentVersion models
with source tracking and metadata.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from core.text_utils import detect_language, TextLanguage


class DocumentSource(str, Enum):
    UPLOAD = "upload"
    CONFLUENCE = "confluence"
    WEBDAV = "webdav"
    URL = "url"
    MULTIMODAL = "multimodal"


class DocumentFormat(str, Enum):
    TXT = "txt"
    MD = "md"
    HTML = "html"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    PDF = "pdf"
    JSON = "json"
    UNKNOWN = "unknown"


class DocumentStatus(str, Enum):
    DRAFT = "draft"
    PROCESSING = "processing"
    PROCESSED = "processed"
    INDEXED = "indexed"
    FAILED = "failed"


@dataclass
class DocumentMetadata:
    """Extended document metadata."""

    author: Optional[str] = None
    created_at: Optional[str] = None
    modified_at: Optional[str] = None
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    language: Optional[str] = None
    title: Optional[str] = None
    subject: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    custom: Dict[str, Any] = field(default_factory=dict)


class DocumentVersion(BaseModel):
    """Version model for documents."""

    version_id: str
    document_id: str
    version_number: int
    content: str
    content_hash: str
    format: DocumentFormat
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    changelog: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Document(BaseModel):
    """Main document model."""

    document_id: str
    title: str
    source: DocumentSource
    source_id: Optional[str] = None
    source_url: Optional[str] = None

    format: DocumentFormat
    current_version: int = 1
    status: DocumentStatus = DocumentStatus.DRAFT

    content: str = ""
    content_hash: str = ""

    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    versions: List[DocumentVersion] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    indexed_at: Optional[datetime] = None
    embedding_ids: List[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        title: str,
        source: DocumentSource,
        content: str = "",
        format: DocumentFormat = DocumentFormat.UNKNOWN,
        source_id: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> "Document":
        doc_id = str(uuid.uuid4())[:8]
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        detected_lang = ""
        if content:
            lang = detect_language(content)
            detected_lang = lang.value if lang else ""

        metadata = {"language": detected_lang} if detected_lang else {}

        return cls(
            document_id=doc_id,
            title=title,
            source=source,
            source_id=source_id,
            source_url=source_url,
            format=format,
            content=content,
            content_hash=content_hash,
            metadata=metadata,
        )

    def create_version(
        self,
        content: str,
        changelog: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> DocumentVersion:
        self.current_version += 1

        new_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        version = DocumentVersion(
            version_id=f"{self.document_id}:v{self.current_version}",
            document_id=self.document_id,
            version_number=self.current_version,
            content=content,
            content_hash=new_hash,
            format=self.format,
            created_by=created_by,
            changelog=changelog,
        )

        self.versions.append(version)
        self.content = content
        self.content_hash = new_hash
        self.updated_at = datetime.utcnow()

        return version

    def get_version(self, version: int) -> Optional[DocumentVersion]:
        for v in self.versions:
            if v.version_number == version:
                return v
        return None

    def rollback_to(self, version: int) -> bool:
        version = self.get_version(version)
        if not version:
            return False

        self.content = version.content
        self.content_hash = version.content_hash
        self.updated_at = datetime.utcnow()

        return True


class DocumentCollection(BaseModel):
    """Collection of documents."""

    collection_id: str
    name: str
    description: Optional[str] = None
    documents: List[Document] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def add_document(self, doc: Document):
        self.documents.append(doc)
        self.updated_at = datetime.utcnow()

    def get_document(self, doc_id: str) -> Optional[Document]:
        for doc in self.documents:
            if doc.document_id == doc_id:
                return doc
        return None

    @property
    def document_count(self) -> int:
        return len(self.documents)
