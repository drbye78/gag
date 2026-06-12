import pytest


class TestTicketBackend:
    def test_backend_is_abc(self):
        from abc import ABC

        from retrieval.ticket import TicketBackend

        assert issubclass(TicketBackend, ABC)


class TestJiraBackend:
    def test_initialization(self):
        from retrieval.ticket import JiraBackend

        backend = JiraBackend(
            url="https://example.atlassian.net",
            email="test@example.com",
            api_token="test-token",
        )
        assert backend.url == "https://example.atlassian.net"
        assert backend.email == "test@example.com"

    def test_initialization_defaults(self):
        from retrieval.ticket import JiraBackend

        backend = JiraBackend()
        assert backend.url is not None


class TestGitHubIssuesBackend:
    def test_initialization(self):
        from retrieval.ticket import GitHubIssuesBackend

        backend = GitHubIssuesBackend(
            owner="test-owner",
            repo="test-repo",
            token="ghp-test-token",
        )
        assert backend.owner == "test-owner"
        assert backend.repo == "test-repo"

    def test_initialization_defaults(self):
        from retrieval.ticket import GitHubIssuesBackend

        backend = GitHubIssuesBackend()
        assert backend.owner is not None


class TestInMemoryTicketBackend:
    def test_initialization(self):
        from retrieval.ticket import InMemoryTicketBackend

        backend = InMemoryTicketBackend()
        assert backend is not None
        assert backend._tickets == []

    def test_add_ticket(self):
        from retrieval.ticket import InMemoryTicketBackend

        backend = InMemoryTicketBackend()
        backend.add_ticket({"key": "TEST-1", "title": "Test ticket", "status": "Open"})
        assert len(backend._tickets) == 1

    @pytest.mark.asyncio
    async def test_search(self):
        from retrieval.ticket import InMemoryTicketBackend

        backend = InMemoryTicketBackend()
        backend._tickets = [
            {"key": "TEST-1", "title": "Login bug", "status": "Open"},
            {"key": "TEST-2", "title": "Display issue", "status": "Closed"},
        ]
        results = await backend.search("login")
        assert len(results) == 1
