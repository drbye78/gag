import hashlib
import yaml
from typing import Any, Dict, List
from dataclasses import dataclass

from ingestion.chunker import Chunk, ChunkResult, TextChunker


K8S_KINDS = [
    "Deployment", "Service", "ConfigMap", "Secret", "Pod", "ReplicaSet",
    "StatefulSet", "DaemonSet", "Job", "CronJob", "Ingress", "PersistentVolume",
    "PersistentVolumeClaim", "Namespace", "ServiceAccount", "Role", "RoleBinding",
]


@dataclass
class K8sResource:
    kind: str
    name: str
    namespace: str
    content: str


class KubernetesChunker(TextChunker):
    def __init__(self, chunk_size: int = 2000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str, source_id: str) -> ChunkResult:
        import time
        start = time.time()

        documents = self._split_yaml_documents(text)
        chunks = []

        for idx, doc in enumerate(documents):
            if not doc.strip():
                continue

            entity = self._parse_k8s_document(doc)
            chunk_id = self._make_chunk_id(source_id, idx)
            chunks.append(Chunk(
                id=chunk_id,
                content=doc,
                chunk_index=idx,
                start_char=0,
                end_char=len(doc),
                metadata={"kind": entity.kind, "name": entity.name, "namespace": entity.namespace},
            ))

        took = int((time.time() - start) * 1000)
        return ChunkResult(
            source_id=source_id,
            source_type="kubernetes",
            chunks=chunks,
            total_chars=len(text),
            took_ms=took,
        )

    def _split_yaml_documents(self, content: str) -> List[str]:
        documents = []
        current = []

        for line in content.split("\n"):
            if line.strip() == "---":
                if current:
                    documents.append("\n".join(current))
                    current = []
            else:
                current.append(line)

        if current:
            documents.append("\n".join(current))

        return documents

    def _parse_k8s_document(self, content: str) -> K8sResource:
        try:
            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                return K8sResource(kind="Unknown", name="unknown", namespace="default", content=content)

            kind = data.get("kind", "Unknown")
            metadata = data.get("metadata", {})
            name = metadata.get("name", "unknown")
            namespace = metadata.get("namespace", "default")

            return K8sResource(kind=kind, name=name, namespace=namespace, content=content)
        except yaml.YAMLError:
            return K8sResource(kind="Unknown", name="unknown", namespace="default", content=content)

    def _make_chunk_id(self, source_id: str, chunk_idx: int) -> str:
        raw = f"{source_id}:{chunk_idx}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_kubernetes_chunker() -> KubernetesChunker:
    return KubernetesChunker()