import hashlib
import logging
import os
from typing import Any, Dict, List

from ingestion.k8s_chunker import KubernetesChunker, K8sResource
from ingestion.helm_chunker import HelmChartChunker
from ingestion.dockerfile_chunker import DockerfileChunker
from ingestion.istio_chunker import IstioChunker

from unified_ingestion.handlers.base import Handler, HandlerResult

logger = logging.getLogger(__name__)


class K8sHandler(Handler):
    EXTENSION_MAP = {
        ".yaml": "kubernetes",
        ".yml": "kubernetes",
        ".json": "kubernetes",
        "Dockerfile": "dockerfile",
        "dockerfile": "dockerfile",
        ".helm": "helm",
    }

    def __init__(self):
        self._k8s_chunker = KubernetesChunker()
        self._helm_chunker = HelmChartChunker()
        self._dockerfile_chunker = DockerfileChunker()
        self._istio_chunker = IstioChunker()

    async def handle(self, content: bytes, source_id: str, metadata: Dict[str, Any]) -> HandlerResult:
        filename = metadata.get("filename", "manifest")
        ext = os.path.splitext(filename)[1].lower()

        if "dockerfile" in filename.lower():
            return await self._handle_dockerfile(content, source_id, filename)

        is_chart = self._detect_helm_chart(filename)
        if is_chart:
            return await self._handle_helm(content, source_id, filename)

        if ext in (".yaml", ".yml", ".json"):
            text = content.decode("utf-8")
            if self._is_istio_resource(text):
                return await self._handle_istio(content, source_id, filename)
            return await self._handle_kubernetes(content, source_id, filename)

        return HandlerResult(success=False, error=f"Unknown K8s type: {filename}")

    async def _handle_kubernetes(
        self, content: bytes, source_id: str, filename: str
    ) -> HandlerResult:
        text = content.decode("utf-8")
        chunker = self._k8s_chunker
        result = chunker.chunk(text, source_id)

        chunks = []
        for chunk in result.chunks:
            chunk_id = hashlib.sha256(f"{source_id}:{chunk.chunk_index}".encode()).hexdigest()[:16]
            chunks.append(
                {
                    "id": chunk_id,
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "metadata": {
                        "source_id": source_id,
                        "filename": filename,
                        "kind": chunk.metadata.get("kind"),
                        "name": chunk.metadata.get("name"),
                        "namespace": chunk.metadata.get("namespace"),
                    },
                }
            )

        return HandlerResult(success=True, chunks=chunks, metadata={})

    async def _handle_helm(
        self, content: bytes, source_id: str, filename: str
    ) -> HandlerResult:
        text = content.decode("utf-8")
        chunker = self._helm_chunker
        result = chunker.chunk(text, source_id)

        chunks = []
        for chunk in result.chunks:
            chunk_id = hashlib.sha256(f"{source_id}:{chunk.chunk_index}".encode()).hexdigest()[:16]
            chunks.append(
                {
                    "id": chunk_id,
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "metadata": {
                        "source_id": source_id,
                        "filename": filename,
                        **chunk.metadata,
                    },
                }
            )

        return HandlerResult(success=True, chunks=chunks, metadata={})

    async def _handle_dockerfile(
        self, content: bytes, source_id: str, filename: str
    ) -> HandlerResult:
        text = content.decode("utf-8")
        chunker = self._dockerfile_chunker
        result = chunker.chunk(text, source_id)

        chunks = []
        for chunk in result.chunks:
            chunk_id = hashlib.sha256(f"{source_id}:{chunk.chunk_index}".encode()).hexdigest()[:16]
            chunks.append(
                {
                    "id": chunk_id,
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "metadata": {
                        "source_id": source_id,
                        "filename": filename,
                        "instruction": chunk.metadata.get("instruction"),
                    },
                }
            )

        return HandlerResult(success=True, chunks=chunks, metadata={})

    async def _handle_istio(
        self, content: bytes, source_id: str, filename: str
    ) -> HandlerResult:
        text = content.decode("utf-8")
        chunker = self._istio_chunker
        result = chunker.chunk(text, source_id)

        chunks = []
        for chunk in result.chunks:
            chunk_id = hashlib.sha256(f"{source_id}:{chunk.chunk_index}".encode()).hexdigest()[:16]
            chunks.append(
                {
                    "id": chunk_id,
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "metadata": {
                        "source_id": source_id,
                        "filename": filename,
                        "kind": chunk.metadata.get("kind"),
                    },
                }
            )

        return HandlerResult(success=True, chunks=chunks, metadata={})

    def _detect_helm_chart(self, filename: str) -> bool:
        return "chart" in filename.lower() or filename in ("Chart.yaml", "values.yaml")

    def _is_istio_resource(self, text: str) -> bool:
        from ingestion.istio_chunker import ISTIO_KINDS

        for kind in ISTIO_KINDS:
            if f"kind: {kind}" in text:
                return True
        return False