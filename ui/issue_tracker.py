"""HAS_ISSUE relationship management from tickets/incidents."""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class UIIssueTracker:
    """Tracks known issues with SAP components and builds HAS_ISSUE relationships."""

    def __init__(self):
        self._issues: List[Dict[str, Any]] = []

    def add_issue(
        self,
        component_name: str,
        issue_type: str,
        description: str,
        source: str = "",
    ):
        """Add issue for a SAP component."""
        self._issues.append({
            "component_name": component_name,
            "issue_type": issue_type,
            "description": description,
            "source": source,
        })

    def get_issues(self, component_name: str) -> List[Dict[str, Any]]:
        """Get all issues for a component."""
        return [i for i in self._issues if i["component_name"] == component_name]

    def build_issues_cypher(self) -> str:
        """Build Cypher for HAS_ISSUE relationships."""
        if not self._issues:
            return ""

        parts = []
        for issue in self._issues:
            props = {
                "issue_type": issue["issue_type"],
                "description": issue["description"],
                "source": issue.get("source", ""),
            }
            props_str = json.dumps(props)
            issue_id = f"issue_{issue['source'].replace('-', '_')}" if issue.get("source") else f"issue_{uuid.uuid4().hex[:8]}"
            parts.append(
                f"MATCH (sc:SAPComponent {{name: '{issue['component_name']}'}}) "
                f"MERGE (s:UISketch {{sketch_id: '{issue_id}'}}) "
                f"SET s.title = '{issue['description']}', s.source_url = '{issue['source']}', "
                f"s.format_type = 'issue', s.ingestion_timestamp = datetime() "
                f"MERGE (sc)-[:HAS_ISSUE {props_str}]->(s)"
            )

        return "\n".join(parts)


_tracker: Optional[UIIssueTracker] = None


def get_issue_tracker() -> UIIssueTracker:
    global _tracker
    if _tracker is None:
        _tracker = UIIssueTracker()
    return _tracker
