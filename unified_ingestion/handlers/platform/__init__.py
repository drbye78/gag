"""
Platform artifact handlers.
"""

from unified_ingestion.handlers.platform.sap import (
    CAPPackageHandler,
    CDSHandler,
    MTAHandler,
    SecurityConfigHandler,
)

__all__ = [
    "MTAHandler",
    "CDSHandler",
    "CAPPackageHandler",
    "SecurityConfigHandler",
]
