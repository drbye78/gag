"""
Platform artifact handlers.
"""

from unified_ingestion.handlers.platform.sap import (
    MTAHandler,
    CDSHandler,
    CAPPackageHandler,
    SecurityConfigHandler,
)

__all__ = [
    "MTAHandler",
    "CDSHandler", 
    "CAPPackageHandler",
    "SecurityConfigHandler",
]