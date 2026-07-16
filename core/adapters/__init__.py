from core.adapters.base import (
    AdapterInput,
    AdapterOutput, 
    PlatformAdapter,
    AdapterRegistry,
    get_adapter_registry,
)

from core.adapters.sap import SAPBTPAdapter
from core.adapters.tanzu import VMwareTanzuAdapter
from core.adapters.powerplatform import PowerPlatformAdapter
from core.adapters.clouds import AWSAdapter, AzureAdapter, GCPAdapter, register_cloud_adapters

_adapter_registry_instance: AdapterRegistry = None


def _ensure_registry() -> AdapterRegistry:
    global _adapter_registry_instance
    if _adapter_registry_instance is None:
        _adapter_registry_instance = AdapterRegistry()
        _adapter_registry_instance.register(SAPBTPAdapter())
        _adapter_registry_instance.register(VMwareTanzuAdapter())
        _adapter_registry_instance.register(PowerPlatformAdapter())
        # Cloud adapters
        _adapter_registry_instance.register(AWSAdapter())
        _adapter_registry_instance.register(AzureAdapter())
        _adapter_registry_instance.register(GCPAdapter())
    return _adapter_registry_instance


def get_adapter_registry() -> AdapterRegistry:
    return _ensure_registry()


__all__ = [
    "AdapterInput",
    "AdapterOutput", 
    "PlatformAdapter",
    "AdapterRegistry",
    "get_adapter_registry",
    "SAPBTPAdapter",
    "VMwareTanzuAdapter",
    "PowerPlatformAdapter",
    "AWSAdapter",
    "AzureAdapter",
    "GCPAdapter",
]