import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx


class ArchitectureSource(str, Enum):
    CONFLUENCE = "confluence"
    GITHUB = "github"
    GITLAB = "gitlab"
    FIGMA = "figma"
    EXCALIDRAW = "excalidraw"
    LOCAL = "local"


@dataclass
class ArchitectureDiagram:
    diagram_id: str
    source: str
    title: str
    description: str
    diagram_type: str
    url: str = ""
    components: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ArchitectureClient:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def fetch_from_confluence(
        self,
        space_key: str,
        label: Optional[str] = None,
    ) -> List[ArchitectureDiagram]:
        url = os.getenv("CONFLUENCE_URL", "")
        email = os.getenv("CONFLUENCE_EMAIL", "")
        api_token = os.getenv("CONFLUENCE_API_TOKEN", "")

        if not url:
            return []

        cql = f"space = {space_key} AND type = page"
        if label:
            cql += f" AND label = {label}"

        try:
            client = self._get_client()
            response = await client.get(
                f"{url}/rest/api/content",
                params={"cql": cql, "expand": "body.storage,version"},
                auth=(email, api_token),
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        diagrams = []
        for page in data.get("results", []):
            body = page.get("body", {}).get("storage", {}).get("value", "")
            if self._is_architecture_diagram(body):
                diagrams.append(
                    ArchitectureDiagram(
                        diagram_id=page.get("id", ""),
                        source=ArchitectureSource.CONFLUENCE.value,
                        title=page.get("title", ""),
                        description=body[:500],
                        diagram_type=self._detect_diagram_type(body),
                        url=f"{url}/spaces/{space_key}/pages/{page.get('id')}",
                        created_at=page.get("version", {}).get("created", 0),
                        updated_at=page.get("version", {}).get("created", 0),
                    )
                )

        return diagrams

    async def fetch_from_github(
        self,
        repo: str,
        path: str = "docs/architecture",
    ) -> List[ArchitectureDiagram]:
        token = os.getenv("GITHUB_TOKEN", "")
        if not token:
            return []

        try:
            client = self._get_client()
            response = await client.get(
                f"https://api.github.com/repos/{repo}/contents/{path}",
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        diagrams = []
        for item in data:
            if item.get("name", "").endswith((".md", ".drawio", ".png", ".svg")):
                diagrams.append(
                    ArchitectureDiagram(
                        diagram_id=item.get("sha", ""),
                        source=ArchitectureSource.GITHUB.value,
                        title=item.get("name", ""),
                        description=f"Architecture diagram from {path}",
                        diagram_type=self._detect_diagram_type(item.get("name", "")),
                        url=item.get("download_url", ""),
                        created_at=0,
                        updated_at=0,
                    )
                )

        return diagrams

    async def fetch_from_local(
        self,
        directory: str,
    ) -> List[ArchitectureDiagram]:
        import glob

        if not directory:
            return []

        patterns = [
            f"{directory}/**/*.drawio",
            f"{directory}/**/*.md",
            f"{directory}/**/*.excalidraw",
        ]

        diagrams = []
        for pattern in patterns:
            for filepath in glob.glob(pattern, recursive=True):
                with open(filepath, "r", errors="ignore") as f:
                    content = f.read()

                diagrams.append(
                    ArchitectureDiagram(
                        diagram_id=filepath,
                        source=ArchitectureSource.LOCAL.value,
                        title=os.path.basename(filepath),
                        description=content[:500],
                        diagram_type=self._detect_diagram_type(filepath),
                        url=f"file://{filepath}",
                    )
                )

        return diagrams

    async def parse_architecture(
        self,
        diagram: ArchitectureDiagram,
    ) -> Dict[str, Any]:
        components = []
        relationships = []

        if diagram.diagram_type == "mermaid":
            components, relationships = self._parse_mermaid(diagram.description)
        elif diagram.diagram_type == "plantuml":
            components, relationships = self._parse_plantuml(diagram.description)
        elif diagram.diagram_type == "excalidraw":
            components, relationships = self._parse_excalidraw(diagram.description)

        return {
            "components": components,
            "relationships": relationships,
        }

    def _is_architecture_diagram(self, content: str) -> bool:
        markers = ["mermaid", "plantuml", "```mermaid", "architecture", "diagram"]
        return any(marker in content.lower() for marker in markers)

    def _detect_diagram_type(self, content: str) -> str:
        if "mermaid" in content:
            return "mermaid"
        elif "@startuml" in content or "plantuml" in content:
            return "plantuml"
        elif content.endswith(".excalidraw"):
            return "excalidraw"
        elif content.endswith(".drawio"):
            return "drawio"
        elif "sequence" in content or "flowchart" in content:
            return "text_diagram"
        return "unknown"

    def _parse_mermaid(self, content: str) -> tuple:
        components = []
        relationships = []

        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if "-->" in line:
                parts = line.split("-->")
                if len(parts) == 2:
                    relationships.append(
                        {
                            "from": parts[0].strip(),
                            "to": parts[1].strip().split("--")[0].strip(),
                            "type": "directs",
                        }
                    )
            elif "{" in line:
                components.append({"name": line.split("{")[0].strip()})

        return components, relationships

    def _parse_plantuml(self, content: str) -> tuple:
        components = []
        relationships = []

        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if "-->" in line:
                parts = line.split("-->")
                if len(parts) == 2:
                    relationships.append(
                        {
                            "from": parts[0].strip(),
                            "to": parts[1].strip().split("--")[0].strip(),
                            "type": "directs",
                        }
                    )

        return components, relationships

    def _parse_excalidraw(self, content: str) -> tuple:
        import json

        try:
            data = json.loads(content)
            elements = data.get("elements", [])

            components = [
                {
                    "id": e.get("id"),
                    "type": e.get("type"),
                    "name": e.get("label", e.get("id")),
                }
                for e in elements
                if e.get("type") in ["rectangle", "diamond"]
            ]

            return components, []
        except Exception:
            return [], []


_client: Optional[ArchitectureClient] = None


def get_architecture_client() -> ArchitectureClient:
    global _client
    if _client is None:
        _client = ArchitectureClient()
    return _client
