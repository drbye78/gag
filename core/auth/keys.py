"""API key management for enterprise."""

import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from enum import Enum


class KeyType(str, Enum):
    API_KEY = "api_key"
    JWT_REFRESH = "jwt_refresh"


class APIKey:
    def __init__(
        self,
        key_id: str,
        key_hash: str,
        key_type: KeyType,
        user_id: str,
        expires_at: Optional[datetime] = None,
        last_used: Optional[datetime] = None,
    ):
        self.key_id = key_id
        self.key_hash = key_hash
        self.key_type = key_type
        self.user_id = user_id
        self.expires_at = expires_at
        self.last_used = last_used


class APIKeyManager:
    def __init__(self):
        self._keys: dict[str, APIKey] = {}

    def create_key(
        self,
        user_id: str,
        key_type: KeyType = KeyType.API_KEY,
        days_valid: int = 90,
    ) -> tuple[str, str]:
        key_id = secrets.token_urlsafe(16)
        key_value = secrets.token_urlsafe(32)
        key_hash = secrets.hash_password(key_value)
        expires_at = datetime.utcnow() + timedelta(days=days_valid)

        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            key_type=key_type,
            user_id=user_id,
            expires_at=expires_at,
        )
        self._keys[key_id] = api_key
        return key_id, key_value

    def validate_key(self, key_id: str, key_value: str) -> bool:
        key = self._keys.get(key_id)
        if not key:
            return False
        if key.expires_at and key.expires_at < datetime.utcnow():
            return False
        import hmac
        if not hmac.compare_digest(key.key_hash, secrets.hash_password(key_value)):
            return False
        key.last_used = datetime.utcnow()
        return True

    def revoke_key(self, key_id: str) -> bool:
        if key_id in self._keys:
            del self._keys[key_id]
            return True
        return False

    def list_keys(self, user_id: str) -> List[APIKey]:
        return [k for k in self._keys.values() if k.user_id == user_id]


_key_manager: Optional[APIKeyManager] = None


def get_key_manager() -> APIKeyManager:
    global _key_manager
    if _key_manager is None:
        _key_manager = APIKeyManager()
    return _key_manager