"""
Git Credentials - Credential management for git repositories.

Supports HTTPS (token, basic auth) and SSH key-based
authentication with per-repo credential storage.
"""

import logging
import os
import uuid
import base64
from typing import Any, Dict, List, Optional

from core.config import get_settings
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

from pydantic import BaseModel


class CredentialType(str, Enum):
    HTTPS_TOKEN = "https_token"
    HTTPS_BASIC = "https_basic"
    SSH_KEY = "ssh_key"


class GitCredential(BaseModel):
    repo_url: str
    credential_type: CredentialType
    username: Optional[str] = None
    token: Optional[str] = None
    password: Optional[str] = None
    ssh_key_path: Optional[str] = None
    ssh_key_password: Optional[str] = None


@dataclass
class StoredCredential:
    credential_id: str
    repo_url: str
    credential_type: CredentialType
    username: Optional[str] = None
    encrypted_token: Optional[str] = None
    encrypted_password: Optional[str] = None
    ssh_key_path: Optional[str] = None
    created_at: float = 0.0
    last_used: float = 0.0


class GitCredentialManager:
    def __init__(self):
        self._credentials: Dict[str, StoredCredential] = {}
        self._repo_credential_map: Dict[str, str] = {}
        self._load_from_env()

    def _load_from_env(self):
        for key, value in os.environ.items():
            if not key.startswith("GIT_REPO_"):
                continue
            if "_URL" in key:
                suffix = key.replace("GIT_REPO_", "").replace("_URL", "")
                cred = GitCredential(
                    repo_url=value,
                    credential_type=CredentialType.HTTPS_TOKEN,
                    token=os.environ.get(f"GIT_REPO_{suffix}_TOKEN"),
                )
                if cred.token:
                    self.add_credential(
                        repo_url=cred.repo_url,
                        credential_type=CredentialType.HTTPS_TOKEN,
                        token=cred.token,
                    )

    def add_credential(
        self,
        repo_url: str,
        credential_type: CredentialType,
        username: Optional[str] = None,
        token: Optional[str] = None,
        password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        ssh_key_password: Optional[str] = None,
    ) -> str:
        credential_id = str(uuid.uuid4())[:8]

        stored = StoredCredential(
            credential_id=credential_id,
            repo_url=repo_url,
            credential_type=credential_type,
            username=username,
            encrypted_token=self._encrypt(token) if token else None,
            encrypted_password=self._encrypt(password) if password else None,
            ssh_key_path=ssh_key_path,
        )

        self._credentials[credential_id] = stored
        self._repo_credential_map[repo_url] = credential_id

        return credential_id

    def get_credential(self, repo_url: str) -> Optional[StoredCredential]:
        credential_id = self._repo_credential_map.get(repo_url)
        if credential_id:
            return self._credentials.get(credential_id)
        return None

    def getcredential_for_url(self, repo_url: str) -> Dict[str, Any]:
        stored = self.get_credential(repo_url)
        if not stored:
            return self._get_public_credential(repo_url)

        return {
            "credential_type": stored.credential_type.value,
            "username": stored.username,
            "token": self._decrypt(stored.encrypted_token)
            if stored.encrypted_token
            else None,
            "password": self._decrypt(stored.encrypted_password)
            if stored.encrypted_password
            else None,
            "ssh_key_path": stored.ssh_key_path,
            "ssh_key_password": stored.ssh_key_password,
        }

    def _get_public_credential(self, repo_url: str) -> Dict[str, Any]:
        if "github.com" in repo_url:
            return {
                "credential_type": CredentialType.HTTPS_TOKEN.value,
                "username": None,
                "token": os.environ.get("GITHUB_TOKEN"),
                "password": None,
                "ssh_key_path": None,
            }
        elif "gitlab.com" in repo_url:
            return {
                "credential_type": CredentialType.HTTPS_TOKEN.value,
                "username": None,
                "token": os.environ.get("GITLAB_TOKEN"),
                "password": None,
                "ssh_key_path": None,
            }
        elif "azure.com" in repo_url or "dev.azure.com" in repo_url:
            return {
                "credential_type": CredentialType.HTTPS_BASIC.value,
                "username": os.environ.get("AZURE_DEVOPS_USERNAME"),
                "token": os.environ.get("AZURE_DEVOPS_TOKEN"),
                "password": None,
                "ssh_key_path": None,
            }

        return {
            "credential_type": "none",
            "username": None,
            "token": None,
            "password": None,
            "ssh_key_path": None,
        }

    def _get_encrypt_key(self) -> str:
        key = get_settings().credential_encrypt_key
        if not key:
            raise RuntimeError(
                "CREDENTIAL_ENCRYPT_KEY environment variable must be set. "
                "Provide a secure random key of at least 32 characters."
            )
        return key

    def _encrypt(self, value: str) -> str:
        if not value:
            return ""
        from cryptography.fernet import Fernet
        import hashlib
        key = self._get_encrypt_key()
        key_bytes = hashlib.sha256(key.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        fernet = Fernet(fernet_key)
        return fernet.encrypt(value.encode()).hex()

    def _decrypt(self, value: str) -> Optional[str]:
        if not value:
            return None
        try:
            from cryptography.fernet import Fernet
            import hashlib
            key = self._get_encrypt_key()
            key_bytes = hashlib.sha256(key.encode()).digest()
            fernet_key = base64.urlsafe_b64encode(key_bytes)
            fernet = Fernet(fernet_key)
            return fernet.decrypt(bytes.fromhex(value)).decode()
        except Exception as e:
            logger.error("Failed to decrypt credential: %s", e)
        return None

    def list_credentials(self) -> list[Dict[str, Any]]:
        return [
            {
                "credential_id": c.credential_id,
                "repo_url": c.repo_url,
                "credential_type": c.credential_type.value,
                "has_token": bool(c.encrypted_token),
                "has_ssh_key": bool(c.ssh_key_path),
            }
            for c in self._credentials.values()
        ]

    def delete_credential(self, credential_id: str) -> bool:
        credential = self._credentials.pop(credential_id, None)
        if credential:
            self._repo_credential_map.pop(credential.repo_url, None)
            return True
        return False


_credential_manager: Optional[GitCredentialManager] = None


def get_credential_manager() -> GitCredentialManager:
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = GitCredentialManager()
    return _credential_manager
