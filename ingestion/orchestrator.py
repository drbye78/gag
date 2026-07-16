"""
Ingestion Orchestrator - Unified pipeline coordination.

Coordinates all ingestion pipelines:
- Git repositories
- Documents
- Tickets (Jira, GitHub Issues)
- Telemetry (Prometheus, Elasticsearch, Loki)
- Knowledge Base (StackOverflow, Reddit, Forums)
- Architecture Diagrams
- Business Requirements
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from ingestion.pipeline import get_ingestion_pipeline
from git.pipeline import GitIngestionPipeline, get_git_pipeline
from documents.pipeline import DocumentPipeline, get_document_pipeline
from ingestion.ticket.pipeline import TicketIngestionPipeline, get_ticket_pipeline
from ingestion.telemetry.pipeline import (
    TelemetryIngestionPipeline,
    get_telemetry_pipeline,
)
from ingestion.knowledge_base.pipeline import (
    KnowledgeBaseIngestionPipeline,
    get_kb_pipeline,
)
from ingestion.architecture.pipeline import (
    ArchitectureIngestionPipeline,
    get_architecture_pipeline,
)
from ingestion.requirements.pipeline import (
    RequirementsIngestionPipeline,
    get_requirements_pipeline,
)


class IngestionSource(str, Enum):
    GIT = "git"
    DOCUMENTS = "documents"
    TICKETS = "tickets"
    TELEMETRY = "telemetry"
    KNOWLEDGE_BASE = "knowledge_base"
    ARCHITECTURE = "architecture"
    REQUIREMENTS = "requirements"


class IngestionMode(str, Enum):
    INCREMENTAL = "incremental"
    FULL = "full"
    SCHEDULED = "scheduled"


class IngestionCoordinator:
    def __init__(self):
        self.git_pipeline = get_git_pipeline()
        self.document_pipeline = get_document_pipeline()
        self.ticket_pipeline = get_ticket_pipeline()
        self.telemetry_pipeline = get_telemetry_pipeline()
        self.kb_pipeline = get_kb_pipeline()
        self.architecture_pipeline = get_architecture_pipeline()
        self.requirements_pipeline = get_requirements_pipeline()
        self.generic_pipeline = get_ingestion_pipeline()

    async def ingest_all(
        self,
        sources: Optional[List[IngestionSource]] = None,
        mode: IngestionMode = IngestionMode.INCREMENTAL,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ingest all configured sources.

        Args:
            sources: List of source types to ingest. Defaults to all sources.
            mode: Ingestion mode (incremental, full, scheduled).
            config: Per-source configuration dict. Keys should match source enum values.
                    Example: {"git": {"repo_url": "...", "branch": "main"}}
        """
        if not sources:
            sources = list(IngestionSource)

        config = config or {}
        results = {}

        for source in sources:
            try:
                source_config = config.get(source.value, {})

                if source == IngestionSource.GIT:
                    repo_url = source_config.get("repo_url")
                    if not repo_url:
                        results[source.value] = {"error": "repo_url not configured"}
                        continue
                    job = await self.git_pipeline.ingest_repository(
                        repo_url=repo_url,
                        branch=source_config.get("branch", "main"),
                    )
                    results[source.value] = {
                        "job_id": job.job_id,
                        "status": job.status.value,
                    }

                elif source == IngestionSource.DOCUMENTS:
                    content = source_config.get("content")
                    filename = source_config.get("filename", "document.md")
                    if not content:
                        results[source.value] = {"error": "content not configured"}
                        continue
                    doc = await self.document_pipeline.upload_document(
                        content=content.encode() if isinstance(content, str) else content,
                        filename=filename,
                    )
                    results[source.value] = {"document_id": doc.document_id}

                elif source == IngestionSource.TICKETS:
                    job = await self.ticket_pipeline.ingest_jira(
                        jql=source_config.get("jql"),
                        max_results=source_config.get("max_results", 100),
                    )
                    results[source.value] = {
                        "job_id": job.job_id,
                        "status": job.status.value,
                    }

                elif source == IngestionSource.TELEMETRY:
                    query = source_config.get("query", "{app=~.*}")
                    job = await self.telemetry_pipeline.ingest_loki_logs(
                        query=query
                    )
                    results[source.value] = {
                        "job_id": job.job_id,
                        "status": job.status.value,
                    }

                elif source == IngestionSource.KNOWLEDGE_BASE:
                    query = source_config.get("query", "SAP BTP")
                    job = await self.kb_pipeline.ingest_stackoverflow(query=query)
                    results[source.value] = {
                        "job_id": job.job_id,
                        "status": job.status.value,
                    }

                elif source == IngestionSource.ARCHITECTURE:
                    directory = source_config.get("directory", "./docs/architecture")
                    job = await self.architecture_pipeline.ingest_local(
                        directory=directory
                    )
                    results[source.value] = {
                        "job_id": job.job_id,
                        "status": job.status.value,
                    }

                elif source == IngestionSource.REQUIREMENTS:
                    job = await self.requirements_pipeline.ingest_jira(
                        jql=source_config.get("jql"),
                    )
                    results[source.value] = {
                        "job_id": job.job_id,
                        "status": job.status.value,
                    }

            except Exception as e:
                results[source.value] = {"error": str(e)}

        return {
            "sources": [s.value for s in sources],
            "mode": mode.value,
            "results": results,
        }

    async def run_ingestion_job(
        self,
        source: IngestionSource,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        if source == IngestionSource.GIT:
            job = await self.git_pipeline.ingest_repository(
                repo_url=config.get("repo_url", ""),
                branch=config.get("branch", "main"),
            )
            return {
                "job_id": job.job_id,
                "status": job.status.value,
                "entities": job.total_entities,
            }

        elif source == IngestionSource.DOCUMENTS:
            doc = await self.document_pipeline.upload_document(
                content=config.get("content", "").encode(),
                filename=config.get("filename", "document.md"),
            )
            return {"document_id": doc.document_id}

        elif source == IngestionSource.TICKETS:
            ticket_source = config.get("ticket_source", "jira")
            if ticket_source == "jira":
                job = await self.ticket_pipeline.ingest_jira(
                    jql=config.get("jql"),
                    max_results=config.get("max_results", 100),
                )
            else:
                job = await self.ticket_pipeline.ingest_github(
                    owner=config.get("owner"),
                    repo=config.get("repo"),
                    state=config.get("state", "all"),
                    max_results=config.get("max_results", 100),
                )
            return {
                "job_id": job.job_id,
                "status": job.status.value,
                "tickets": job.ticket_count,
            }

        elif source == IngestionSource.TELEMETRY:
            tel_source = config.get("telemetry_source", "loki")
            if tel_source == "prometheus":
                job = await self.telemetry_pipeline.ingest_prometheus_metrics(
                    query=config.get("query", "up"),
                )
            elif tel_source == "elasticsearch":
                job = await self.telemetry_pipeline.ingest_elasticsearch_logs(
                    query=config.get("query", "*"),
                    level=config.get("level"),
                    service=config.get("service"),
                )
            else:
                job = await self.telemetry_pipeline.ingest_loki_logs(
                    query=config.get("query", "{*}"),
                )
            return {
                "job_id": job.job_id,
                "status": job.status.value,
                "logs": job.log_count,
                "metrics": job.metric_count,
            }

        elif source == IngestionSource.KNOWLEDGE_BASE:
            kb_source = config.get("kb_source", "stackoverflow")
            if kb_source == "stackoverflow":
                job = await self.kb_pipeline.ingest_stackoverflow(
                    query=config.get("query", ""),
                )
            elif kb_source == "reddit":
                job = await self.kb_pipeline.ingest_reddit(
                    subreddit=config.get("subreddit", "programming"),
                    query=config.get("query", ""),
                )
            else:
                job = await self.kb_pipeline.ingest_forum(
                    query=config.get("query", ""),
                )
            return {
                "job_id": job.job_id,
                "status": job.status.value,
                "entries": job.entry_count,
            }

        elif source == IngestionSource.ARCHITECTURE:
            arch_source = config.get("arch_source", "local")
            if arch_source == "confluence":
                job = await self.architecture_pipeline.ingest_confluence(
                    space_key=config.get("space_key", "ARCH"),
                )
            elif arch_source == "github":
                job = await self.architecture_pipeline.ingest_github(
                    repo=config.get("repo", ""),
                )
            else:
                job = await self.architecture_pipeline.ingest_local(
                    directory=config.get("directory", "./docs"),
                )
            return {
                "job_id": job.job_id,
                "status": job.status.value,
                "diagrams": job.diagram_count,
            }

        elif source == IngestionSource.REQUIREMENTS:
            req_source = config.get("req_source", "jira")
            if req_source == "jira":
                job = await self.requirements_pipeline.ingest_jira()
            elif req_source == "confluence":
                job = await self.requirements_pipeline.ingest_confluence(
                    space_key=config.get("space_key", "REQ"),
                )
            else:
                job = await self.requirements_pipeline.ingest_local()
            return {
                "job_id": job.job_id,
                "status": job.status.value,
                "requirements": job.req_count,
            }

        return {"error": f"Unknown source: {source}"}

    def get_pipeline_status(self) -> Dict[str, Any]:
        return {
            "git": {"status": "available"},
            "documents": {"status": "available"},
            "tickets": {"jobs": self.ticket_pipeline.list_jobs()},
            "telemetry": {"jobs": self.telemetry_pipeline.list_jobs()},
            "knowledge_base": {"jobs": self.kb_pipeline.list_jobs()},
            "architecture": {"jobs": self.architecture_pipeline.list_jobs()},
            "requirements": {"jobs": self.requirements_pipeline.list_jobs()},
        }

    def list_available_sources(self) -> List[str]:
        return [s.value for s in IngestionSource]


_coordinator: Optional[IngestionCoordinator] = None


def get_ingestion_coordinator() -> IngestionCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = IngestionCoordinator()
    return _coordinator
