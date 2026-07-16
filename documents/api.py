"""
Documents API - FastAPI endpoints for document ingestion.

Provides upload, version, Confluence, WebDAV,
multimodal endpoints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, UploadFile, Depends

from core.auth import require_authenticated

from documents.pipeline import DocumentPipeline, get_document_pipeline
from documents.confluence import get_confluence_client
from documents.webdav import get_webdav_client
from documents.multimodal import (
    HybridMultimodalParser as MultimodalParser,
    get_multimodal_parser,
)


class DocumentResponse(BaseModel):
    document_id: str
    title: str
    source: str
    format: str
    current_version: int
    status: str


class VersionRequest(BaseModel):
    content: str
    changelog: Optional[str] = None


class VersionResponse(BaseModel):
    version_id: str
    version_number: int
    content_hash: str


class ConfluenceSyncRequest(BaseModel):
    space_key: str
    include_children: bool = True
    max_depth: int = 3


class ConfluencePagesRequest(BaseModel):
    page_ids: List[str]
    include_children: bool = False


class WebDAVSyncRequest(BaseModel):
    path: str = "/"
    extensions: Optional[List[str]] = None


class ImageParseRequest(BaseModel):
    image_url: str
    title: Optional[str] = None


router = APIRouter(prefix="/documents", tags=["documents"], dependencies=[Depends(require_authenticated)])


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile,
    title: Optional[str] = None,
):
    pipeline = get_document_pipeline()
    content = await file.read()

    doc = await pipeline.upload_document(
        content=content,
        filename=file.filename or "Untitled",
        title=title or file.filename,
    )

    return DocumentResponse(
        document_id=doc.document_id,
        title=doc.title,
        source=doc.source.value,
        format=doc.format.value,
        current_version=doc.current_version,
        status=doc.status.value,
    )


@router.post("/upload/batch")
async def upload_documents(files: List[UploadFile]):
    pipeline = get_document_pipeline()

    files_data = []
    for f in files:
        content = await f.read()
        files_data.append((content, f.filename or "Untitled"))

    docs = await pipeline.upload_multiple(files_data)

    return {
        "documents": [
            {
                "document_id": d.document_id,
                "title": d.title,
            }
            for d in docs
        ]
    }


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    pipeline = get_document_pipeline()
    doc = pipeline.get_document(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        document_id=doc.document_id,
        title=doc.title,
        source=doc.source.value,
        format=doc.format.value,
        current_version=doc.current_version,
        status=doc.status.value,
    )


@router.get("/{document_id}/content")
async def get_document_content(document_id: str):
    pipeline = get_document_pipeline()
    doc = pipeline.get_document(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "document_id": doc.document_id,
        "content": doc.content,
    }


@router.post("/{document_id}/version", response_model=VersionResponse)
async def create_version(
    document_id: str,
    request: VersionRequest,
):
    pipeline = get_document_pipeline()
    success = pipeline.create_version(
        doc_id=document_id,
        content=request.content,
        changelog=request.changelog,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = pipeline.get_document(document_id)

    return VersionResponse(
        version_id=f"{document_id}:v{doc.current_version}",
        version_number=doc.current_version,
        content_hash=doc.content_hash,
    )


@router.get("/{document_id}/versions")
async def list_versions(document_id: str):
    pipeline = get_document_pipeline()
    doc = pipeline.get_document(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "versions": [
            {
                "version_id": v.version_id,
                "version_number": v.version_number,
                "created_at": v.created_at.isoformat(),
            }
            for v in doc.versions
        ]
    }


@router.get("/{document_id}/versions/{version}")
async def get_version(document_id: str, version: int):
    pipeline = get_document_pipeline()
    content = pipeline.get_version(document_id, version)

    if content is None:
        raise HTTPException(status_code=404, detail="Version not found")

    return {
        "document_id": document_id,
        "version": version,
        "content": content,
    }


@router.post("/{document_id}/rollback/{version}")
async def rollback_version(document_id: str, version: int):
    pipeline = get_document_pipeline()
    success = pipeline.rollback(document_id, version)

    if not success:
        raise HTTPException(status_code=400, detail="Cannot rollback")

    return {"status": "rolled_back", "version": version}


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    pipeline = get_document_pipeline()
    success = pipeline.delete_document(document_id)

    if not success:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"status": "deleted"}


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(limit: int = 50):
    if limit < 1:
        limit = 1
    elif limit > 1000:
        limit = 1000
    pipeline = get_document_pipeline()
    docs = pipeline.list_documents(limit)

    return [DocumentResponse(**d) for d in docs]


@router.post("/confluence/space")
async def sync_confluence_space(request: ConfluenceSyncRequest):
    pipeline = get_document_pipeline()
    docs = await pipeline.sync_confluence_space(
        space_key=request.space_key,
        include_children=request.include_children,
        max_depth=request.max_depth,
    )

    return {
        "synced_count": len(docs),
        "documents": [
            {
                "document_id": d.document_id,
                "title": d.title,
            }
            for d in docs
        ],
    }


@router.post("/confluence/pages")
async def sync_confluence_pages(request: ConfluencePagesRequest):
    pipeline = get_document_pipeline()
    docs = await pipeline.sync_confluence_pages(
        page_ids=request.page_ids,
        include_children=request.include_children,
    )

    return {
        "synced_count": len(docs),
        "documents": [
            {
                "document_id": d.document_id,
                "title": d.title,
            }
            for d in docs
        ],
    }


@router.post("/webdav/sync")
async def sync_webdav(request: WebDAVSyncRequest):
    pipeline = get_document_pipeline()
    docs = await pipeline.sync_webdav(
        path=request.path,
        extensions=request.extensions,
    )

    return {
        "synced_count": len(docs),
        "documents": [
            {
                "document_id": d.document_id,
                "title": d.title,
            }
            for d in docs
        ],
    }


@router.post("/multimodal/image")
async def parse_image(request: ImageParseRequest):
    pipeline = get_document_pipeline()

    title = request.title or "Image Analysis"
    doc = await pipeline.parse_image(request.image_url, title)

    return {
        "document_id": doc.document_id,
        "title": doc.title,
        "content": doc.content,
    }


@router.post("/multimodal/image/base64")
async def parse_image_base64(image: UploadFile):
    pipeline = get_document_pipeline()
    content = await image.read()

    title = image.filename or "Image Analysis"
    doc = await pipeline.parse_image_bytes(content, title)

    return {
        "document_id": doc.document_id,
        "title": doc.title,
        "content": doc.content,
    }


app = router


__all__ = ["app"]
