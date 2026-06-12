"""HAS_ISSUE relationship management from tickets/incidents.

Uses parameterized Cypher queries to prevent injection attacks.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

CypherStatement = Tuple[str, Dict[str, Any]]


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
        self._issues.append(
            {
                "component_name": component_name,
                "issue_type": issue_type,
                "description": description,
                "source": source,
            }
        )

    def get_issues(self, component_name: str) -> List[Dict[str, Any]]:
        """Get all issues for a component."""
        return [i for i in self._issues if i["component_name"] == component_name]

    def build_issues_cypher(self) -> List[CypherStatement]:
        """Build parameterized Cypher for HAS_ISSUE relationships."""
        if not self._issues:
            return []

        statements: List[CypherStatement] = []
        for issue in self._issues:
            issue_id = (
                f"issue_{issue['source'].replace('-', '_')}"
                if issue.get("source")
                else f"issue_{uuid.uuid4().hex[:8]}"
            )
            props: Dict[str, Any] = {
                "issue_type": issue["issue_type"],
                "description": issue["description"],
                "source": issue.get("source", ""),
            }
            statements.append(
                (
                    "MATCH (sc:SAPComponent {name: $component_name}) "
                    "MERGE (s:UISketch {sketch_id: $issue_id}) "
                    "SET s.title = $description, s.source_url = $source, "
                    "s.format_type = 'issue', s.ingestion_timestamp = datetime() "
                    "MERGE (sc)-[:HAS_ISSUE $props]->(s)",
                    {
                        "component_name": issue["component_name"],
                        "issue_id": issue_id,
                        "description": issue["description"],
                        "source": issue.get("source", ""),
                        "props": props,
                    },
                )
            )

        return statements


_tracker: Optional[UIIssueTracker] = None


def get_issue_tracker() -> UIIssueTracker:
    global _tracker
    if _tracker is None:
        _tracker = UIIssueTracker()
    return _tracker
