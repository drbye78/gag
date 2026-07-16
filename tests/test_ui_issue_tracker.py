"""Tests for UIIssueTracker - HAS_ISSUE relationship tracking."""

from ui.issue_tracker import UIIssueTracker, get_issue_tracker


class TestAddIssue:
    def test_add_issue(self):
        """Add issue, verify get_issues returns it."""
        tracker = UIIssueTracker()
        tracker.add_issue(
            component_name="SAPUI5 Table",
            issue_type="performance",
            description="Slow rendering with >1000 rows",
            source="ticket-123",
        )

        issues = tracker.get_issues("SAPUI5 Table")
        assert len(issues) == 1
        assert issues[0]["issue_type"] == "performance"
        assert issues[0]["description"] == "Slow rendering with >1000 rows"
        assert issues[0]["source"] == "ticket-123"


class TestGetNoIssues:
    def test_get_no_issues(self):
        """Unknown component returns empty list."""
        tracker = UIIssueTracker()
        issues = tracker.get_issues("NonExistent Component")
        assert issues == []


class TestMultipleIssuesSameComponent:
    def test_multiple_issues_same_component(self):
        """Multiple issues for one component."""
        tracker = UIIssueTracker()
        tracker.add_issue(
            component_name="SAPUI5 Table",
            issue_type="performance",
            description="Slow rendering with >1000 rows",
            source="ticket-123",
        )
        tracker.add_issue(
            component_name="SAPUI5 Table",
            issue_type="usability",
            description="No built-in column resize",
            source="ticket-456",
        )

        issues = tracker.get_issues("SAPUI5 Table")
        assert len(issues) == 2
        issue_types = {i["issue_type"] for i in issues}
        assert "performance" in issue_types
        assert "usability" in issue_types


class TestBuildIssuesCypher:
    def test_build_issues_cypher(self):
        """Generates Cypher with HAS_ISSUE, component name, issue_type."""
        tracker = UIIssueTracker()
        tracker.add_issue(
            component_name="SAPUI5 Table",
            issue_type="performance",
            description="Slow rendering with >1000 rows",
            source="ticket-123",
        )

        cypher = tracker.build_issues_cypher()

        assert "HAS_ISSUE" in cypher
        assert "SAPUI5 Table" in cypher
        assert "performance" in cypher
        assert "MATCH" in cypher
        assert "MERGE" in cypher


class TestBuildIssuesCypherEmpty:
    def test_build_issues_cypher_empty(self):
        """No issues returns empty string."""
        tracker = UIIssueTracker()
        cypher = tracker.build_issues_cypher()
        assert cypher == ""


class TestGetIssueTrackerSingleton:
    def test_get_issue_tracker_returns_singleton(self):
        """get_issue_tracker returns same instance."""
        t1 = get_issue_tracker()
        t2 = get_issue_tracker()
        assert t1 is t2
