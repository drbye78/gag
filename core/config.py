"""
Configuration management for the Engineering Intelligence System.

Provides centralized settings loaded from environment variables with sensible defaults.
Uses Pydantic Settings for validation and type safety.
"""

import os
import logging
import warnings
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, model_validator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pydantic Settings with validation and type safety."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    debug: bool = False
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    falkordb_host: str = "localhost"
    falkordb_port: int = 7379
    falkordb_user: str = ""
    falkordb_pass: str = ""

    redis_url: str = "redis://localhost:6379"

    llm_provider: str = "openrouter"
    llm_model: str = "qwen-max"
    llm_api_key: str = ""

    embedding_provider: str = "openai"
    openai_api_key: str = ""
    dashscope_api_key: str = ""
    ollama_host: str = "http://localhost:11434"
    qwen_api_key: str = ""
    anthropic_api_key: str = ""
    vlm_provider: str = ""

    rerank_provider: str = "cohere"
    rerank_strategy: str = "single"
    rerank_top_k: int = 10
    rerank_min_score: float = 0.3
    cohere_api_key: str = ""
    jina_api_key: str = ""

    citation_style: str = "parenthetical"
    citation_include_scores: bool = True

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60

    @field_validator('jwt_secret', mode='before')
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if not v or v == "change-me-in-production":
            import os
            import sys
            if os.getenv("DEBUG", "").lower() not in ["true", "1", "yes"]:
                print("FATAL: JWT_SECRET must be set in production mode", file=sys.stderr)
                print("FATAL: Set JWT_SECRET environment variable to a secure random value", file=sys.stderr)
                sys.exit(78)  # EX_CONFIG
        return v

    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    cors_origins: str = "*"

    ticket_backend: str = ""
    telemetry_backend: str = ""
    docs_backend: str = ""

    jira_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""

    github_owner: str = ""
    github_repo: str = ""
    github_token: str = ""
    gitlab_token: str = ""

    azure_devops_username: str = ""
    azure_devops_token: str = ""

    credential_encrypt_key: str = ""

    confluence_url: str = ""
    confluence_email: str = ""
    confluence_api_token: str = ""

    webdav_url: str = ""
    webdav_user: str = ""
    webdav_pass: str = ""

    default_language: str = "auto"
    enable_language_detection: bool = True
    russian_model: str = "text-embedding-v3"

    prometheus_url: str = "http://localhost:9090"
    prometheus_user: str = ""
    prometheus_password: str = ""

    elastic_url: str = "http://localhost:9200"
    elastic_user: str = ""
    elastic_pass: str = ""
    elastic_api_key: str = ""

    loki_url: str = "http://localhost:3100"
    loki_token: str = ""

    stackoverflow_api_key: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    forum_base_url: str = ""
    forum_api_key: str = ""

    requirements_path: str = "requirements"

    max_workers: int = 4
    request_timeout: int = 60

    enable_metrics: bool = True
    enable_tracing: bool = False

    otel_service_name: str = "eis"
    otel_exporter_otlp_endpoint: str = ""
    otel_exporter_otlp_insecure: bool = True
    otel_exporter_console: bool = False
    otel_trace_sampler: str = "parent"

    entity_aware_max_hops: int = 3
    iterative_max_iterations: int = 3
    iterative_confidence_threshold: float = 0.7

    graphrag_enabled: bool = Field(default=False, validation_alias="GRAPH_RAG_ENABLED")
    graphrag_use_llm_extraction: bool = Field(default=False, validation_alias="GRAPH_RAG_USE_LLM")
    graphrag_structural_chunking: bool = Field(default=True, validation_alias="GRAPH_RAG_STRUCTURAL_CHUNKING")
    graphrag_incremental: bool = Field(default=True, validation_alias="GRAPH_RAG_INCREMENTAL")
    graphrag_community_detection: bool = Field(default=True, validation_alias="GRAPH_RAG_COMMUNITY_DETECTION")
    graphrag_max_entities: int = Field(default=100, validation_alias="GRAPH_RAG_MAX_ENTITIES")
    graphrag_default_hops: int = Field(default=3, validation_alias="GRAPH_RAG_DEFAULT_HOPS")
    graphrag_entity_types: str = Field(default="PERSON,ORGANIZATION,CONCEPT,EVENT,LOCATION,PRODUCT,TECHNOLOGY,DOCUMENT,PROCESS", validation_alias="GRAPH_RAG_ENTITY_TYPES")
    graphrag_relationship_types: str = Field(default="RELATED_TO,PART_OF,WORKS_FOR,LOCATED_AT,USES,DEPENDS_ON,CREATED_BY,DEFINED_IN,REFERENCES,CONTAINS,IMPLEMENTS,MANAGES", validation_alias="GRAPH_RAG_RELATIONSHIP_TYPES")

    chunking_chunker_type: str = "semantic"
    chunking_semantic_threshold: float = 0.5
    chunking_semantic_embed_model: str = "BAAI/bge-small-en-v1.5"
    chunking_sentence_size: int = 1024
    chunking_sentence_overlap: int = 20
    chunking_code_max_lines: int = 100
    chunking_min_length: int = 50
    chunking_max_length: int = 2048

    colbert_enabled: bool = False
    colbert_model_name: str = "colbert-ir/colbertv2.0"
    colbert_max_length: int = 512
    colbert_top_k: int = 10
    colbert_rerank: bool = True

    retrieval_default_strategy: str = "hybrid"
    retrieval_fusion_method: str = "rrf"
    retrieval_parallel: bool = True
    retrieval_timeout: int = 30
    retrieval_fallback: bool = True

    diagram_index_enabled: bool = False
    diagram_collection: str = "diagrams"
    diagram_vector_size: int = 384

    ui_sketch_enabled: bool = False
    colpali_enabled: bool = False

    @model_validator(mode="after")
    def _post_validate(self):
        if self.jwt_secret == "change-me-in-production":
            raise ValueError(
                "SECURITY ERROR: JWT_SECRET is using the default placeholder value. "
                "Set JWT_SECRET to a strong random value before deploying to production."
            )
        if not self.credential_encrypt_key:
            warnings.warn(
                "SECURITY WARNING: CREDENTIAL_ENCRYPT_KEY is not set. "
                "Git credential encryption will be disabled.",
                RuntimeWarning,
                stacklevel=2,
            )
        return self


_settings: Optional["Settings"] = None


def get_settings() -> "Settings":
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset the singleton (primarily for testing)."""
    global _settings
    _settings = None


def setup_logging() -> logging.Logger:
    settings = get_settings()

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger("config")
    logger.debug("Logging configured at level: %s", settings.log_level)
    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
