"""
Authentication and authorization with proper RBAC enforcement.

Provides JWT token management, role-based access control,
and convenience functions for API-level auth checks.
"""

import logging
import os
import hashlib
import hmac
import secrets
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import Request

import jwt

from core.config import get_settings


class Role(str, Enum):
    ADMIN = "admin"
    ENGINEER = "engineer"
    VIEWER = "viewer"
    GUEST = "guest"


class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


ROLE_PERMISSIONS = {
    Role.ADMIN: {
        Permission.READ,
        Permission.WRITE,
        Permission.EXECUTE,
        Permission.ADMIN,
    },
    Role.ENGINEER: {Permission.READ, Permission.WRITE, Permission.EXECUTE},
    Role.VIEWER: {Permission.READ},
    Role.GUEST: {Permission.READ},
}


@dataclass
class User:
    user_id: str
    email: str
    password_hash: str
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    created_at: float = 0.0
    last_login: Optional[float] = None
    active: bool = True


logger = logging.getLogger(__name__)


class RBACManager:
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._failed_attempts: Dict[str, list] = {}  # email -> [timestamps]
        self._max_failed_attempts = 5
        self._lockout_seconds = 300  # 5 minutes
        self._user_store = None  # Lazy init

    async def _get_user_store(self):
        if self._user_store is None:
            try:
                from core.user_store import get_user_store
                self._user_store = await get_user_store()
            except Exception:
                logger.debug("Redis user store unavailable, using in-memory fallback")
                self._user_store = False  # Sentinel to avoid retrying
        return self._user_store if self._user_store is not False else None

    def hash_password(self, password: str) -> str:
        """Hash password with random salt (not jwt_secret)."""
        salt = secrets.token_bytes(32)
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            100000,
        )
        return key.hex() + ":" + salt.hex()

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against stored hash."""
        try:
            key_hex, salt_hex = hashed.rsplit(":", 1)
            salt = bytes.fromhex(salt_hex)
            key = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode(),
                salt,
                100000,
            )
            return hmac.compare_digest(key.hex(), key_hex)
        except Exception:
            return False

    async def create_user(
        self,
        user_id: str,
        email: str,
        password: str,
        roles: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None,
    ) -> User:
        user = User(
            user_id=user_id,
            email=email,
            password_hash=self.hash_password(password),
            roles=roles or [Role.GUEST.value],
            permissions=permissions or [],
            created_at=time.time(),
        )
        self._users[user_id] = user

        # Persist to Redis
        store = await self._get_user_store()
        if store:
            try:
                await store.create_user(self._user_to_dict(user))
            except Exception as e:
                logger.warning("Failed to persist user to Redis: %s", e)

        logger.info("User created: %s (%s) with roles %s", user_id, email, user.roles)
        return user

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        # Check lockout
        now = time.time()
        attempts = self._failed_attempts.get(email, [])
        recent = [t for t in attempts if now - t < self._lockout_seconds]
        if len(recent) >= self._max_failed_attempts:
            logger.error("Account locked out for %s after %d failed attempts", email, self._max_failed_attempts)
            return None  # Locked out

        # Search in-memory users
        for user in self._users.values():
            if user.email == email and user.active:
                if self.verify_password(password, user.password_hash):
                    user.last_login = now
                    self._failed_attempts.pop(email, None)
                    logger.info("Successful authentication for %s", email)
                    return user

        # Fall back: try Redis-backed users not yet cached
        store = await self._get_user_store()
        if store:
            try:
                all_usernames = await store.list_users()
                for username in all_usernames:
                    if username in self._users:
                        continue  # Already checked above
                    data = await store.get_user(username)
                    if data and data.get("email") == email and data.get("active", True):
                        stored_hash = data.get("password_hash", "")
                        if self.verify_password(password, stored_hash):
                            user = self._dict_to_user(data)
                            user.last_login = now
                            self._users[username] = user
                            self._failed_attempts.pop(email, None)
                            logger.info("Successful authentication for %s", email)
                            return user
            except Exception as e:
                logger.debug("Redis authenticate fallback failed: %s", e)

        # Track failed attempt
        self._failed_attempts.setdefault(email, []).append(now)
        logger.warning("Failed authentication attempt for %s", email)
        return None

    async def get_user(self, user_id: str) -> Optional[User]:
        # Try in-memory first
        user = self._users.get(user_id)
        if user:
            return user

        # Try Redis
        store = await self._get_user_store()
        if store:
            try:
                data = await store.get_user(user_id)
                if data:
                    user = self._dict_to_user(data)
                    self._users[user_id] = user  # Cache in memory
                    return user
            except Exception as e:
                logger.debug("Redis lookup failed for user %s: %s", user_id, e)

        return None

    def has_permission(self, user: User, required: Permission) -> bool:
        """Check if user has the required permission via their roles or direct permissions."""
        for role_str in user.roles:
            role = self._resolve_role(role_str)
            if role and required in ROLE_PERMISSIONS.get(role, set()):
                return True
        return required.value in user.permissions

    def has_role(self, user: User, required: Role) -> bool:
        return required.value in user.roles

    def authorize(self, user: User, permission: Permission) -> bool:
        return self.has_permission(user, permission)

    async def grant_role(self, user_id: str, role: Role) -> bool:
        user = await self.get_user(user_id)
        if user:
            user.roles.append(role.value)
            logger.info("Role %s granted to user %s", role.value, user_id)
            return True
        return False

    async def revoke_role(self, user_id: str, role: Role) -> bool:
        user = await self.get_user(user_id)
        if user and role.value in user.roles:
            user.roles.remove(role.value)
            logger.info("Role %s revoked from user %s", role.value, user_id)
            return True
        return False

    async def deactivate_user(self, user_id: str) -> bool:
        user = await self.get_user(user_id)
        if user:
            user.active = False
            logger.info("User %s deactivated", user_id)
            return True
        return False

    @staticmethod
    def _resolve_role(role_str: str) -> Optional[Role]:
        """Convert a role string to a Role enum member."""
        try:
            return Role(role_str)
        except ValueError:
            return None

    @staticmethod
    def _user_to_dict(user: User) -> Dict[str, Any]:
        """Serialize a User to a dict for Redis storage."""
        return {
            "username": user.user_id,
            "email": user.email,
            "password_hash": user.password_hash,
            "roles": user.roles,
            "permissions": user.permissions,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "active": user.active,
        }

    @staticmethod
    def _dict_to_user(data: Dict[str, Any]) -> User:
        """Deserialize a dict from Redis to a User object."""
        return User(
            user_id=data.get("username", ""),
            email=data.get("email", ""),
            password_hash=data.get("password_hash", ""),
            roles=data.get("roles", []),
            permissions=data.get("permissions", []),
            created_at=data.get("created_at", 0.0),
            last_login=data.get("last_login"),
            active=data.get("active", True),
        )


class TokenManager:
    def __init__(self, rbac: RBACManager):
        self.rbac = rbac
        self.settings = get_settings()

    def create_token(self, user: User) -> str:
        now = time.time()
        payload = {
            "sub": user.user_id,
            "email": user.email,
            "roles": user.roles,
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + (self.settings.jwt_expiry_minutes * 60),
        }
        return jwt.encode(
            payload,
            self.settings.jwt_secret,
            algorithm=self.settings.jwt_algorithm,
        )

    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret,
                algorithms=[self.settings.jwt_algorithm],
            )

            # Check blacklist
            jti = payload.get("jti")
            if jti:
                try:
                    from core.token_blacklist import get_token_blacklist

                    blacklist = await get_token_blacklist()
                    if await blacklist.is_blacklisted(jti):
                        logger.warning("Token rejected: jti %s is blacklisted", jti)
                        return None
                except Exception as e:
                    logger.debug("Blacklist check failed (allowing token): %s", e)

            user = await self.rbac.get_user(payload.get("sub", ""))
            if user and user.active:
                return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        return None


def require_permission(*permissions: Permission):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("user")

            if not user:
                from fastapi import HTTPException

                raise HTTPException(status_code=401, detail="Not authenticated")

            rbac = get_rbac_manager()
            for perm in permissions:
                if not rbac.has_permission(user, perm):
                    from fastapi import HTTPException

                    raise HTTPException(
                        status_code=403,
                        detail=f"Missing permission: {perm.value}",
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(*roles: Role):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("user")

            if not user:
                from fastapi import HTTPException

                raise HTTPException(status_code=401, detail="Not authenticated")

            rbac = get_rbac_manager()
            missing_roles = []
            for role in roles:
                if not rbac.has_role(user, role):
                    missing_roles.append(role.value)

            if missing_roles:
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=403,
                    detail=f"Missing required roles: {', '.join(missing_roles)}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


_rbac_manager: Optional[RBACManager] = None
_token_manager: Optional[TokenManager] = None


def get_rbac_manager() -> RBACManager:
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager


def get_token_manager() -> TokenManager:
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager(get_rbac_manager())
    return _token_manager


# ---------------------------------------------------------------------------
# Standalone convenience functions (used by tests and API endpoints)
# ---------------------------------------------------------------------------


async def create_token(user_id: str, roles: Optional[List[str]] = None) -> str:
    """Create a JWT token for a user.

    In production this requires user to exist.
    In test mode user will be auto created.
    """
    rbac = get_rbac_manager()
    user = await rbac.get_user(user_id)
    is_debug = os.getenv("DEBUG", "").lower() in ["true", "1", "yes"]

    if user is None:
        if is_debug:
            # SECURITY: Debug auto-creation is intentionally restricted to GUEST role only.
            # This prevents privilege escalation via debug mode.
            user = await rbac.create_user(
                user_id=user_id,
                email=f"{user_id}@example.com",
                password=secrets.token_hex(16),
                roles=[Role.GUEST.value],
            )
        else:
            raise ValueError(f"User {user_id} does not exist")

    tm = get_token_manager()
    return tm.create_token(user)


async def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify a JWT token and return the payload or None."""
    tm = get_token_manager()
    return await tm.verify_token(token)


async def check_permission(user_id: str, permission: str) -> bool:
    """Check if a user has a specific permission string (e.g. 'read', 'write')."""
    rbac = get_rbac_manager()
    user = await rbac.get_user(user_id)
    if not user:
        return False
    try:
        perm = Permission(permission)
    except ValueError:
        return permission in user.permissions
    return rbac.has_permission(user, perm)


async def check_role(user_id: str, role: str) -> bool:
    """Check if a user has a specific role string (e.g. 'admin')."""
    rbac = get_rbac_manager()
    user = await rbac.get_user(user_id)
    if not user:
        return False
    try:
        role_enum = Role(role)
    except ValueError:
        return role in user.roles
    return rbac.has_role(user, role_enum)


# ---------------------------------------------------------------------------
# FastAPI Authentication Dependencies
# ---------------------------------------------------------------------------


async def require_authenticated(request: "Request") -> User:
    """FastAPI dependency that checks for valid JWT and returns the authenticated user.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: 401 if no token provided or token is invalid

    Returns:
        User: The authenticated user object
    """
    from fastapi import HTTPException

    auth_header = request.headers.get("authorization")

    if not auth_header:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    tm = get_token_manager()
    payload = await tm.verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    rbac = get_rbac_manager()
    user = await rbac.get_user(user_id)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.active:
        raise HTTPException(
            status_code=401,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
