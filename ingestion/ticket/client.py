import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx


class TicketSource(str, Enum):
    JIRA = "jira"
    GITHUB = "github"


@dataclass
class Ticket:
    ticket_id: str
    source: str
    title: str
    description: str
    status: str
    priority: str = ""
    assignee: str = ""
    reporter: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    labels: List[str] = field(default_factory=list)
    comments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class JiraClient:
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
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                auth=(self.email, self.api_token),
                timeout=30.0,
            )
        return self._client

    async def fetch_issues(
        self,
        jql: Optional[str] = None,
        max_results: int = 100,
    ) -> List[Ticket]:
        if not jql:
            jql = f'project = "{self.project}" ORDER BY updated DESC'

        try:
            client = self._get_client()
            response = await client.get(
                f"{self.url}/rest/api/3/search",
                params={"jql": jql, "maxResults": max_results},
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        tickets = []
        for issue in data.get("issues", []):
            fields = issue.get("fields", {})
            tickets.append(
                Ticket(
                    ticket_id=issue.get("key", ""),
                    source=TicketSource.JIRA.value,
                    title=fields.get("summary", ""),
                    description=fields.get("description", {}).get("content", ""),
                    status=fields.get("status", {}).get("name", ""),
                    priority=fields.get("priority", {}).get("name", ""),
                    assignee=fields.get("assignee", {}).get("displayName", ""),
                    reporter=fields.get("reporter", {}).get("displayName", ""),
                    created_at=fields.get("created", ""),
                    updated_at=fields.get("updated", ""),
                    labels=[l.get("name", "") for l in fields.get("labels", [])],
                    metadata={
                        "issue_type": fields.get("issuetype", {}).get("name", ""),
                        "project": fields.get("project", {}).get("name", ""),
                    },
                )
            )

        return tickets

    async def fetch_issue(self, issue_key: str) -> Optional[Ticket]:
        try:
            client = self._get_client()
            response = await client.get(
                f"{self.url}/rest/api/3/issue/{issue_key}",
            )
            response.raise_for_status()
            data = response.json()
            fields = data.get("fields", {})
        except Exception:
            return None

        return Ticket(
            ticket_id=data.get("key", ""),
            source=TicketSource.JIRA.value,
            title=fields.get("summary", ""),
            description=fields.get("description", {}).get("content", ""),
            status=fields.get("status", {}).get("name", ""),
            priority=fields.get("priority", {}).get("name", ""),
            assignee=fields.get("assignee", {}).get("displayName", ""),
            reporter=fields.get("reporter", {}).get("displayName", ""),
            created_at=fields.get("created", ""),
            updated_at=fields.get("updated", ""),
            labels=[l.get("name", "") for l in fields.get("labels", [])],
            metadata={"issue_type": fields.get("issuetype", {}).get("name", "")},
        )

    async def fetch_comments(self, issue_key: str) -> List[Dict[str, Any]]:
        try:
            client = self._get_client()
            response = await client.get(
                f"{self.url}/rest/api/3/issue/{issue_key}/comment",
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        return [
            {
                "author": c.get("author", {}).get("displayName", ""),
                "body": c.get("body", {}).get("content", ""),
                "created": c.get("created", ""),
            }
            for c in data.get("results", [])
        ]


class GitHubIssuesClient:
    def __init__(
        self,
        token: Optional[str] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
    ):
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.owner = owner or os.getenv("GITHUB_OWNER", "")
        self.repo = repo or os.getenv("GITHUB_REPO", "")
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=30.0,
            )
        return self._client

    async def fetch_issues(
        self,
        state: str = "all",
        labels: Optional[List[str]] = None,
        max_results: int = 100,
    ) -> List[Ticket]:
        if not self.owner or not self.repo:
            return []

        try:
            client = self._get_client()
            response = await client.get(
                f"https://api.github.com/repos/{self.owner}/{self.repo}/issues",
                params={"state": state, "per_page": max_results},
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        tickets = []
        for issue in data:
            if "pull_request" in issue:
                continue

            tickets.append(
                Ticket(
                    ticket_id=str(issue.get("number", "")),
                    source=TicketSource.GITHUB.value,
                    title=issue.get("title", ""),
                    description=issue.get("body", ""),
                    status=issue.get("state", ""),
                    assignee=issue.get("assignee", {}).get("login", ""),
                    reporter=issue.get("user", {}).get("login", ""),
                    created_at=issue.get("created_at", ""),
                    updated_at=issue.get("updated_at", ""),
                    labels=[l for l in issue.get("labels", [])],
                    metadata={
                        "url": issue.get("html_url", ""),
                        "comments": issue.get("comments", 0),
                    },
                )
            )

        return tickets

    async def fetch_issue(self, issue_number: int) -> Optional[Ticket]:
        if not self.owner or not self.repo:
            return None

        try:
            client = self._get_client()
            response = await client.get(
                f"https://api.github.com/repos/{self.owner}/{self.repo}/issues/{issue_number}",
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return None

        return Ticket(
            ticket_id=str(data.get("number", "")),
            source=TicketSource.GITHUB.value,
            title=data.get("title", ""),
            description=data.get("body", ""),
            status=data.get("state", ""),
            assignee=data.get("assignee", {}).get("login", ""),
            reporter=data.get("user", {}).get("login", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            labels=[l for l in data.get("labels", [])],
            metadata={
                "url": data.get("html_url", ""),
                "comments": data.get("comments", 0),
            },
        )


_jira_client: Optional[JiraClient] = None
_github_client: Optional[GitHubIssuesClient] = None


def get_jira_client() -> JiraClient:
    global _jira_client
    if _jira_client is None:
        _jira_client = JiraClient()
    return _jira_client


def get_github_client() -> GitHubIssuesClient:
    global _github_client
    if _github_client is None:
        _github_client = GitHubIssuesClient()
    return _github_client
