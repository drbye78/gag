class TestDockerfileChunker:
    def test_dockerfile_chunker_import(self):
        from ingestion.dockerfile_chunker import DockerfileChunker

        assert DockerfileChunker is not None


class TestK8sChunker:
    def test_k8s_chunker_import(self):
        from ingestion.k8s_chunker import KubernetesChunker

        assert KubernetesChunker is not None


class TestGraphQLChunker:
    def test_graphql_chunker_import(self):
        from ingestion.graphql_chunker import GraphQLChunker

        assert GraphQLChunker is not None


class TestIstioChunker:
    def test_istio_chunker_import(self):
        from ingestion.istio_chunker import IstioChunker

        assert IstioChunker is not None


class TestHelmChunker:
    def test_helm_chunker_import(self):
        from ingestion.helm_chunker import HelmChartChunker

        assert HelmChartChunker is not None
