class TestGitPipeline:
    def test_git_pipeline_exists(self):
        from git.pipeline import GitIngestionPipeline

        assert GitIngestionPipeline is not None


class TestTelemetryPipeline:
    def test_telemetry_pipeline_exists(self):
        from ingestion.telemetry.pipeline import TelemetryIngestionPipeline

        assert TelemetryIngestionPipeline is not None


class TestArchitecturePipeline:
    def test_architecture_pipeline_exists(self):
        from ingestion.architecture.pipeline import ArchitectureIngestionPipeline

        assert ArchitectureIngestionPipeline is not None


class TestTicketPipeline:
    def test_ticket_pipeline_exists(self):
        from ingestion.ticket.pipeline import TicketIngestionPipeline

        assert TicketIngestionPipeline is not None


class TestRequirementsPipeline:
    def test_requirements_pipeline_exists(self):
        from ingestion.pipeline import IngestionJob, JobRegistry

        assert IngestionJob is not None
        assert JobRegistry is not None


class TestKBPipeline:
    def test_kb_pipeline_exists(self):
        from ingestion.knowledge_base.pipeline import KnowledgeBaseIngestionPipeline

        assert KnowledgeBaseIngestionPipeline is not None
