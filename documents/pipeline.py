"""
Document Pipeline - Document ingestion orchestration.

Coordinates upload → parse → index with versioning
and job tracking.
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from documents.models import Document, DocumentSource, DocumentFormat, DocumentStatus
from documents.parse import HybridDocumentParser as DocumentParser, get_document_parser
from documents.confluence import ConfluenceClient, get_confluence_client
from documents.webdav import WebDAVClient, get_webdav_client
from documents.multimodal import (
    HybridMultimodalParser as MultimodalParser,
    get_multimodal_parser,
)


class DocumentJobStatus(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DocumentJob:
    job_id: str
    document_id: str
    source: DocumentSource
    status: DocumentJobStatus = DocumentJobStatus.PENDING
    content: str = ""
    parsed: bool = False
    indexed: bool = False
    version_number: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def progress(self) -> float:
        if self.status == DocumentJobStatus.COMPLETED:
            return 1.0
        elif self.status == DocumentJobStatus.FAILED:
            return 0.0
        elif self.status == DocumentJobStatus.PENDING:
            return 0.0
        elif self.status == DocumentJobStatus.PARSING:
            return 0.5
        elif self.status == DocumentJobStatus.INDEXING:
            return 0.8
        return 0.0


class DocumentPipeline:
    def __init__(
        self,
        parser: Optional[DocumentParser] = None,
        confluence: Optional[ConfluenceClient] = None,
        webdav: Optional[WebDAVClient] = None,
        multimodal: Optional[MultimodalParser] = None,
    ):
        self.parser = parser or get_document_parser()
        self.confluence = confluence or get_confluence_client()
        self.webdav = webdav or get_webdav_client()
        self.multimodal = multimodal or get_multimodal_parser()
        self._documents: Dict[str, Document] = {}
        self._jobs: Dict[str, DocumentJob] = {}

    async def upload_document(
        self,
        content: bytes,
        filename: str,
        title: Optional[str] = None,
        create_version: bool = False,
        changelog: Optional[str] = None,
    ) -> Document:
        doc = Document.create(
            title=title or filename,
            source=DocumentSource.UPLOAD,
            format=self.parser.detect_format(filename, content),
        )

        parsed = self.parser.parse(content, filename, {"document_id": doc.document_id})

        doc.content = parsed.content
        doc.status = DocumentStatus.PROCESSED

        if create_version and doc.document_id in self._documents:
            existing = self._documents[doc.document_id]
            existing.create_version(parsed.content, changelog)
        else:
            self._documents[doc.document_id] = doc

        return doc

    async def upload_multiple(
        self,
        files: List[tuple],
    ) -> List[Document]:
        documents = []
        for content, filename in files:
            doc = await self.upload_document(content, filename)
            documents.append(doc)
        return documents

    async def sync_confluence_space(
        self,
        space_key: str,
        include_children: bool = True,
        max_depth: int = 3,
    ) -> List[Document]:
        pages = await self.confluence.sync_space(space_key, include_children, max_depth)

        documents = []

        for page in pages:
            doc = Document.create(
                title=page.title,
                source=DocumentSource.CONFLUENCE,
                source_id=page.page_id,
                source_url=page.url,
                format=DocumentFormat.HTML,
            )
            doc.content = page.content
            doc.status = DocumentStatus.PROCESSED

            self._documents[doc.document_id] = doc
            documents.append(doc)

            for child in page.children:
                child_doc = Document.create(
                    title=child.title,
                    source=DocumentSource.CONFLUENCE,
                    source_id=child.page_id,
                    format=DocumentFormat.HTML,
                )
                child_doc.content = child.content
                child_doc.status = DocumentStatus.PROCESSED

                self._documents[child_doc.document_id] = child_doc
                documents.append(child_doc)

        return documents

    async def sync_confluence_pages(
        self,
        page_ids: List[str],
        include_children: bool = False,
    ) -> List[Document]:
        pages = await self.confluence.sync_pages(page_ids, include_children)

        documents = []

        for page in pages:
            doc = Document.create(
                title=page.title,
                source=DocumentSource.CONFLUENCE,
                source_id=page.page_id,
                format=DocumentFormat.HTML,
            )
            doc.content = page.content
            doc.status = DocumentStatus.PROCESSED

            self._documents[doc.document_id] = doc
            documents.append(doc)

        return documents

    async def sync_webdav(
        self,
        path: str = "/",
        extensions: Optional[List[str]] = None,
    ) -> List[Document]:
        contents = await self.webdav.download_folder(path, extensions)

        documents = []

        for file_path, content in contents.items():
            filename = file_path.split("/")[-1]

            doc = Document.create(
                title=filename,
                source=DocumentSource.WEBDAV,
                source_id=file_path,
                format=self.parser.detect_format(filename, content),
            )

            parsed = self.parser.parse(
                content, filename, {"document_id": doc.document_id}
            )

            doc.content = parsed.content
            doc.status = DocumentStatus.PROCESSED

            self._documents[doc.document_id] = doc
            documents.append(doc)

        return documents

    async def parse_image(
        self,
        image_url: str,
        title: str,
    ) -> Document:
        result = await self.multimodal.parse_image(image_url)

        doc = Document.create(
            title=title,
            source=DocumentSource.MULTIMODAL,
            source_id=image_url,
            format=DocumentFormat.UNKNOWN,
        )
        doc.content = result.text
        doc.status = DocumentStatus.PROCESSED
        doc.metadata = result.metadata

        self._documents[doc.document_id] = doc
        return doc

    async def parse_image_bytes(
        self,
        image_bytes: bytes,
        title: str,
    ) -> Document:
        result = await self.multimodal.parse_image_bytes(image_bytes)

        doc = Document.create(
            title=title,
            source=DocumentSource.MULTIMODAL,
            format=DocumentFormat.UNKNOWN,
        )
        doc.content = result.text
        doc.status = DocumentStatus.PROCESSED
        doc.metadata = result.metadata

        self._documents[doc.document_id] = doc
        return doc

    def get_document(self, doc_id: str) -> Optional[Document]:
        return self._documents.get(doc_id)

    def get_version(self, doc_id: str, version: int) -> Optional[str]:
        doc = self._documents.get(doc_id)
        if doc:
            v = doc.get_version(version)
            return v.content if v else None
        return None

    def create_version(
        self,
        doc_id: str,
        content: str,
        changelog: Optional[str] = None,
    ) -> bool:
        doc = self._documents.get(doc_id)
        if not doc:
            return False

        doc.create_version(content, changelog)
        return True

    def rollback(self, doc_id: str, version: int) -> bool:
        doc = self._documents.get(doc_id)
        if not doc:
            return False
        return doc.rollback_to(version)

    def list_documents(self, limit: int = 50) -> List[Dict[str, Any]]:
        docs = list(self._documents.values())[-limit:]
        return [
            {
                "document_id": d.document_id,
                "title": d.title,
                "source": d.source.value,
                "format": d.format.value,
                "status": d.status.value,
                "current_version": d.current_version,
                "created_at": d.created_at.isoformat(),
            }
            for d in docs
        ]

    def delete_document(self, doc_id: str) -> bool:
        return self._documents.pop(doc_id, None) is not None


_pipeline: Optional[DocumentPipeline] = None


def get_document_pipeline() -> DocumentPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = DocumentPipeline()
    return _pipeline
