"""
Auth API - FastAPI endpoints for authentication and token management.

Provides /auth/register, /auth/token, /auth/revoke endpoints.
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator

from core.auth import (
    Role,
    User,
    get_rbac_manager,
    get_token_manager,
    require_authenticated,
    verify_token,
)
from core.token_blacklist import get_token_blacklist

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Models ──


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    roles: Optional[list[str]] = None

    @field_validator("username", "email", "password")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("field must not be empty")
        return v.strip()


class TokenRequest(BaseModel):
    username: str
    password: str

    @field_validator("username", "password")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("field must not be empty")
        return v.strip()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    username: str
    email: str
    message: str


class RevokeResponse(BaseModel):
    message: str


# ── Endpoints ──


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(request: RegisterRequest):
    """Register a new user."""
    rbac = get_rbac_manager()

    # Check if user already exists
    existing = await rbac.get_user(request.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    roles = request.roles or [Role.GUEST.value]

    # Validate roles
    valid_roles = {r.value for r in Role}
    for role in roles:
        if role not in valid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role: {role}. Valid roles: {', '.join(sorted(valid_roles))}",
            )

    user = await rbac.create_user(
        user_id=request.username,
        email=request.email,
        password=request.password,
        roles=roles,
    )

    return RegisterResponse(
        username=user.user_id,
        email=user.email,
        message="User registered successfully",
    )


@router.post("/token", response_model=TokenResponse)
async def login(request: TokenRequest):
    """Login and get an access token."""
    rbac = get_rbac_manager()

    user = await rbac.authenticate(request.username, request.password)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tm = get_token_manager()
    token = tm.create_token(user)
    return TokenResponse(access_token=token)


@router.post("/revoke", response_model=RevokeResponse)
async def revoke_token(
    request: Request,
    _user: User = Depends(require_authenticated),
):
    """Revoke the current access token.

    Adds the token's JTI to the blacklist, preventing any future use
    of this token. The blacklist entry expires when the token naturally
    expires.
    """
    auth_header = request.headers.get("authorization", "")
    parts = auth_header.split()
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid authorization header")

    token = parts[1]
    payload = await verify_token(token)

    if not payload:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(status_code=400, detail="Token has no JTI claim")

    exp = payload.get("exp", 0)
    now = int(time.time())
    expires_in = max(0, exp - now)

    blacklist = await get_token_blacklist()
    await blacklist.blacklist(jti, expires_in)

    logger.info("Token revoked: jti=%s, expires_in=%ds", jti, expires_in)

    return RevokeResponse(message="Token revoked successfully")
