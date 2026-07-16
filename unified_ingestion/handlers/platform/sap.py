"""
SAP BTP Artifact Handlers.

Handlers for SAP Business Technology Platform specific artifacts:
- MTA deployment descriptors
- CDS models
- CAP package.json
- Security configurations
"""

import json
import logging
from typing import Any, Dict, List

from unified_ingestion.handlers.base import Handler, HandlerResult, Chunk

logger = logging.getLogger(__name__)


class MTAHandler(Handler):
    """Handler for SAP MTA (Multi-Target Application) descriptors."""
    
    async def handle(
        self,
        content: bytes,
        path: str,
        metadata: Dict[str, Any],
    ) -> HandlerResult:
        """Parse MTA deployment descriptor (mtad.yaml)."""
        try:
            import yaml
            data = yaml.safe_load(content)
            
            if not data:
                return HandlerResult(success=False, chunks=[], error="Empty MTA file")
            
            # Extract MTA metadata
            mta_version = data.get("_schema-version", "unknown")
            mta_id = data.get("ID", path)
            version = data.get("version", "unknown")
            
            # Extract modules
            modules = data.get("modules", [])
            module_names = [m.get("name", "") for m in modules]
            
            # Extract services
            resources = data.get("resources", [])
            resource_names = [r.get("name", "") for r in resources]
            
            # Build chunk content
            chunks = [
                Chunk(
                    id=f"{path}:mta",
                    content=f"MTA: {mta_id} v{version} (schema: {mta_version})\n"
                            f"Modules: {', '.join(module_names)}\n"
                            f"Resources: {', '.join(resource_names)}",
                    chunk_index=0,
                    start_char=0,
                    end_char=500,
                    metadata={
                        "artifact_type": "mta",
                        "platform": "sap",
                        "mta_id": mta_id,
                        "modules": module_names,
                        "resources": resource_names,
                    },
                )
            ]
            
            return HandlerResult(success=True, chunks=chunks, metadata={
                    "platform": "sap",
                    "artifact_type": "mta",
                    "mta_id": mta_id,
                    "version": version,
                })
        except Exception as e:
            logger.warning(f"MTA parsing failed for {path}: {e}")
            return HandlerResult(success=False, chunks=[], error=str(e))


class CDSHandler(Handler):
    """Handler for SAP CDS (Core Data Services) models."""
    
    async def handle(
        self,
        content: bytes,
        path: str,
        metadata: Dict[str, Any],
    ) -> HandlerResult:
        """Parse CDS model files (*.cds)."""
        try:
            text = content.decode("utf-8", errors="ignore")
            
            # Extract CDS entities (simplified parsing)
            entities = []
            lines = text.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("entity ") or line.startswith("view "):
                    name = line.split()[1].split("{")[0].strip()
                    entities.append(name)
            
            chunks = [
                Chunk(
                    id=f"{path}:cds",
                    content=f"CDS: {path}\nEntities: {', '.join(entities)}",
                    chunk_index=0,
                    start_char=0,
                    end_char=len(text),
                    metadata={
                        "artifact_type": "cds",
                        "platform": "sap",
                        "entities": entities,
                    },
                )
            ]
            
            return HandlerResult(success=True, chunks=chunks, metadata={
                    "platform": "sap",
                    "artifact_type": "cds",
                    "entities": entities,
                })
        except Exception as e:
            logger.warning(f"CDS parsing failed for {path}: {e}")
            return HandlerResult(success=False, chunks=[], error=str(e))


class CAPPackageHandler(Handler):
    """Handler for SAP CAP package.json."""
    
    async def handle(
        self,
        content: bytes,
        path: str,
        metadata: Dict[str, Any],
    ) -> HandlerResult:
        """Parse SAP CAP package.json."""
        try:
            data = json.loads(content)
            
            # Extract CAP-specific metadata
            name = data.get("name", "")
            version = data.get("version", "")
            cds = data.get("cds", {})
            
            # Extract dependencies
            deps = data.get("dependencies", {})
            dev_deps = data.get("devDependencies", {})
            
            chunks = [
                Chunk(
                    id=f"{path}:cap",
                    content=f"CAP Package: {name} v{version}\n"
                            f"Dependencies: {len(deps)}\n"
                            f"Dev Dependencies: {len(dev_deps)}",
                    chunk_index=0,
                    start_char=0,
                    end_char=500,
                    metadata={
                        "artifact_type": "cap_package",
                        "platform": "sap",
                        "name": name,
                        "version": version,
                    },
                )
            ]
            
            return HandlerResult(success=True, chunks=chunks, metadata={
                    "platform": "sap",
                    "artifact_type": "cap_package",
                    "name": name,
                })
        except Exception as e:
            logger.warning(f"CAP package parsing failed for {path}: {e}")
            return HandlerResult(success=False, chunks=[], error=str(e))


class SecurityConfigHandler(Handler):
    """Handler for SAP XSUAA security configuration."""
    
    async def handle(
        self,
        content: bytes,
        path: str,
        metadata: Dict[str, Any],
    ) -> HandlerResult:
        """Parse xs-security.json."""
        try:
            data = json.loads(content)
            
            # Extract security config
            xsappname = data.get("xsappname", "")
            scopes = data.get("scopes", [])
            role_templates = data.get("role-templates", [])
            authorities = data.get("authorities", [])
            
            chunks = [
                Chunk(
                    id=f"{path}:security",
                    content=f"Security: {xsappname}\n"
                            f"Scopes: {len(scopes)}\n"
                            f"Role Templates: {len(role_templates)}",
                    chunk_index=0,
                    start_char=0,
                    end_char=500,
                    metadata={
                        "artifact_type": "security",
                        "platform": "sap",
                        "xsappname": xsappname,
                    },
                )
            ]
            
            return HandlerResult(success=True, chunks=chunks, metadata={
                    "platform": "sap",
                    "artifact_type": "security",
                    "xsappname": xsappname,
                })
        except Exception as e:
            logger.warning(f"Security config parsing failed for {path}: {e}")
            return HandlerResult(success=False, chunks=[], error=str(e))