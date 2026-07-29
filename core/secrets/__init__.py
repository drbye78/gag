"""Secrets Manager integration for production deployments.

Supports:
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SecretsProvider(ABC):
    """Base class for secrets providers."""
    
    @abstractmethod
    async def get_secret(self, key: str, json_key: Optional[str] = None) -> Optional[str]:
        """Get a secret value.

        Args:
            key: Provider-specific secret identifier (e.g., AWS Secret ID,
                 Vault path, Azure secret name, env var name).
            json_key: Optional JSON field name within the secret value.
                      If None, return the entire secret string.
                      If provided, parse as JSON and return that field.
        """
        pass
    
    @abstractmethod
    async def get_secrets(self, prefix: str = "") -> Dict[str, str]:
        """Get all secrets with optional prefix filter."""
        pass


class VaultSecretsProvider(SecretsProvider):
    """HashiCorp Vault secrets provider."""
    
    def __init__(self, url: str = None, token: str = None, mount: str = "secret"):
        self.url = url or os.getenv("VAULT_ADDR", "http://localhost:8200")
        self.token = token or os.getenv("VAULT_TOKEN")
        self.mount = mount
    
    async def get_secret(self, key: str, json_key: Optional[str] = None) -> Optional[str]:
        if not self.token:
            logger.warning("Vault token not configured")
            return None
        
        try:
            import hvac
            client = hvac.Client(url=self.url, token=self.token)
            secret = client.secrets.kv.v2.read_secret_version(
                path=key,
                mount_point=self.mount
            )
            value = secret["data"]["data"].get("value")
            if json_key and value:
                secret_dict = json.loads(value)
                return secret_dict.get(json_key)
            return value
        except Exception as e:
            logger.error("Failed to get Vault secret %s: %s", key, e)
            return None
    
    async def get_secrets(self, prefix: str = "") -> Dict[str, str]:
        if not self.token:
            return {}
        
        try:
            import hvac
            client = hvac.Client(url=self.url, token=self.token)
            secrets = {}
            
            list_response = client.secrets.kv.v2.list_secrets(
                path=prefix,
                mount_point=self.mount
            )
            
            for key in list_response.get("data", {}).get("keys", []):
                if key.endswith("/"):
                    continue
                value = await self.get_secret(f"{prefix}/{key}".strip("/"))
                if value:
                    secrets[key] = value
            
            return secrets
        except Exception as e:
            logger.error("Failed to list Vault secrets: %s", e)
            return {}


class AWSSecretsManagerProvider(SecretsProvider):
    """AWS Secrets Manager provider."""
    
    def __init__(self, region: str = None, profile: str = None):
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.profile = profile
    
    async def get_secret(self, key: str, json_key: Optional[str] = None) -> Optional[str]:
        """Get a secret from AWS Secrets Manager.

        Args:
            key: AWS Secret ID (e.g., "prod/database/credentials").
            json_key: Optional JSON field name within the secret value.
                      If None, return the entire JSON secret string.
                      If provided, parse as JSON and return that field.
        """
        try:
            import boto3
            import asyncio

            def _fetch():
                client = boto3.client(
                    "secretsmanager",
                    region_name=self.region,
                    profile_name=self.profile
                )
                response = client.get_secret_value(SecretId=key)
                secret_string = response.get("SecretString")
                if secret_string:
                    if json_key:
                        secret_dict = json.loads(secret_string)
                        return secret_dict.get(json_key)
                    return secret_string
                return None

            return await asyncio.to_thread(_fetch)
        except Exception as e:
            logger.error("Failed to get AWS secret %s: %s", key, e)
            return None
    
    async def get_secrets(self, prefix: str = "") -> Dict[str, str]:
        try:
            import boto3
            client = boto3.client(
                "secretsmanager",
                region_name=self.region,
                profile_name=self.profile
            )
            
            secrets = {}
            paginator = client.get_paginator("list_secrets")
            
            for page in paginator.paginate(
                Filters=[{"Key": "name-prefix", "Values": [prefix]}]
            ):
                for secret in page["SecretList"]:
                    name = secret["Name"].replace(prefix, "").strip("/")
                    value = await self.get_secret(secret["Name"])
                    if value:
                        secrets[name] = value
            
            return secrets
        except Exception as e:
            logger.error("Failed to list AWS secrets: %s", e)
            return {}


class AzureKeyVaultProvider(SecretsProvider):
    """Azure Key Vault provider."""
    
    def __init__(self, vault_url: str = None, tenant_id: str = None, client_id: str = None):
        self.vault_url = vault_url or os.getenv("AZURE_KEY_VAULT_URL")
        self.tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
        self.client_id = client_id or os.getenv("AZURE_CLIENT_ID")
    
    async def get_secret(self, key: str, json_key: Optional[str] = None) -> Optional[str]:
        if not self.vault_url:
            logger.warning("Azure Key Vault not configured")
            return None

        try:
            import asyncio

            def _fetch():
                from azure.identity import DefaultCredential
                from azure.keyvault.secrets import SecretClient
                credential = DefaultCredential(tenant_id=self.tenant_id, client_id=self.client_id)
                client = SecretClient(vault_url=self.vault_url, credential=credential)
                secret = client.get_secret(key)
                value = secret.value
                if json_key and value:
                    secret_dict = json.loads(value)
                    return secret_dict.get(json_key)
                return value

            return await asyncio.to_thread(_fetch)
        except Exception as e:
            logger.error("Failed to get Azure secret %s: %s", key, e)
            return None
    
    async def get_secrets(self, prefix: str = "") -> Dict[str, str]:
        if not self.vault_url:
            return {}
        
        try:
            from azure.identity import DefaultCredential
            from azure.keyvault.secrets import SecretClient
            
            credential = DefaultCredential(tenant_id=self.tenant_id, client_id=self.client_id)
            client = SecretClient(vault_url=self.vault_url, credential=credential)
            
            secrets = {}
            for secret in client.list_properties_of_secrets():
                if prefix and not secret.name.startswith(prefix):
                    continue
                value = await self.get_secret(secret.name)
                if value:
                    secrets[secret.name] = value
            
            return secrets
        except Exception as e:
            logger.error("Failed to list Azure secrets: %s", e)
            return {}


class EnvironmentSecretsProvider(SecretsProvider):
    """Fallback to environment variables."""
    
    async def get_secret(self, key: str, json_key: Optional[str] = None) -> Optional[str]:
        value = os.getenv(key)
        if json_key and value:
            try:
                secret_dict = json.loads(value)
                return secret_dict.get(json_key)
            except (json.JSONDecodeError, TypeError):
                return None
        return value
    
    async def get_secrets(self, prefix: str = "") -> Dict[str, str]:
        prefix = prefix.upper()
        return {
            k: v for k, v in os.environ.items()
            if k.upper().startswith(prefix)
        }


def get_secrets_provider() -> SecretsProvider:
    """Get configured secrets provider based on environment."""
    
    if os.getenv("AZURE_KEY_VAULT_URL"):
        logger.info("Using Azure Key Vault for secrets")
        return AzureKeyVaultProvider()
    
    if os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_REGION"):
        logger.info("Using AWS Secrets Manager for secrets")
        return AWSSecretsManagerProvider()
    
    if os.getenv("VAULT_ADDR") and os.getenv("VAULT_TOKEN"):
        logger.info("Using HashiCorp Vault for secrets")
        return VaultSecretsProvider()
    
    logger.info("Using environment variables for secrets (fallback)")
    return EnvironmentSecretsProvider()


async def get_secret(key: str, default: str = None, json_key: Optional[str] = None) -> str:
    """Get a secret from the configured provider."""
    provider = get_secrets_provider()
    return await provider.get_secret(key, json_key=json_key) or default


async def get_all_secrets(prefix: str = "") -> Dict[str, str]:
    """Get all secrets from the configured provider."""
    provider = get_secrets_provider()
    return await provider.get_secrets(prefix)