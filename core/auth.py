"""
Authentication and authorization with proper RBAC enforcement.

Provides JWT token management, role-based access control,
and convenience functions for API-level auth checks.
"""

import os
import hashlib
import hmac
import secrets
import time
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


class RBACManager:
    def __init__(self):
        self._users: Dict[str, User] = {}

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

    def create_user(
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
        return user

    def authenticate(self, email: str, password: str) -> Optional[User]:
        for user in self._users.values():
            if user.email == email and user.active:
                if self.verify_password(password, user.password_hash):
                    user.last_login = time.time()
                    return user
        return None

    def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

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

    def grant_role(self, user_id: str, role: Role) -> bool:
        user = self._users.get(user_id)
        if user:
            user.roles.append(role.value)
            return True
        return False

    def revoke_role(self, user_id: str, role: Role) -> bool:
        user = self._users.get(user_id)
        if user and role.value in user.roles:
            user.roles.remove(role.value)
            return True
        return False

    def deactivate_user(self, user_id: str) -> bool:
        user = self._users.get(user_id)
        if user:
            user.active = False
            return True
        return False

    @staticmethod
    def _resolve_role(role_str: str) -> Optional[Role]:
        """Convert a role string to a Role enum member."""
        try:
            return Role(role_str)
        except ValueError:
            return None


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
            "iat": now,
            "exp": now + (self.settings.jwt_expiry_minutes * 60),
        }
        return jwt.encode(
            payload,
            self.settings.jwt_secret,
            algorithm=self.settings.jwt_algorithm,
        )

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret,
                algorithms=[self.settings.jwt_algorithm],
            )
            user = self.rbac.get_user(payload.get("sub", ""))
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
    user = rbac.get_user(user_id)
    is_debug = os.getenv("DEBUG", "").lower() in ["true", "1", "yes"]

    if user is None:
        if is_debug:
            user = rbac.create_user(
                user_id=user_id,
                email=f"{user_id}@example.com",
                password=secrets.token_hex(16),
                roles=roles or [Role.GUEST.value],
            )
        else:
            raise ValueError(f"User {user_id} does not exist")

    if roles and is_debug:
        has_admin_requested = Role.ADMIN.value in roles
        has_admin_current = any(r == Role.ADMIN.value for r in user.roles)

        if has_admin_requested and not has_admin_current:
            raise PermissionError(
                "Cannot grant admin role in DEBUG mode without existing admin privileges"
            )
        user.roles = roles

    tm = get_token_manager()
    return tm.create_token(user)
    """Verify a JWT token and return the payload or None."""
    tm = get_token_manager()
    return tm.verify_token(token)


async def check_permission(user_id: str, permission: str) -> bool:
    """Check if a user has a specific permission string (e.g. 'read', 'write')."""
    rbac = get_rbac_manager()
    user = rbac.get_user(user_id)
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
    user = rbac.get_user(user_id)
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


class PublicEndpoint:
    """Marker class to exempt routes from authentication.

    Usage:
        @app.get("/health")
        async def health():
            ...

        # Or use in route definition:
        app.add_api_route("/health", health, tags=["public"], dependencies=[])
    """


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
    payload = tm.verify_token(token)

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
    user = rbac.get_user(user_id)

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
