"""
Platform Adapter Integration for Unified Ingestion.

Extends unified_ingestion to support platform-specific artifacts:
- SAP BTP: MTA, CDS, CAP annotations
- Power Platform: Power Pages, Power Automate, Power Apps
- AWS: CloudFormation, SAM, CDK
- Azure: ARM templates, Bicep
- VMware Tanzu: manifests, helm charts
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from unified_ingestion.handlers.base import Chunk, Handler, HandlerResult


class PlatformArtifactHandler(Handler):
    """Base class for platform-specific artifact handlers."""

    def __init__(self):
        self._platform_handlers: Dict[str, Handler] = {}

    @abstractmethod
    def get_platform_id(self) -> str:
        """Return platform identifier (e.g., 'sap', 'aws', 'azure')."""
        pass

    @abstractmethod
    def get_supported_artifacts(self) -> List[str]:
        """Return list of supported artifact types."""
        pass

    def register_handler(self, artifact_type: str, handler: Handler) -> None:
        """Register a handler for a specific artifact type."""
        self._platform_handlers[artifact_type] = handler

    def get_handler(self, artifact_type: str) -> Optional[Handler]:
        """Get handler for a specific artifact type."""
        return self._platform_handlers.get(artifact_type)


class SAPBTPArtifactHandler(PlatformArtifactHandler):
    """Handler for SAP BTP-specific artifacts."""

    def get_platform_id(self) -> str:
        return "sap"

    def get_supported_artifacts(self) -> List[str]:
        return [
            "mta",
            "cds",
            "package_json",
            "security",
        ]

    async def handle(
        self,
        content: bytes,
        path: str,
        metadata: Dict[str, Any],
    ) -> HandlerResult:
        from unified_ingestion.handlers.platform.sap import (
            CAPPackageHandler,
            CDSHandler,
            MTAHandler,
            SecurityConfigHandler,
        )

        filename = path.lower()

        if "mtad" in filename or "mta.yaml" in filename:
            handler = MTAHandler()
        elif ".cds" in filename:
            handler = CDSHandler()
        elif "package.json" in filename:
            handler = CAPPackageHandler()
        elif "security" in filename:
            handler = SecurityConfigHandler()
        else:
            return HandlerResult(chunks=[], error=f"Unknown SAP artifact: {path}")

        return await handler.handle(content, path, metadata)


class PowerPlatformArtifactHandler(PlatformArtifactHandler):
    """Handler for Microsoft Power Platform artifacts."""

    def get_platform_id(self) -> str:
        return "powerplatform"

    def get_supported_artifacts(self) -> List[str]:
        return ["powerapps", "powerautomate", "powerpages", "dataverse"]

    async def handle(self, content: bytes, path: str, metadata: Dict[str, Any]) -> HandlerResult:
        return HandlerResult(chunks=[], error="Power Platform handler not implemented")


class AWSArtifactHandler(PlatformArtifactHandler):
    """Handler for AWS-specific artifacts."""

    def get_platform_id(self) -> str:
        return "aws"

    def get_supported_artifacts(self) -> List[str]:
        return ["cloudformation", "cdk", "sam", "amplify"]

    async def handle(self, content: bytes, path: str, metadata: Dict[str, Any]) -> HandlerResult:
        return HandlerResult(chunks=[], error="AWS handler not implemented")


class AzureArtifactHandler(PlatformArtifactHandler):
    """Handler for Azure-specific artifacts."""

    def get_platform_id(self) -> str:
        return "azure"

    def get_supported_artifacts(self) -> List[str]:
        return ["bicep", "arm", "terraform", "funcapp"]

    async def handle(self, content: bytes, path: str, metadata: Dict[str, Any]) -> HandlerResult:
        return HandlerResult(chunks=[], error="Azure handler not implemented")


class PlatformArtifactRegistry:
    """Registry for platform-specific artifact handlers."""

    def __init__(self):
        self._platforms: Dict[str, PlatformArtifactHandler] = {}

    def register(self, handler: PlatformArtifactHandler) -> None:
        self._platforms[handler.get_platform_id()] = handler

    def get(self, platform_id: str) -> Optional[PlatformArtifactHandler]:
        return self._platforms.get(platform_id)

    def detect_platform(self, path: str, content: Optional[bytes] = None) -> Optional[str]:
        """Detect platform from file path or content."""
        from pathlib import Path
        from urllib.parse import unquote

        filename = unquote(Path(path).name).lower()

        # Path-based detection
        if any(
            marker in filename
            for marker in ["sap", "btp", "mta", "mtad", "cds", "xsuaa", "xs-security", "package"]
        ):
            return "sap"
        if any(
            marker in filename
            for marker in ["powerapps", "powerautomate", "powerpages", "dataverse"]
        ):
            return "powerplatform"
        if any(marker in filename for marker in ["cloudformation", "cdk", "sam", "amplify", "aws"]):
            return "aws"
        if any(marker in filename for marker in ["bicep", "arm", "azure", "logicapp", "funcapp"]):
            return "azure"
        if any(marker in filename for marker in ["tanzu", "helm", "k8s", "istio"]):
            return "tanzu"
        if any(
            marker in filename
            for marker in ["salesforce", "apex", "visualforce", "lightning"]
        ):
            return "salesforce"
        if any(marker in filename for marker in ["gcp", "gke", "firestore", "cloudfunctions"]):
            return "gcp"
        if any(
            marker in filename
            for marker in ["platformv", "sber", "pangolin", "dataspace"]
        ):
            return "platformv"

        # Content-based detection (if provided)
        if content:
            text = content.decode("utf-8", errors="ignore")[:1000]
            if "_schema.cloudformation.amazonaws.com" in text:
                return "aws"
            if '"$schema": ".*azure.com"' in text:
                return "azure"
            if "SAP_CAP" in text or "_cds_yaml" in text:
                return "sap"

        return None

    def get_handler(self, path: str, content: Optional[bytes] = None) -> Optional[Handler]:
        """Detect platform and return appropriate handler."""
        platform_id = self.detect_platform(path, content)
        if not platform_id:
            return None

        platform_handler = self.get(platform_id)
        if not platform_handler:
            return None

        # Detect artifact type from filename
        from pathlib import Path
        from urllib.parse import unquote

        filename = unquote(Path(path).name).lower()

        artifact_type = self._detect_artifact_type(platform_id, filename)
        if artifact_type:
            return platform_handler.get_handler(artifact_type)

        return platform_handler

    def _detect_artifact_type(self, platform_id: str, filename: str) -> Optional[str]:
        """Detect artifact type from filename."""
        name = filename.lower()

        if platform_id == "sap":
            if ".mtad.yaml" in name or "mtad.yaml" in name:
                return "mta"
            if ".cds" in name:
                return "cds"
            if "package.json" in name:
                return "package_json"
            if "xs-security.json" in name:
                return "security"

        elif platform_id == "powerplatform":
            if "powerapps" in name:
                return "powerapps"
            if "powerautomate" in name or ".flow" in name:
                return "powerautomate"

        elif platform_id == "aws":
            if "cloudformation" in name or name.endswith(".yaml"):
                return "cloudformation"
            if "cdk" in name:
                return "cdk"
            if "sam" in name:
                return "sam"

        elif platform_id == "azure":
            if ".bicep" in name:
                return "bicep"
            if "arm" in name or "azuredeploy" in name:
                return "arm"
            if "terraform" in name:
                return "terraform"

        return None


# Global registry instance
_platform_registry: Optional[PlatformArtifactRegistry] = None


def get_platform_registry() -> PlatformArtifactRegistry:
    """Get global platform artifact registry."""
    global _platform_registry
    if _platform_registry is None:
        _platform_registry = PlatformArtifactRegistry()
        _platform_registry.register(SAPBTPArtifactHandler())
        _platform_registry.register(PowerPlatformArtifactHandler())
        _platform_registry.register(AWSArtifactHandler())
        _platform_registry.register(AzureArtifactHandler())
    return _platform_registry
