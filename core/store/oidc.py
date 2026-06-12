"""OIDC provider integration for enterprise auth."""

import logging
from typing import Dict, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class OIDCConfig(BaseModel):
    client_id: str
    client_secret: str = ""
    authority: str  # e.g., https://login.microsoftonline.com/{tenant}
    redirect_uri: str = "http://localhost:8000/auth/callback"
    scope: str = "openid profile email"


class OIDCProvider:
    def __init__(self, config: OIDCConfig):
        self.config = config

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.config.client_id,
            "response_type": "code",
            "redirect_uri": self.config.redirect_uri,
            "scope": self.config.scope,
            "state": state,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.config.authority}/oauth2/v2.0/authorize?{query}"

    def exchange_code(self, code: str) -> Optional[Dict]:
        token_url = f"{self.config.authority}/oauth2/v2.0/token"
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.config.redirect_uri,
        }
        import asyncio

        import httpx

        async def exchange():
            async with httpx.AsyncClient() as client:
                resp = await client.post(token_url, data=data)
                if resp.status_code == 200:
                    return resp.json()
                return None

        return asyncio.run(exchange())


_oidc_provider: Optional[OIDCProvider] = None


def get_oidc_provider(
    authority: str = "https://login.microsoftonline.com/common",
    client_id: str = "",
    client_secret: str = "",
) -> Optional[OIDCProvider]:
    global _oidc_provider
    if not client_id:
        return None
    if _oidc_provider is None:
        config = OIDCConfig(
            authority=authority,
            client_id=client_id,
            client_secret=client_secret,
        )
        _oidc_provider = OIDCProvider(config)
    return _oidc_provider
