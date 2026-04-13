import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class TicketCredentials:
    source: str
    url: str
    auth_type: str
    credentials: Dict[str, str] = field(default_factory=dict)


class TicketCredentialManager:
    def __init__(self):
        self._credentials: Dict[str, TicketCredentials] = {}

    def add_jira(
        self,
        source: str,
        url: str,
        email: str,
        api_token: str,
    ) -> None:
        self._credentials[source] = TicketCredentials(
            source=source,
            url=url,
            auth_type="api_token",
            credentials={
                "email": email,
                "api_token": api_token,
            },
        )

    def add_github(
        self,
        source: str,
        token: str,
        owner: Optional[str] = None,
    ) -> None:
        self._credentials[source] = TicketCredentials(
            source=source,
            url="https://api.github.com",
            auth_type="bearer",
            credentials={
                "token": token,
                "owner": owner or "",
            },
        )

    def get(self, source: str) -> Optional[TicketCredentials]:
        return self._credentials.get(source)

    def list_sources(self) -> list[str]:
        return list(self._credentials.keys())

    def remove(self, source: str) -> bool:
        if source in self._credentials:
            del self._credentials[source]
            return True
        return False


_credential_manager: Optional[TicketCredentialManager] = None


def get_ticket_credentials() -> TicketCredentialManager:
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = TicketCredentialManager()
    return _credential_manager
