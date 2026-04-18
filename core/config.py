"""
Configuration management for the Engineering Intelligence System.

Provides centralized settings loaded from environment variables with sensible defaults.
Supports configuration for API, databases, LLM providers, authentication, and rate limiting.
"""

import os
import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional


class Settings:
    """Central configuration class managing all system settings from environment variables."""

    def __init__(self):
        # --- General ---
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # --- API ---
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))

        # --- Vector DB (Qdrant) ---
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))

        # --- Graph DB (FalkorDB) ---
        self.falkordb_host = os.getenv("FALKORDB_HOST", "localhost")
        self.falkordb_port = int(os.getenv("FALKORDB_PORT", "7379"))
        self.falkordb_user = os.getenv("FALKORDB_USER", "")
        self.falkordb_pass = os.getenv("FALKORDB_PASS", "")

        # --- Redis ---
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        # --- LLM ---
        self.llm_provider = os.getenv("LLM_PROVIDER", "openrouter")
        self.llm_model = os.getenv("LLM_MODEL", "qwen-max")
        self.llm_api_key = os.getenv("LLM_API_KEY", "")

        # --- Embeddings ---
        self.embedding_provider = os.getenv("EMBEDDING_PROVIDER", "openai")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.dashscope_api_key = os.getenv("DASHSCOPE_API_KEY", "")
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.qwen_api_key = os.getenv("QWEN_API_KEY", "")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.vlm_provider = os.getenv("VLM_PROVIDER", "")

        # --- Reranking ---
        self.rerank_provider = os.getenv("RERANK_PROVIDER", "cohere")
        self.rerank_strategy = os.getenv("RERANK_STRATEGY", "single")
        self.rerank_top_k = int(os.getenv("RERANK_TOP_K", "10"))
        self.rerank_min_score = float(os.getenv("RERANK_MIN_SCORE", "0.3"))
        self.cohere_api_key = os.getenv("COHERE_API_KEY", "")
        self.jina_api_key = os.getenv("JINA_API_KEY", "")

        # --- Citations ---
        self.citation_style = os.getenv("CITATION_STYLE", "parenthetical")
        self.citation_include_scores = (
            os.getenv("CITATION_INCLUDE_SCORES", "true").lower() == "true"
        )

        # --- Auth / RBAC ---
        self.jwt_secret = os.getenv("JWT_SECRET", "change-me-in-production")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expiry_minutes = int(os.getenv("JWT_EXPIRY_MINUTES", "60"))

        self.rate_limit_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
        self.rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
        self.cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")

        # --- Backend selectors ---
        self.ticket_backend = os.getenv("TICKET_BACKEND", "")
        self.telemetry_backend = os.getenv("TELEMETRY_BACKEND", "")
        self.docs_backend = os.getenv("DOCS_BACKEND", "")

        # --- Jira ---
        self.jira_url = os.getenv("JIRA_URL", "")
        self.jira_email = os.getenv("JIRA_EMAIL", "")
        self.jira_api_token = os.getenv("JIRA_API_TOKEN", "")

        # --- GitHub ---
        self.github_owner = os.getenv("GITHUB_OWNER", "")
        self.github_repo = os.getenv("GITHUB_REPO", "")
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.gitlab_token = os.getenv("GITLAB_TOKEN", "")

        # --- Azure DevOps ---
        self.azure_devops_username = os.getenv("AZURE_DEVOPS_USERNAME", "")
        self.azure_devops_token = os.getenv("AZURE_DEVOPS_TOKEN", "")

        # --- Git credentials ---
        self.credential_encrypt_key = os.getenv("CREDENTIAL_ENCRYPT_KEY", "")

        # --- Confluence ---
        self.confluence_url = os.getenv("CONFLUENCE_URL", "")
        self.confluence_email = os.getenv("CONFLUENCE_EMAIL", "")
        self.confluence_api_token = os.getenv("CONFLUENCE_API_TOKEN", "")

        # --- WebDAV ---
        self.webdav_url = os.getenv("WEBDAV_URL", "")
        self.webdav_user = os.getenv("WEBDAV_USER", "")
        self.webdav_pass = os.getenv("WEBDAV_PASS", "")

        # --- Multilingual ---
        self.default_language = os.getenv("DEFAULT_LANGUAGE", "auto")
        self.enable_language_detection = (
            os.getenv("ENABLE_LANGUAGE_DETECTION", "true").lower() == "true"
        )
        self.russian_model = os.getenv("RUSSIAN_EMBEDDING_MODEL", "text-embedding-v3")

        # --- Prometheus ---
        self.prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
        self.prometheus_user = os.getenv("PROMETHEUS_USER", "")
        self.prometheus_password = os.getenv("PROMETHEUS_PASSWORD", "")

        # --- Elasticsearch ---
        self.elastic_url = os.getenv("ELASTIC_URL", "http://localhost:9200")
        self.elastic_user = os.getenv("ELASTIC_USER", "")
        self.elastic_pass = os.getenv("ELASTIC_PASS", "")
        self.elasticsearch_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
        self.elastic_api_key = os.getenv("ELASTIC_API_KEY", "")

        # --- Loki ---
        self.loki_url = os.getenv("LOKI_URL", "http://localhost:3100")
        self.loki_token = os.getenv("LOKI_TOKEN", "")

        # --- Knowledge Base ---
        self.stackoverflow_api_key = os.getenv("STACKOVERFLOW_API_KEY", "")
        self.reddit_client_id = os.getenv("REDDIT_CLIENT_ID", "")
        self.reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
        self.forum_base_url = os.getenv("FORUM_BASE_URL", "")
        self.forum_api_key = os.getenv("FORUM_API_KEY", "")

        # --- Requirements ---
        self.requirements_path = os.getenv("REQUIREMENTS_PATH", "requirements")

        # --- Performance ---
        self.max_workers = int(os.getenv("MAX_WORKERS", "4"))
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "60"))

        # --- Observability ---
        self.enable_metrics = os.getenv("ENABLE_METRICS", "true").lower() == "true"
        self.enable_tracing = os.getenv("ENABLE_TRACING", "false").lower() == "true"

        # --- Entity-aware reasoning ---
        self.entity_aware_max_hops = int(os.getenv("ENTITY_AWARE_MAX_HOPS", "3"))
        self.iterative_max_iterations = int(os.getenv("ITERATIVE_MAX_ITERATIONS", "3"))
        self.iterative_confidence_threshold = float(
            os.getenv("ITERATIVE_CONFIDENCE_THRESHOLD", "0.7")
        )

        # --- GraphRAG ---
        self.graphrag_enabled = os.getenv("GRAPH_RAG_ENABLED", "false").lower() == "true"
        self.graphrag_use_llm_extraction = os.getenv("GRAPH_RAG_USE_LLM", "false").lower() == "true"
        self.graphrag_structural_chunking = os.getenv("GRAPH_RAG_STRUCTURAL_CHUNKING", "true").lower() == "true"
        self.graphrag_incremental = os.getenv("GRAPH_RAG_INCREMENTAL", "true").lower() == "true"
        self.graphrag_community_detection = os.getenv("GRAPH_RAG_COMMUNITY_DETECTION", "true").lower() == "true"
        self.graphrag_max_entities = int(os.getenv("GRAPH_RAG_MAX_ENTITIES", "100"))
        self.graphrag_default_hops = int(os.getenv("GRAPH_RAG_DEFAULT_HOPS", "3"))
        self.graphrag_entity_types = os.getenv(
            "GRAPH_RAG_ENTITY_TYPES",
            "PERSON,ORGANIZATION,CONCEPT,EVENT,LOCATION,PRODUCT,TECHNOLOGY,DOCUMENT,PROCESS"
        ).split(",")
        self.graphrag_relationship_types = os.getenv(
            "GRAPH_RAG_RELATIONSHIP_TYPES",
            "RELATED_TO,PART_OF,WORKS_FOR,LOCATED_AT,USES,DEPENDS_ON,CREATED_BY,DEFINED_IN,REFERENCES,CONTAINS,IMPLEMENTS,MANAGES"
        ).split(",")

        # --- Chunking ---
        self.chunking_chunker_type = os.getenv("CHUNKING_CHUNKER_TYPE", "semantic")
        self.chunking_semantic_threshold = float(os.getenv("CHUNKING_SEMANTIC_CHUNK_THRESHOLD", "0.5"))
        self.chunking_semantic_embed_model = os.getenv(
            "CHUNKING_SEMANTIC_EMBED_MODEL", "BAAI/bge-small-en-v1.5"
        )
        self.chunking_sentence_size = int(os.getenv("CHUNKING_SENTENCE_CHUNK_SIZE", "1024"))
        self.chunking_sentence_overlap = int(os.getenv("CHUNKING_SENTENCE_CHUNK_OVERLAP", "20"))
        self.chunking_code_max_lines = int(os.getenv("CHUNKING_CODE_CHUNK_MAX_LINES", "100"))
        self.chunking_min_length = int(os.getenv("CHUNKING_CHUNK_MIN_LENGTH", "50"))
        self.chunking_max_length = int(os.getenv("CHUNKING_CHUNK_MAX_LENGTH", "2048"))

        # --- ColBERT ---
        self.colbert_enabled = os.getenv("COLBERT_ENABLED", "false").lower() == "true"
        self.colbert_model_name = os.getenv("COLBERT_MODEL_NAME", "colbert-ir/colbertv2.0")
        self.colbert_max_length = int(os.getenv("COLBERT_MAX_LENGTH", "512"))
        self.colbert_top_k = int(os.getenv("COLBERT_SIMILARITY_TOP_K", "10"))
        self.colbert_rerank = os.getenv("COLBERT_RERANK_AFTER", "true").lower() == "true"

        # --- Retrieval Strategy ---
        self.retrieval_default_strategy = os.getenv("RETRIEVAL_DEFAULT_STRATEGY", "hybrid")
        self.retrieval_fusion_method = os.getenv("RETRIEVAL_FUSION_METHOD", "rrf")
        self.retrieval_parallel = os.getenv("RETRIEVAL_PARALLEL_RETRIEVAL", "true").lower() == "true"
        self.retrieval_timeout = int(os.getenv("RETRIEVAL_TIMEOUT_SECONDS", "30"))
        self.retrieval_fallback = os.getenv("RETRIEVAL_FALLBACK_ON_EMPTY", "true").lower() == "true"

        # --- Diagram Indexing ---
        self.diagram_index_enabled = os.getenv("DIAGRAM_INDEX_ENABLED", "false").lower() == "true"
        self.diagram_collection = os.getenv("DIAGRAM_COLLECTION", "diagrams")
        self.diagram_vector_size = int(os.getenv("DIAGRAM_VECTOR_SIZE", "384"))

        # --- UI Sketch ---
        self.ui_sketch_enabled = os.getenv("UI_SKETCH_ENABLED", "false").lower() == "true"

        # --- ColPali ---
        self.colpali_enabled = os.getenv("COLPALI_ENABLED", "false").lower() == "true"

    def validate(self) -> None:
        """Validate critical security settings at startup."""
        if self.jwt_secret == "change-me-in-production":
            import warnings

            warnings.warn(
                "SECURITY WARNING: JWT_SECRET is using the default placeholder value. "
                "Set JWT_SECRET to a strong random value before deploying to production.",
                RuntimeWarning,
                stacklevel=2,
            )
        if not self.credential_encrypt_key:
            import warnings

            warnings.warn(
                "SECURITY WARNING: CREDENTIAL_ENCRYPT_KEY is not set. "
                "Git credential encryption will be disabled.",
                RuntimeWarning,
                stacklevel=2,
            )


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
