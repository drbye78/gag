import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx


class RequirementsSource(str, Enum):
    JIRA = "jira"
    CONFLUENCE = "confluence"
    LOCAL = "local"


@dataclass
class Requirement:
    req_id: str
    source: str
    title: str
    description: str
    status: str
    priority: str = ""
    type: str = ""
    acceptance_criteria: List[str] = field(default_factory=list)
    traceability: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RequirementsClient:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client


class JiraRequirementsClient(RequirementsClient):
    def __init__(
        self,
        url: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
        project: str = "REQ",
    ):
        super().__init__()
        self.url = url or os.getenv("JIRA_URL", "")
        self.email = email or os.getenv("JIRA_EMAIL", "")
        self.api_token = api_token or os.getenv("JIRA_API_TOKEN", "")
        self.project = project

    async def fetch_requirements(
        self,
        issue_type: str = "Story",
        max_results: int = 100,
    ) -> List[Requirement]:
        if not self.url:
            return []

        jql = f"project = {self.project} AND issuetype = {issue_type} ORDER BY created DESC"

        try:
            client = self._get_client()
            response = await client.get(
                f"{self.url}/rest/api/3/search",
                params={"jql": jql, "maxResults": max_results},
                auth=(self.email, self.api_token),
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        requirements = []
        for issue in data.get("issues", []):
            fields = issue.get("fields", {})
            requirements.append(
                Requirement(
                    req_id=issue.get("key", ""),
                    source=RequirementsSource.JIRA.value,
                    title=fields.get("summary", ""),
                    description=self._extract_description(
                        fields.get("description", {})
                    ),
                    status=fields.get("status", {}).get("name", ""),
                    priority=fields.get("priority", {}).get("name", ""),
                    type=fields.get("issuetype", {}).get("name", ""),
                    acceptance_criteria=self._extract_acceptance_criteria(
                        fields.get("description", {})
                    ),
                    traceability=[],
                    created_at=fields.get("created", ""),
                    updated_at=fields.get("updated", ""),
                )
            )

        return requirements

    def _extract_description(self, description: Any) -> str:
        if isinstance(description, dict):
            return description.get("content", "")
        return str(description) if description else ""

    def _extract_acceptance_criteria(self, description: Any) -> List[str]:
        criteria = []
        if isinstance(description, dict):
            content = description.get("content", "")
            if content:
                for line in content.split("\n"):
                    if "acceptance" in line.lower() or "criteria" in line.lower():
                        criteria.append(line.strip())
        return criteria


class ConfluenceRequirementsClient(RequirementsClient):
    def __init__(
        self,
        url: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
    ):
        super().__init__()
        self.url = url or os.getenv("CONFLUENCE_URL", "")
        self.email = email or os.getenv("CONFLUENCE_EMAIL", "")
        self.api_token = api_token or os.getenv("CONFLUENCE_API_TOKEN", "")

    async def fetch_requirements(
        self,
        space_key: str = "REQ",
        label: Optional[str] = "requirements",
    ) -> List[Requirement]:
        if not self.url:
            return []

        cql = f"space = {space_key} AND type = page"
        if label:
            cql += f" AND label = {label}"

        try:
            client = self._get_client()
            response = await client.get(
                f"{self.url}/rest/api/content",
                params={"cql": cql, "expand": "body.storage,version"},
                auth=(self.email, self.api_token),
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        requirements = []
        for page in data.get("results", []):
            body = page.get("body", {}).get("storage", {}).get("value", "")
            parsed = self._parse_requirements(body)

            requirements.append(
                Requirement(
                    req_id=page.get("id", ""),
                    source=RequirementsSource.CONFLUENCE.value,
                    title=page.get("title", ""),
                    description=body[:500],
                    status="active",
                    type="requirement",
                    acceptance_criteria=parsed.get("acceptance_criteria", []),
                    traceability=parsed.get("traceability", []),
                    created_at=page.get("version", {}).get("created", 0),
                    updated_at=page.get("version", {}).get("created", 0),
                )
            )

        return requirements

    def _parse_requirements(self, content: str) -> Dict[str, Any]:
        acceptance = []
        traceability = []

        lines = content.split("\n")
        current_section = None

        for line in lines:
            line_lower = line.lower().strip()
            if "acceptance" in line_lower or "criteria" in line_lower:
                current_section = "acceptance"
            elif "trace" in line_lower or "link" in line_lower:
                current_section = "traceability"
            elif line.strip().startswith("*") or line.strip().startswith("-"):
                if current_section == "acceptance":
                    acceptance.append(line.strip().lstrip("*-").strip())
                elif current_section == "traceability":
                    traceability.append(line.strip().lstrip("*-").strip())

        return {
            "acceptance_criteria": acceptance,
            "traceability": traceability,
        }


class LocalRequirementsClient(RequirementsClient):
    def __init__(self, base_path: Optional[str] = None):
        super().__init__()
        self.base_path = base_path or os.getenv("REQUIREMENTS_PATH", "requirements")

    async def fetch_requirements(
        self,
        file_pattern: str = "*.md",
    ) -> List[Requirement]:
        import glob

        if not self.base_path:
            return []

        pattern = f"{self.base_path}/**/{file_pattern}"
        requirements = []

        for filepath in glob.glob(pattern, recursive=True):
            try:
                with open(filepath, "r", errors="ignore") as f:
                    content = f.read()

                parsed = self._parse_requirements(content)

                requirements.append(
                    Requirement(
                        req_id=filepath,
                        source=RequirementsSource.LOCAL.value,
                        title=os.path.basename(filepath),
                        description=content[:500],
                        status="active",
                        type="requirement",
                        acceptance_criteria=parsed.get("acceptance_criteria", []),
                        traceability=parsed.get("traceability", []),
                    )
                )
            except Exception:
                continue

        return requirements

    def _parse_requirements(self, content: str) -> Dict[str, Any]:
        acceptance = []
        traceability = []

        lines = content.split("\n")
        current_section = None

        for line in lines:
            line_lower = line.lower().strip()
            if "acceptance" in line_lower or "criteria" in line_lower:
                current_section = "acceptance"
            elif "trace" in line_lower:
                current_section = "traceability"
            elif line.strip().startswith(("#", "*", "-")):
                text = line.strip().lstrip("#*- ").strip()
                if current_section == "acceptance" and text:
                    acceptance.append(text)
                elif current_section == "traceability" and text:
                    traceability.append(text)

        return {
            "acceptance_criteria": acceptance,
            "traceability": traceability,
        }


_client: Optional[RequirementsClient] = None


def get_requirements_client() -> RequirementsClient:
    global _client
    if _client is None:
        _client = RequirementsClient()
    return _client
