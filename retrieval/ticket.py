"""
Ticket Retriever - Support ticket retrieval.

Supports Jira and GitHub Issues backends with in-memory fallback.
"""

import os
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx


class TicketBackend(ABC):
    @abstractmethod
    async def search(
        self,
        query: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        pass


class JiraBackend(TicketBackend):
    def __init__(
        self,
        url: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
        project: str = "ENG",
    ):
        self.url = url or os.getenv("JIRA_URL", "")
        self.email = email or os.getenv("JIRA_EMAIL", "")
        self.api_token = api_token or os.getenv("JIRA_API_TOKEN", "")
        self.project = project
        self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            auth = (self.email, self.api_token)
            self._client = httpx.AsyncClient(auth=auth, timeout=30.0)
        return self._client

    async def search(
        self,
        query: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        jql = f"project = {self.project}"
        if query:
            jql += f' AND text ~ "{query}"'
        if status:
            jql += f' AND status = "{status}"'
        if priority:
            jql += f' AND priority = "{priority}"'

        jql += f" ORDER BY created DESC"

        try:
            client = self._get_client()
            resp = await client.get(
                f"{self.url}/rest/api/3/search",
                params={"jql": jql, "maxResults": limit},
            )
            resp.raise_for_status()
            data = resp.json()

            return [
                {
                    "id": issue["key"],
                    "title": issue["fields"]["summary"],
                    "description": issue["fields"]["description"] or "",
                    "status": issue["fields"]["status"]["name"],
                    "priority": issue["fields"]["priority"]["name"],
                }
                for issue in data.get("issues", [])
            ]
        except Exception:
            return []

    async def get(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        try:
            client = self._get_client()
            resp = await client.get(f"{self.url}/rest/api/3/issue/{ticket_id}")
            resp.raise_for_status()
            issue = resp.json()

            return {
                "id": issue["key"],
                "title": issue["fields"]["summary"],
                "description": issue["fields"]["description"] or "",
                "status": issue["fields"]["status"]["name"],
                "priority": issue["fields"]["priority"]["name"],
            }
        except Exception:
            return None


class GitHubIssuesBackend(TicketBackend):
    def __init__(
        self,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        token: Optional[str] = None,
    ):
        self.owner = owner or os.getenv("GITHUB_OWNER", "")
        self.repo = repo or os.getenv("GITHUB_REPO", "")
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {"Accept": "application/vnd.github.v3+json"}
            if self.token:
                headers["Authorization"] = f"token {self.token}"
            self._client = httpx.AsyncClient(headers=headers, timeout=30.0)
        return self._client

    async def search(
        self,
        query: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        search_query = f"repo:{self.owner}/{self.repo}"
        if query:
            search_query += f" {query}"
        if status:
            search_query += f" state:{status}"

        try:
            client = self._get_client()
            resp = await client.get(
                "https://api.github.com/search/issues",
                params={"q": search_query, "per_page": limit},
            )
            resp.raise_for_status()
            data = resp.json()

            return [
                {
                    "id": str(issue["number"]),
                    "title": issue["title"],
                    "description": issue["body"] or "",
                    "status": issue["state"],
                    "priority": "medium",
                }
                for issue in data.get("items", [])
            ]
        except Exception:
            return []

    async def get(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        try:
            client = self._get_client()
            resp = await client.get(
                f"https://api.github.com/repos/{self.owner}/{self.repo}/issues/{ticket_id}"
            )
            resp.raise_for_status()
            issue = resp.json()

            return {
                "id": str(issue["number"]),
                "title": issue["title"],
                "description": issue["body"] or "",
                "status": issue["state"],
                "priority": "medium",
            }
        except Exception:
            return None


class InMemoryTicketBackend(TicketBackend):
    """Fallback in-memory backend for development/testing."""

    def __init__(self):
        self._tickets: List[Dict[str, Any]] = []

    def add_ticket(self, ticket: Dict[str, Any]) -> None:
        self._tickets.append(ticket)

    async def search(
        self,
        query: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        results = []
        query_lower = query.lower() if query else ""

        for ticket in self._tickets:
            if query_lower:
                if query_lower not in ticket.get("title", "").lower():
                    if query_lower not in ticket.get("description", "").lower():
                        continue
            if status and ticket.get("status") != status:
                continue
            if priority and ticket.get("priority") != priority:
                continue
            results.append(ticket)

        return results[:limit]

    async def get(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        for ticket in self._tickets:
            if ticket.get("id") == ticket_id:
                return ticket
        return None


class TicketRetriever:
    def __init__(self, backend: Optional[TicketBackend] = None):
        self.backend = backend or self._create_default_backend()

    @staticmethod
    def _create_default_backend() -> TicketBackend:
        backend_type = os.getenv("TICKET_BACKEND", "").lower()

        if backend_type == "jira":
            return JiraBackend()
        elif backend_type == "github":
            return GitHubIssuesBackend()
        else:
            backend = InMemoryTicketBackend()
            backend.add_ticket(
                {
                    "id": "T001",
                    "title": "Login fails on Safari",
                    "description": "Users cannot login using Safari browser",
                    "status": "open",
                    "priority": "high",
                }
            )
            backend.add_ticket(
                {
                    "id": "T002",
                    "title": "API timeout issues",
                    "description": "API requests timing out after 30s",
                    "status": "in_progress",
                    "priority": "critical",
                }
            )
            backend.add_ticket(
                {
                    "id": "T003",
                    "title": "Memory leak in worker",
                    "description": "Background worker shows increasing memory",
                    "status": "open",
                    "priority": "medium",
                }
            )
            return backend

    async def search(
        self,
        query: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)

        results = await self.backend.search(query, status, priority, limit)

        took = int(time.time() * 1000) - start

        return {
            "source": "tickets",
            "query": query,
            "results": results,
            "total": len(results),
            "took_ms": took,
        }

    async def get(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        return await self.backend.get(ticket_id)


def get_ticket_retriever() -> TicketRetriever:
    return TicketRetriever()
