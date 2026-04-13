"""
WebDAV Client - WebDAV folder synchronization.

Provides file listing, download, and sync from
WebDAV-enabled storage (Nextcloud, SharePoint, etc.).
"""

import logging
import os
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class WebDAVMethod(str, Enum):
    PROPFIND = "PROPFIND"
    GET = "GET"
    PUT = "PUT"
    MKCOL = "MKCOL"
    DELETE = "DELETE"
    COPY = "COPY"
    MOVE = "MOVE"


@dataclass
class WebDAVFile:
    """WebDAV file model."""

    path: str
    name: str
    size: int
    content_type: str
    modified: Optional[str] = None
    created: Optional[str] = None
    is_directory: bool = False
    etag: Optional[str] = None


class WebDAVClient:
    def __init__(
        self,
        url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.url = url or os.getenv("WEBDAV_URL", "")
        self.username = username or os.getenv("WEBDAV_USER", "")
        self.password = password or os.getenv("WEBDAV_PASS", "")

        self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            auth = (self.username, self.password) if self.username else None
            self._client = httpx.AsyncClient(
                auth=auth,
                timeout=60.0,
                follow_redirects=True,
            )
        return self._client

    def _build_url(self, path: str) -> str:
        base = self.url.rstrip("/")
        path = path.lstrip("/")
        return f"{base}/{path}"

    async def list_directory(
        self,
        path: str = "/",
        deep: bool = False,
    ) -> List[WebDAVFile]:
        url = self._build_url(path)

        propfind_body = """<?xml version="1.0" encoding="utf-8"?>
        <d:propfind xmlns:d="DAV:">
            <d:prop>
                <d:displayname/>
                <d:getcontentlength/>
                <d:getcontenttype/>
                <d:getlastmodified/>
                <d:creationdate/>
                <d:resourcetype/>
                <d:getetag/>
            </d:prop>
        </d:propfind>"""

        client = self._get_client()

        try:
            resp = await client.request(
                method="PROPFIND",
                url=url,
                headers={
                    "Depth": "1" if not deep else "infinity",
                    "Content-Type": "application/xml",
                },
                content=propfind_body.encode(),
            )

            if resp.status_code not in (207, 200):
                return []

            return self._parse_propfind_response(resp.text)

        except Exception:
            return []

    def _parse_propfind_response(self, xml: str) -> List[WebDAVFile]:
        import re

        files = []

        responses = re.findall(r"<d:response>(.*?)</d:response>", xml, re.DOTALL)

        for resp in responses:
            href_match = re.search(r"<d:href>(.*?)</d:href>", resp)
            if not href_match:
                continue

            path = href_match.group(1).strip()
            if path.endswith("/"):
                path = path[:-1]

            name_match = re.search(r"<d:displayname>(.*?)</d:displayname>", resp)
            name = name_match.group(1) if name_match else os.path.basename(path)

            size_match = re.search(
                r"<d:getcontentlength>(.*?)</d:getcontentlength>", resp
            )
            size = int(size_match.group(1)) if size_match else 0

            type_match = re.search(r"<d:getcontenttype>(.*?)</d:getcontenttype>", resp)
            content_type = (
                type_match.group(1) if type_match else "application/octet-stream"
            )

            mod_match = re.search(r"<d:getlastmodified>(.*?)</d:getlastmodified>", resp)
            modified = mod_match.group(1) if mod_match else None

            is_dir = "<d:collection/>" in resp or "<d:collection>" in resp

            etag_match = re.search(r"<d:getetag>(.*?)</d:getetag>", resp)
            etag = etag_match.group(1) if etag_match else None

            files.append(
                WebDAVFile(
                    path=path,
                    name=name,
                    size=size,
                    content_type=content_type,
                    modified=modified,
                    is_directory=is_dir,
                    etag=etag,
                )
            )

        return files[1:]

    async def download_file(self, path: str) -> Optional[bytes]:
        url = self._build_url(path)

        client = self._get_client()

        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.content
        except Exception as e:
            logger.error("Failed to download WebDAV file %s: %s", path, e)

        return None

    async def upload_file(
        self,
        path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> bool:
        url = self._build_url(path)

        client = self._get_client()

        try:
            resp = await client.put(
                url,
                content=content,
                headers={"Content-Type": content_type},
            )
            return resp.status_code in (200, 201, 204)
        except Exception:
            return False

    async def delete_file(self, path: str) -> bool:
        url = self._build_url(path)

        client = self._get_client()

        try:
            resp = await client.delete(url)
            return resp.status_code in (200, 204)
        except Exception:
            return False

    async def create_directory(self, path: str) -> bool:
        url = self._build_url(path)

        client = self._get_client()

        try:
            resp = await client.request(
                method="MKCOL",
                url=url,
            )
            return resp.status_code in (200, 201)
        except Exception:
            return False

    async def sync_folder(
        self,
        path: str = "/",
        extensions: Optional[List[str]] = None,
        max_files: int = 100,
    ) -> List[WebDAVFile]:
        all_files = []

        await self._sync_folder_recursive(path, all_files, extensions, max_files)

        return all_files[:max_files]

    async def _sync_folder_recursive(
        self,
        path: str,
        results: List[WebDAVFile],
        extensions: Optional[List[str]],
        max_files: int,
    ):
        if len(results) >= max_files:
            return

        files = await self.list_directory(path, deep=False)

        for file in files:
            if file.is_directory:
                await self._sync_folder_recursive(
                    file.path, results, extensions, max_files
                )
            elif not extensions or any(file.name.endswith(ext) for ext in extensions):
                results.append(file)

            if len(results) >= max_files:
                break

    async def download_folder(
        self,
        path: str = "/",
        extensions: Optional[List[str]] = None,
    ) -> Dict[str, bytes]:
        files = await self.sync_folder(path, extensions)

        contents = {}
        for file in files:
            if not file.is_directory:
                content = await self.download_file(file.path)
                if content:
                    contents[file.path] = content

        return contents

    async def get_file_info(self, path: str) -> Optional[WebDAVFile]:
        files = await self.list_directory(os.path.dirname(path), deep=False)

        for file in files:
            if file.path.rstrip("/") == path.rstrip("/"):
                return file

        return None


_webdav_client: Optional[WebDAVClient] = None


def get_webdav_client() -> WebDAVClient:
    global _webdav_client
    if _webdav_client is None:
        _webdav_client = WebDAVClient()
    return _webdav_client
