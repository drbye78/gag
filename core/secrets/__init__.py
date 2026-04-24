"""Secrets Manager integration for production deployments.

Supports:
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
"""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SecretsProvider(ABC):
    """Base class for secrets providers."""
    
    @abstractmethod
    async def get_secret(self, key: str) -> Optional[str]:
        """Get a secret value by key."""
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
    
    async def get_secret(self, key: str) -> Optional[str]:
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
            return secret["data"]["data"].get("value")
        except Exception as e:
            logger.error(f"Failed to get Vault secret {key}: {e}")
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
            logger.error(f"Failed to list Vault secrets: {e}")
            return {}


class AWSSecretsManagerProvider(SecretsProvider):
    """AWS Secrets Manager provider."""
    
    def __init__(self, region: str = None, profile: str = None):
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.profile = profile
    
    async def get_secret(self, key: str) -> Optional[str]:
        try:
            import boto3
            client = boto3.client(
                "secretsmanager",
                region_name=self.region,
                profile_name=self.profile
            )
            response = client.get_secret_value(SecretId=key)
            return response.get("SecretString", {}).get(key)
        except Exception as e:
            logger.error(f"Failed to get AWS secret {key}: {e}")
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
            logger.error(f"Failed to list AWS secrets: {e}")
            return {}


class AzureKeyVaultProvider(SecretsProvider):
    """Azure Key Vault provider."""
    
    def __init__(self, vault_url: str = None, tenant_id: str = None, client_id: str = None):
        self.vault_url = vault_url or os.getenv("AZURE_KEY_VAULT_URL")
        self.tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
        self.client_id = client_id or os.getenv("AZURE_CLIENT_ID")
    
    async def get_secret(self, key: str) -> Optional[str]:
        if not self.vault_url:
            logger.warning("Azure Key Vault not configured")
            return None
        
        try:
            from azure.identity import DefaultCredential
            from azure.keyvault.secrets import SecretClient
            
            credential = DefaultCredential(tenant_id=self.tenant_id, client_id=self.client_id)
            client = SecretClient(vault_url=self.vault_url, credential=credential)
            secret = client.get_secret(key)
            return secret.value
        except Exception as e:
            logger.error(f"Failed to get Azure secret {key}: {e}")
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
            async for secret in client.list_properties_of_secrets():
                if prefix and not secret.name.startswith(prefix):
                    continue
                value = await self.get_secret(secret.name)
                if value:
                    secrets[secret.name] = value
            
            return secrets
        except Exception as e:
            logger.error(f"Failed to list Azure secrets: {e}")
            return {}


class EnvironmentSecretsProvider(SecretsProvider):
    """Fallback to environment variables."""
    
    async def get_secret(self, key: str) -> Optional[str]:
        return os.getenv(key)
    
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


async def get_secret(key: str, default: str = None) -> str:
    """Get a secret from the configured provider."""
    provider = get_secrets_provider()
    return await provider.get_secret(key) or default


async def get_all_secrets(prefix: str = "") -> Dict[str, str]:
    """Get all secrets from the configured provider."""
    provider = get_secrets_provider()
    return await provider.get_secrets(prefix)