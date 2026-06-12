"""Platform adapter template for creating new platform handlers."""

import json
import logging
from typing import Any, Dict, List

from unified_ingestion.handlers.base import Chunk, Handler, HandlerResult
from unified_ingestion.platform import PlatformArtifactHandler

logger = logging.getLogger(__name__)


class MyPlatformArtifactHandler(PlatformArtifactHandler):
    """Handler for MyPlatform-specific artifacts."""

    def get_platform_id(self) -> str:
        return "myplatform"

    def get_supported_artifacts(self) -> List[str]:
        return ["myartifact1", "myartifact2"]

    async def handle(
        self,
        content: bytes,
        path: str,
        metadata: Dict[str, Any],
    ) -> HandlerResult:
        from unified_ingestion.handlers.platform.myplatform import (
            MyArtifact1Handler,
            MyArtifact2Handler,
        )

        filename = path.lower()

        if "artifact1" in filename:
            handler: Handler = MyArtifact1Handler()
        elif "artifact2" in filename:
            handler = MyArtifact2Handler()
        else:
            return HandlerResult(
                success=False, chunks=[], error=f"Unknown MyPlatform artifact: {path}"
            )

        return await handler.handle(content, path, metadata)


class MyArtifact1Handler(Handler):
    """Handler for MyPlatform artifact type 1."""

    async def handle(
        self,
        content: bytes,
        path: str,
        metadata: Dict[str, Any],
    ) -> HandlerResult:
        try:
            text = content.decode("utf-8", errors="ignore")
            data = json.loads(text)

            artifact_id = data.get("id", "unknown")
            version = data.get("version", "1.0.0")

            chunks = [
                Chunk(
                    id=f"{path}:artifact1",
                    content=f"MyPlatform Artifact1: {artifact_id}",
                    chunk_index=0,
                    start_char=0,
                    end_char=len(text),
                    metadata={
                        "artifact_type": "artifact1",
                        "platform": "myplatform",
                        "artifact_id": artifact_id,
                    },
                )
            ]

            return HandlerResult(
                success=True,
                chunks=chunks,
                metadata={
                    "platform": "myplatform",
                    "artifact_type": "artifact1",
                    "artifact_id": artifact_id,
                    "version": version,
                },
            )
        except Exception as e:
            logger.warning(f"Artifact1 parsing failed for {path}: {e}")
            return HandlerResult(success=False, chunks=[], error=str(e))


class MyArtifact2Handler(Handler):
    """Handler for MyPlatform artifact type 2."""

    async def handle(
        self,
        content: bytes,
        path: str,
        metadata: Dict[str, Any],
    ) -> HandlerResult:
        try:
            text = content.decode("utf-8", errors="ignore")
            return HandlerResult(
                success=True,
                chunks=[],
                metadata={"platform": "myplatform", "artifact_type": "artifact2"},
            )
        except Exception as e:
            logger.warning(f"Artifact2 parsing failed for {path}: {e}")
            return HandlerResult(success=False, chunks=[], error=str(e))
