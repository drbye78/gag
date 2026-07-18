"""
Retrieval Module - Multi-source retrieval components.

All imports are lazy to prevent cascading dependency loading.
Importing retrieval.orchestrator no longer pulls in documents.parse → llama_index.
"""

__all__ = [
    "DocsRetriever", "CodeRetriever", "GraphRetriever", "CodeGraphRetriever",
    "TicketRetriever", "TelemetryRetriever", "KnowledgeRetriever",
    "RetrievalOrchestrator", "RetrievalRouter", "RetrievalSource",
    "RerankProvider", "RerankResult", "RerankPipeline", "RerankConfig", "RerankStrategy",
    "get_rerank_pipeline",
    "CitationStyle", "CitationSource", "Citation", "AnnotatedAnswer",
    "CitationBuilder", "CitationFormatter",
    "ReasoningMode", "get_reasoning_engine",
    "get_entity_aware_reasoning_engine",
    "IterativeRetrievalReasoner", "IterationStrategy", "get_iterative_reasoning_engine",
    "EntityCentricRetriever", "get_entity_centric_retriever",
    "LateInteractionRetriever", "LateInteractionResult", "get_late_interaction_retriever",
    "DiagramRetriever", "DiagramSearchResult", "DiagramRetrievalResult",
    "get_diagram_retriever",
    "ColBERTIndexer", "ColBERTIndexResult", "ColBERTRetriever",
    "get_colbert_indexer", "get_colbert_retriever",
    "get_colbert_search_client",
]

# Module-level flag to track if heavy imports have been loaded
_imports_loaded = False
_loaded = {}

def __getattr__(name):
    """Lazy-load retrieval components on first access."""
    global _imports_loaded

    # Simple mappings
    _simple = {
        "DocsRetriever": ("retrieval.docs", "DocsRetriever"),
        "get_docs_retriever": ("retrieval.docs", "get_docs_retriever"),
        "CodeRetriever": ("retrieval.code", "CodeRetriever"),
        "get_code_retriever": ("retrieval.code", "get_code_retriever"),
        "GraphRetriever": ("retrieval.graph", "GraphRetriever"),
        "get_graph_retriever": ("retrieval.graph", "get_graph_retriever"),
        "CodeGraphRetriever": ("retrieval.code_graph", "CodeGraphRetriever"),
        "get_code_graph_retriever": ("retrieval.code_graph", "get_code_graph_retriever"),
        "TicketRetriever": ("retrieval.ticket", "TicketRetriever"),
        "get_ticket_retriever": ("retrieval.ticket", "get_ticket_retriever"),
        "TelemetryRetriever": ("retrieval.telemetry", "TelemetryRetriever"),
        "get_telemetry_retriever": ("retrieval.telemetry", "get_telemetry_retriever"),
        "RetrievalOrchestrator": ("retrieval.orchestrator", "RetrievalOrchestrator"),
        "RetrievalRouter": ("retrieval.orchestrator", "RetrievalRouter"),
        "RetrievalSource": ("retrieval.orchestrator", "RetrievalSource"),
        "ReasoningMode": ("retrieval.reasoning", "ReasoningMode"),
        "get_reasoning_engine": ("retrieval.reasoning", "get_reasoning_engine"),
        "EntityCentricRetriever": ("retrieval.entity_centric", "EntityCentricRetriever"),
        "get_entity_centric_retriever": ("retrieval.entity_centric", "get_entity_centric_retriever"),
    }

    if name in _simple:
        mod_path, attr_name = _simple[name]
        import importlib
        mod = importlib.import_module(mod_path)
        return getattr(mod, attr_name)

    # Optional imports (may fail due to missing deps)
    _optional = {
        "ColBERTIndexer": ("retrieval.colbert", "ColBERTIndexer"),
        "ColBERTIndexResult": ("retrieval.colbert", "ColBERTIndexResult"),
        "ColBERTRetriever": ("retrieval.colbert", "ColBERTRetriever"),
        "get_colbert_indexer": ("retrieval.colbert", "get_colbert_indexer"),
        "get_colbert_retriever": ("retrieval.colbert", "get_colbert_retriever"),
        "get_colbert_search_client": ("retrieval.colbert", "get_colbert_search_client"),
        "DiagramRetriever": ("retrieval.diagram", "DiagramRetriever"),
        "DiagramSearchResult": ("retrieval.diagram", "DiagramSearchResult"),
        "DiagramRetrievalResult": ("retrieval.diagram", "DiagramRetrievalResult"),
        "get_diagram_retriever": ("retrieval.diagram", "get_diagram_retriever"),
        "KnowledgeRetriever": ("retrieval.knowledge", "KnowledgeRetriever"),
        "get_knowledge_retriever": ("retrieval.knowledge", "get_knowledge_retriever"),
        "LateInteractionRetriever": ("retrieval.late_interaction", "LateInteractionRetriever"),
        "LateInteractionResult": ("retrieval.late_interaction", "LateInteractionResult"),
        "get_late_interaction_retriever": ("retrieval.late_interaction", "get_late_interaction_retriever"),
    }

    if name in _optional:
        mod_path, attr_name = _optional[name]
        try:
            import importlib
            mod = importlib.import_module(mod_path)
            return getattr(mod, attr_name)
        except (ImportError, OSError):
            return None

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
