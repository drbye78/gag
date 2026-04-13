import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class TelemetryCredentials:
    source: str
    url: str
    auth_type: str
    credentials: Dict[str, str] = field(default_factory=dict)


class TelemetryCredentialManager:
    def __init__(self):
        self._credentials: Dict[str, TelemetryCredentials] = {}

    def add_prometheus(
        self,
        source: str,
        url: str,
        basic_auth: Optional[tuple] = None,
    ) -> None:
        creds = {"url": url}
        if basic_auth:
            creds["username"] = basic_auth[0]
            creds["password"] = basic_auth[1]
        else:
            creds["username"] = os.getenv("PROMETHEUS_USER", "")
            creds["password"] = os.getenv("PROMETHEUS_PASSWORD", "")

        self._credentials[source] = TelemetryCredentials(
            source=source,
            url=url,
            auth_type="basic_auth" if creds.get("username") else "none",
            credentials=creds,
        )

    def add_elasticsearch(
        self,
        source: str,
        url: str,
        api_key: Optional[str] = None,
    ) -> None:
        creds = {"url": url, "api_key": api_key or os.getenv("ELASTIC_API_KEY", "")}

        self._credentials[source] = TelemetryCredentials(
            source=source,
            url=url,
            auth_type="api_key",
            credentials=creds,
        )

    def add_loki(
        self,
        source: str,
        url: str,
        token: Optional[str] = None,
    ) -> None:
        creds = {"url": url, "token": token or os.getenv("LOKI_TOKEN", "")}

        self._credentials[source] = TelemetryCredentials(
            source=source,
            url=url,
            auth_type="bearer",
            credentials=creds,
        )

    def get(self, source: str) -> Optional[TelemetryCredentials]:
        return self._credentials.get(source)

    def list_sources(self) -> list[str]:
        return list(self._credentials.keys())

    def remove(self, source: str) -> bool:
        if source in self._credentials:
            del self._credentials[source]
            return True
        return False


_credential_manager: Optional[TelemetryCredentialManager] = None


def get_telemetry_credentials() -> TelemetryCredentialManager:
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = TelemetryCredentialManager()
    return _credential_manager
