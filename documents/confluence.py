"""
Confluence Client - Atlassian Confluence API client.

Provides space and page sync with children support, attachments, and recursive fetching.
"""

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

import httpx


class ConfluenceContentType(str, Enum):
    STORAGE = "confluence_storage"
    EDITOR_V2 = "editor_v2"
    ADF = "editor_adf"


@dataclass
class ConfluenceAttachment:
    """Confluence attachment model."""

    attachment_id: str
    title: str
    mime_type: str
    file_size: int
    download_link: Optional[str] = None
    web_link: Optional[str] = None
    created_at: Optional[str] = None
    version: int = 1


@dataclass
class ConfluencePage:
    """Confluence page model."""

    page_id: str
    title: str
    space_key: str
    content: str
    content_type: str = "confluence_storage"
    parent_id: Optional[str] = None
    version: int = 1
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    url: Optional[str] = None
    children: List["ConfluencePage"] = field(default_factory=list)
    attachments: List[ConfluenceAttachment] = field(default_factory=list)


class ConfluenceClient:
    # Confluence REST APIv2 base
    API_VERSION = "v2"
    # Legacy API for attachments (REST API v1)
    LEGACY_API = "rest/api"

    def __init__(
        self,
        url: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
    ):
        self.url = url or os.getenv("CONFLUENCE_URL", "")
        self.email = email or os.getenv("CONFLUENCE_EMAIL", "")
        self.api_token = api_token or os.getenv("CONFLUENCE_API_TOKEN", "")
        self.base_url = f"{self.url}/wiki/api/{self.API_VERSION}"
        self.legacy_url = f"{self.url}/{self.LEGACY_API}"

        self._headers = {
            "Authorization": f"Basic {self._get_auth()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get_auth(self) -> str:
        import base64

        creds = f"{self.email}:{self.api_token}"
        return base64.b64encode(creds.encode()).decode()

    # ──────────────────────────────────────────────────────────
    # Attachments API
    # ──────────────────────────────────────────────────────────

    async def list_attachments(
        self,
        page_id: str,
    ) -> List[Dict[str, Any]]:
        """List all attachments for a page."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.legacy_url}/content/{page_id}/child/attachment",
                headers=self._headers,
                params={"limit": 100},
                timeout=30.0,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            return data.get("results", [])

    async def get_attachment(
        self,
        page_id: str,
        attachment_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a specific attachment."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.legacy_url}/content/{page_id}/child/attachment/{attachment_id}",
                headers=self._headers,
                timeout=30.0,
            )
            if resp.status_code == 200:
                return resp.json()
            return None

    async def download_attachment(
        self,
        page_id: str,
        attachment_id: str,
    ) -> Optional[bytes]:
        """Download attachment binary content."""
        attachment = await self.get_attachment(page_id, attachment_id)
        if not attachment:
            return None

        download_url = attachment.get("_links", {}).get("download")
        if not download_url:
            return None

        # Handle relative URLs
        if download_url.startswith("/"):
            download_url = f"{self.url}{download_url}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                download_url,
                headers=self._headers,
                timeout=60.0,
            )
            if resp.status_code == 200:
                return resp.content
            return None

    async def get_page_attachments(
        self,
        page_id: str,
    ) -> List[ConfluenceAttachment]:
        """Get all attachments for a page with full metadata."""
        attachments = []
        results = await self.list_attachments(page_id)

        for item in results:
            file_meta = item.get("metadata", {}).get("file", {})
            attachments.append(
                ConfluenceAttachment(
                    attachment_id=item.get("id", ""),
                    title=item.get("title", ""),
                    mime_type=file_meta.get("mimeType", "application/octet-stream"),
                    file_size=file_meta.get("size", 0),
                    download_link=item.get("_links", {}).get("download"),
                    web_link=item.get("_links", {}).get("webui"),
                    created_at=item.get("createdAt"),
                    version=item.get("version", {}).get("number", 1),
                )
            )

        return attachments

    # ──────────────────────────────────────────────────────────
    # Child pages with recursive support
    # ──────────────────────────────────────────────────────────

    async def get_page_children(
        self,
        page_id: str,
        depth: int = 1,
    ) -> List[ConfluencePage]:
        children = []

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/pages/{page_id}/children",
                headers=self._headers,
                timeout=30.0,
            )
            if resp.status_code != 200:
                return children

            data = resp.json()
            results = data.get("results", [])

            for item in results:
                child_id = item.get("id")
                child_page = await self.get_page(child_id)

                if child_page:
                    body = await self.get_page_body(child_id)

                    child = ConfluencePage(
                        page_id=child_id,
                        title=child_page.get("title", ""),
                        space_key=child_page.get("spaceId", ""),
                        content=body or "",
                        version=child_page.get("version", {}).get("number", 1),
                    )

                    if depth > 1:
                        child.children = await self.get_page_children(
                            child_id, depth - 1
                        )

                    children.append(child)

        return children

    async def get_page_tree(
        self,
        page_id: str,
        include_attachments: bool = False,
    ) -> ConfluencePage:
        """Get a page with its full tree of children and optionally attachments."""
        page_data = await self.get_page(page_id)
        if not page_data:
            return ConfluencePage(
                page_id=page_id,
                title="Not Found",
                space_key="",
                content="",
            )

        body = await self.get_page_body(page_id)

        page = ConfluencePage(
            page_id=page_id,
            title=page_data.get("title", ""),
            space_key=page_data.get("spaceId", ""),
            content=body or "",
            version=page_data.get("version", {}).get("number", 1),
            created_at=page_data.get("createdAt"),
            updated_at=page_data.get("version", {}).get("createdAt"),
            url=page_data.get("_links", {}).get("webui"),
        )

        # Get children recursively
        page.children = await self.get_page_children(page_id, depth=10)

        if include_attachments:
            page.attachments = await self.get_page_attachments(page_id)

        return page

    async def sync_pages_with_tree(
        self,
        page_ids: List[str],
        include_attachments: bool = True,
    ) -> List[ConfluencePage]:
        """Sync multiple pages with full tree and attachments."""
        pages = []

        for page_id in page_ids:
            page = await self.get_page_tree(page_id, include_attachments)
            pages.append(page)

        return pages

    # ──────────────────────────────────────────────────────────
    # Legacy API wrappers (keep for compatibility)
    # ──────────────────────────────────────────────────────────

    async def list_spaces(self, limit: int = 25) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/spaces",
                headers=self._headers,
                params={"limit": limit},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])

    async def get_space(self, space_key: str) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/spaces/{space_key}",
                headers=self._headers,
                timeout=30.0,
            )
            if resp.status_code == 200:
                return resp.json()
            return None

    async def list_pages(
        self,
        space_key: Optional[str] = None,
        limit: int = 25,
    ) -> List[Dict[str, Any]]:
        params = {"limit": limit}
        if space_key:
            params["space-id"] = space_key

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/pages",
                headers=self._headers,
                params=params,
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])

    async def get_page(self, page_id: str) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/pages/{page_id}",
                headers=self._headers,
                timeout=30.0,
            )
            if resp.status_code == 200:
                return resp.json()
            return None

    async def get_page_body(self, page_id: str) -> Optional[str]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/pages/{page_id}/body",
                headers=self._headers,
                timeout=30.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("representation", {}).get("value", "")
            return None

    async def get_page_children(
        self,
        page_id: str,
        depth: int = 1,
    ) -> List[ConfluencePage]:
        children = []

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/pages/{page_id}/children",
                headers=self._headers,
                timeout=30.0,
            )
            if resp.status_code != 200:
                return children

            data = resp.json()
            results = data.get("results", [])

            for item in results:
                child_id = item.get("id")
                child_page = await self.get_page(child_id)

                if child_page:
                    body = await self.get_page_body(child_id)

                    children.append(
                        ConfluencePage(
                            page_id=child_id,
                            title=child_page.get("title", ""),
                            space_key=child_page.get("spaceId", ""),
                            content=body or "",
                            version=child_page.get("version", {}).get("number", 1),
                        )
                    )

                    if depth > 1:
                        grandchildren = await self.get_page_children(
                            child_id, depth - 1
                        )
                        children[-1].children = grandchildren

        return children

    async def sync_space(
        self,
        space_key: str,
        include_children: bool = True,
        max_depth: int = 3,
    ) -> List[ConfluencePage]:
        pages = []

        space_pages = await self.list_pages(space_key=space_key, limit=100)

        for page_data in space_pages:
            page_id = page_data.get("id")
            body = await self.get_page_body(page_id)

            page = ConfluencePage(
                page_id=page_id,
                title=page_data.get("title", ""),
                space_key=space_key,
                content=body or "",
                version=page_data.get("version", {}).get("number", 1),
            )

            if include_children and max_depth > 0:
                page.children = await self.get_page_children(page_id, depth=max_depth)

            pages.append(page)

        return pages

    async def sync_pages(
        self,
        page_ids: List[str],
        include_children: bool = False,
    ) -> List[ConfluencePage]:
        pages = []

        for page_id in page_ids:
            page_data = await self.get_page(page_id)
            if not page_data:
                continue

            body = await self.get_page_body(page_id)

            page = ConfluencePage(
                page_id=page_id,
                title=page_data.get("title", ""),
                space_key=page_data.get("spaceId", ""),
                content=body or "",
            )

            if include_children:
                page.children = await self.get_page_children(page_id)

            pages.append(page)

        return pages

    async def search_pages(
        self,
        cql: str,
        limit: int = 25,
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/pages",
                headers=self._headers,
                params={"cql": cql, "limit": limit},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])


_confluence_client: Optional[ConfluenceClient] = None


def get_confluence_client() -> ConfluenceClient:
    global _confluence_client
    if _confluence_client is None:
        _confluence_client = ConfluenceClient()
    return _confluence_client
