import hashlib
import re
from typing import Any, Dict, List
from dataclasses import dataclass

from ingestion.chunker import Chunk, ChunkResult, TextChunker


ISTIO_KINDS = [
    "VirtualService",
    "DestinationRule", 
    "Gateway",
    "ServiceEntry",
    "EnvoyFilter",
    "Sidecar",
    "AuthorizationPolicy",
    "RequestAuthentication",
    "PeerAuthentication",
    "Telemetry",
    "ProxyConfig",
    "WasmPlugin",
    "GrpcWebPlugin",
    "DestinationRule",
    "EnvoyFilter",
    "HTTPAPISpec",
    "HTTPAPISpecBinding",
    "QuotaSpec",
    "QuotaSpecBinding",
    "RateLimitRequest",
    "RateLimitDescriptor",
    "ClusterLocalService",
    "MutualTLS",
    "JWTRule",
]


@dataclass
class IstioResource:
    kind: str
    name: str
    namespace: str
    api_version: str
    content: str
    hosts: List[str]
    gateways: List[str]


class IstioChunker(TextChunker):
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

            entity = self._parse_istio_document(doc)
            chunk_id = self._make_chunk_id(source_id, idx)
            chunks.append(Chunk(
                id=chunk_id,
                content=doc,
                chunk_index=idx,
                start_char=0,
                end_char=len(doc),
                metadata={
                    "kind": entity.kind,
                    "name": entity.name,
                    "namespace": entity.namespace,
                    "api_version": entity.api_version,
                    "hosts": entity.hosts,
                    "gateways": entity.gateways,
                },
            ))

        took = int((time.time() - start) * 1000)
        return ChunkResult(
            source_id=source_id,
            source_type="istio",
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

    def _parse_istio_document(self, content: str) -> IstioResource:
        lines = content.split("\n")
        kind = "Unknown"
        name = "unknown"
        namespace = "default"
        api_version = "networking.istio.io/v1beta1"
        hosts = []
        gateways = []

        for line in lines:
            stripped = line.strip()
            
            if stripped.startswith("kind:"):
                kind_val = stripped.split(":", 1)[1].strip()
                if kind_val in ISTIO_KINDS:
                    kind = kind_val
            elif stripped.startswith("name:"):
                name = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("namespace:"):
                namespace = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("apiVersion:"):
                api_version = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("hosts:"):
                hosts_match = re.findall(r"-\s*(.+)", stripped)
                if hosts_match:
                    hosts.extend([h.strip().strip('"') for h in hosts_match])
            elif stripped.startswith("gateways:"):
                gw_match = re.findall(r"-\s*(.+)", stripped)
                if gw_match:
                    gateways.extend([g.strip().strip('"') for g in gw_match])

        if "hosts:" in content:
            for match in re.finditer(r"hosts:\s*\n\s*-\s*(.+?)\n", content, re.MULTILINE):
                hosts.append(match.group(1).strip().strip('"'))
        
        if "gateways:" in content:
            for match in re.finditer(r"gateways:\s*\n\s*-\s*(.+?)\n", content, re.MULTILINE):
                gateways.append(match.group(1).strip().strip('"'))

        return IstioResource(
            kind=kind,
            name=name,
            namespace=namespace,
            api_version=api_version,
            content=content,
            hosts=hosts,
            gateways=gateways,
        )

    def _make_chunk_id(self, source_id: str, chunk_idx: int) -> str:
        raw = f"{source_id}:{chunk_idx}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_istio_chunker() -> IstioChunker:
    return IstioChunker()