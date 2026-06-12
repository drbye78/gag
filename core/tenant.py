"""Multi-tenant context management."""

from contextvars import ContextVar
from enum import Enum
from typing import Optional


class DataRegion(str, Enum):
    US = "us"
    EU = "eu"
    APAC = "apac"
    DEFAULT = "us"


_tenant_context: ContextVar[Optional[str]] = ContextVar("tenant_context", default=None)
_tenant_region: ContextVar[DataRegion] = ContextVar("tenant_region", default=DataRegion.DEFAULT)


def set_tenant(tenant_id: str, region: DataRegion = DataRegion.US) -> None:
    _tenant_context.set(tenant_id)
    _tenant_region.set(region)


def get_tenant() -> Optional[str]:
    return _tenant_context.get()


def get_region() -> DataRegion:
    return _tenant_region.get()


def clear_tenant() -> None:
    _tenant_context.set(None)
    _tenant_region.set(DataRegion.DEFAULT)


class TenantContext:
    """Context manager for tenant-scoped operations."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def __enter__(self):
        set_tenant(self.tenant_id)
        return self

    def __exit__(self, *args):
        clear_tenant()


def require_tenant() -> str:
    """Get tenant or raise if not set."""
    tenant = get_tenant()
    if not tenant:
        raise ValueError("Tenant context required")
    return tenant
