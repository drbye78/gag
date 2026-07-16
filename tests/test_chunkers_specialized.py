"""
Tests for specialized chunkers: Dockerfile, Helm, and Istio.

Tests verify that each chunker correctly parses and chunks its specific
file format, extracting the appropriate metadata and structure.
"""

import pytest

from ingestion.chunker import ChunkResult
from ingestion.dockerfile_chunker import DockerfileChunker
from ingestion.helm_chunker import HelmChartChunker
from ingestion.istio_chunker import IstioChunker


class TestDockerfileChunker:
    """Tests for DockerfileChunker."""

    @pytest.fixture
    def chunker(self):
        return DockerfileChunker()

    def test_chunk_parses_instructions(self, chunker):
        """Test that DockerfileChunker parses all Dockerfile instructions."""
        dockerfile_content = """FROM python:3.12-slim
RUN apt-get update && apt-get install -y curl
RUN pip install fastapi uvicorn
COPY . /app
WORKDIR /app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
EXPOSE 8000
ENV PYTHONUNBUFFERED=1
"""
        result = chunker.chunk(dockerfile_content, "test-dockerfile")

        # Verify result structure
        assert isinstance(result, ChunkResult)
        assert result.source_id == "test-dockerfile"
        assert result.source_type == "dockerfile"
        assert result.total_chars > 0

        # Should have chunks for each instruction type found
        assert len(result.chunks) > 0

        # Verify each chunk has the expected structure
        for chunk in result.chunks:
            assert chunk.id is not None
            assert chunk.content is not None
            assert chunk.chunk_index >= 0
            assert "instruction" in chunk.metadata
            assert "count" in chunk.metadata

    def test_chunk_groups_by_type(self, chunker):
        """Test that instructions are grouped by type."""
        dockerfile_content = """FROM python:3.12
FROM alpine:latest
RUN echo "first run"
RUN echo "second run"
RUN echo "third run"
CMD ["echo", "a"]
CMD ["echo", "b"]
ENV A=1
ENV B=2
ENV C=3
"""
        result = chunker.chunk(dockerfile_content, "test-grouped")

        # Verify groups: FROM=2, RUN=3, CMD=2, ENV=3
        instruction_groups = {chunk.metadata["instruction"]: chunk.metadata["count"] for chunk in result.chunks}

        assert "FROM" in instruction_groups
        assert instruction_groups["FROM"] == 2
        assert "RUN" in instruction_groups
        assert instruction_groups["RUN"] == 3
        assert "CMD" in instruction_groups
        assert instruction_groups["CMD"] == 2
        assert "ENV" in instruction_groups
        assert instruction_groups["ENV"] == 3

        # Verify content format includes grouped arguments
        for chunk in result.chunks:
            assert chunk.content.startswith(chunk.metadata["instruction"] + ":")


class TestHelmChunker:
    """Tests for HelmChartChunker."""

    @pytest.fixture
    def chunker(self):
        return HelmChartChunker()

    def test_chunk_extracts_chart_yaml(self, chunker):
        """Test that HelmChartChunker extracts Chart.yaml metadata."""
        helm_content = """apiVersion: v2
name: my-app
version: 1.0.0
description: A Helm chart for my application
type: application
kubeVersion: ">=1.20.0"
"""
        result = chunker.chunk(helm_content, "test-chart")

        # Verify result structure
        assert isinstance(result, ChunkResult)
        assert result.source_id == "test-chart"
        assert result.source_type == "helm"
        assert result.total_chars > 0

        # Should have at least the chart metadata chunk
        chunks = result.chunks
        assert len(chunks) > 0

        # Find the chart metadata chunk
        chart_chunk = None
        for chunk in chunks:
            if chunk.metadata.get("type") == "chart_metadata":
                chart_chunk = chunk
                break

        assert chart_chunk is not None, "Chart metadata chunk not found"
        assert "name" in chart_chunk.metadata
        assert "version" in chart_chunk.metadata
        assert chart_chunk.metadata["name"] == "my-app"
        assert chart_chunk.metadata["version"] == "1.0.0"

    def test_chunk_extracts_values(self, chunker):
        """Test that HelmChartChunker extracts values.yaml content."""
        helm_content = """apiVersion: v2
name: my-app
version: 2.0.0

replicaCount: 3

image:
  repository: myregistry/myapp
  pullPolicy: IfNotPresent
  tag: "latest"

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: myapp.example.com
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 500m
    memory: 512Mi
"""
        result = chunker.chunk(helm_content, "test-values")

        # Verify values chunk exists
        chunks = result.chunks
        values_chunk = None
        for chunk in chunks:
            if chunk.metadata.get("type") == "values":
                values_chunk = chunk
                break

        assert values_chunk is not None, "Values chunk not found"
        assert values_chunk.content is not None
        # Values should contain key entries from the values
        assert "replicaCount:" in values_chunk.content or "image:" in values_chunk.content


class TestIstioChunker:
    """Tests for IstioChunker."""

    @pytest.fixture
    def chunker(self):
        return IstioChunker()

    def test_chunk_extracts_virtual_service(self, chunker):
        """Test that IstioChunker extracts VirtualService resources."""
        istio_content = """apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: my-service
  namespace: default
spec:
  hosts:
    - myapp.example.com
  gateways:
    - my-gateway
  http:
    - match:
        - uri:
            prefix: /api
      route:
        - destination:
            host: my-service.default.svc.cluster.local
            port:
              number: 8080
    - route:
        - destination:
            host: my-service.default.svc.cluster.local
            port:
              number: 80
"""
        result = chunker.chunk(istio_content, "test-vs")

        # Verify result structure
        assert isinstance(result, ChunkResult)
        assert result.source_id == "test-vs"
        assert result.source_type == "istio"
        assert result.total_chars > 0

        # Should have at least one chunk for the VirtualService
        chunks = result.chunks
        assert len(chunks) > 0

        # Find the VirtualService chunk
        vs_chunk = None
        for chunk in chunks:
            if chunk.metadata.get("kind") == "VirtualService":
                vs_chunk = chunk
                break

        assert vs_chunk is not None, "VirtualService chunk not found"
        assert vs_chunk.metadata["name"] == "my-service"
        assert vs_chunk.metadata["namespace"] == "default"
        assert "myapp.example.com" in vs_chunk.metadata.get("hosts", [])
        assert "my-gateway" in vs_chunk.metadata.get("gateways", [])

    def test_chunk_extracts_destination_rule(self, chunker):
        """Test that IstioChunker extracts DestinationRule resources."""
        istio_content = """apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: my-service-dr
  namespace: default
spec:
  host: my-service.default.svc.cluster.local
  trafficPolicy:
    connectionPool:
      http:
        h2UpgradePolicy: upgrade
        http1MaxPendingRequests: 100
        http2MaxRequests: 1000
    loadBalancer:
      simple: LEAST_REQUEST
    tls:
      mode: ISTIO_MUTUAL
  subsets:
    - name: v1
      labels:
        version: v1
    - name: v2
      labels:
        version: v2
"""
        result = chunker.chunk(istio_content, "test-dr")

        # Verify result structure
        chunks = result.chunks
        assert len(chunks) > 0

        # Find the DestinationRule chunk
        dr_chunk = None
        for chunk in chunks:
            if chunk.metadata.get("kind") == "DestinationRule":
                dr_chunk = chunk
                break

        assert dr_chunk is not None, "DestinationRule chunk not found"
        assert dr_chunk.metadata["name"] == "my-service-dr"
        assert dr_chunk.metadata["namespace"] == "default"
        assert dr_chunk.metadata["kind"] == "DestinationRule"

    def test_chunk_multiple_documents(self, chunker):
        """Test that IstioChunker handles multiple YAML documents."""
        istio_content = """apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: my-gateway
  namespace: default
spec:
  selector:
    istio: ingressgateway
  servers:
    - port:
        number: 80
        name: http
        protocol: HTTP
      hosts:
        - "*"
---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: my-vs
  namespace: default
spec:
  hosts:
    - myapp.example.com
  http:
    - route:
        - destination:
            host: myapp.default.svc.cluster.local
            port:
              number: 80
"""
        result = chunker.chunk(istio_content, "test-multi")

        # Should have 2 chunks (one per document)
        assert len(result.chunks) == 2

        kinds = {chunk.metadata.get("kind") for chunk in result.chunks}
        assert "Gateway" in kinds
        assert "VirtualService" in kinds
