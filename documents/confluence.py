"""
Confluence Client - Atlassian Confluence API client.

Provides space and page sync with children support.
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx


@dataclass
class ConfluencePage:
    """Confluence page model."""

    page_id: str
    title: str
    space_key: str
    content: str
    content_type: str = " confluence_storage"
    parent_id: Optional[str] = None
    version: int = 1
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    url: Optional[str] = None
    children: List["ConfluencePage"] = field(default_factory=list)


class ConfluenceClient:
    def __init__(
        self,
        url: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
    ):
        self.url = url or os.getenv("CONFLUENCE_URL", "")
        self.email = email or os.getenv("CONFLUENCE_EMAIL", "")
        self.api_token = api_token or os.getenv("CONFLUENCE_API_TOKEN", "")
        self.base_url = f"{self.url}/wiki/api/v2"

        self._headers = {
            "Authorization": f"Basic {self._get_auth()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get_auth(self) -> str:
        import base64

        creds = f"{self.email}:{self.api_token}"
        return base64.b64encode(creds.encode()).decode()

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
