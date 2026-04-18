"""
Retrieval Module - Multi-source retrieval components.

Exports: DocsRetriever, CodeRetriever, GraphRetriever,
TicketRetriever, TelemetryRetriever, RetrievalOrchestrator.
"""

from retrieval.docs import DocsRetriever, get_docs_retriever
from retrieval.code import CodeRetriever, get_code_retriever
from retrieval.graph import GraphRetriever, get_graph_retriever
from retrieval.code_graph import CodeGraphRetriever, get_code_graph_retriever
from retrieval.ticket import TicketRetriever, get_ticket_retriever
from retrieval.telemetry import TelemetryRetriever, get_telemetry_retriever
from retrieval.orchestrator import (
    RetrievalOrchestrator,
    RetrievalRouter,
    RetrievalSource,
)
from retrieval.rerank import (
    RerankProvider,
    RerankResult,
    RerankPipeline,
    RerankConfig,
    RerankStrategy,
    get_rerank_pipeline,
)
from retrieval.citations import (
    CitationStyle,
    CitationSource,
    Citation,
    AnnotatedAnswer,
    CitationBuilder,
    CitationFormatter,
)
from retrieval.reasoning import ReasoningMode, get_reasoning_engine
from retrieval.reasoning.entity_aware import get_entity_aware_reasoning_engine
from retrieval.reasoning.iterative import (
    IterativeRetrievalReasoner,
    IterationStrategy,
    get_iterative_reasoning_engine,
)
from retrieval.entity_centric import (
    EntityCentricRetriever,
    get_entity_centric_retriever,
)

# Late interaction requires ColPali/torch — lazy import
try:
    from retrieval.late_interaction import (
        LateInteractionRetriever,
        LateInteractionResult,
        get_late_interaction_retriever,
    )
except ImportError:
    pass
# Diagram retrieval requires Pillow — lazy import
try:
    from retrieval.diagram import (
        DiagramRetriever,
        DiagramSearchResult,
        DiagramRetrievalResult,
        DiagramQdrantIndexer,
        DiagramGraphIndexer,
        get_diagram_retriever,
        get_diagram_qdrant_indexer,
        get_diagram_graph_indexer,
    )
except ImportError:
    pass

try:
    from retrieval.colbert import (
        ColBERTIndexer,
        ColBERTIndexResult,
        ColBERTRetriever,
        ColBERTQdrantIndexer,
        ColBERTQdrantRetriever,
        ColBERTSearchClient,
        get_colbert_indexer,
        get_colbert_retriever,
        get_colbert_qdrant_indexer,
        get_colbert_qdrant_retriever,
        get_colbert_search_client,
    )
except ImportError:
    pass


__all__ = [
    "DocsRetriever",
    "CodeRetriever",
    "GraphRetriever",
    "CodeGraphRetriever",
    "TicketRetriever",
    "TelemetryRetriever",
    "RetrievalOrchestrator",
    "RetrievalRouter",
    "RetrievalSource",
    "RerankProvider",
    "RerankResult",
    "RerankPipeline",
    "RerankConfig",
    "RerankStrategy",
    "get_rerank_pipeline",
    "CitationStyle",
    "CitationSource",
    "Citation",
    "AnnotatedAnswer",
    "CitationBuilder",
    "CitationFormatter",
    "ReasoningEngine",
    "ReasoningMode",
    "get_reasoning_engine",
    "EntityAwareReasoningEngine",
    "GraphPathType",
    "get_entity_aware_reasoning_engine",
    "IterativeRetrievalReasoner",
    "IterationStrategy",
    "get_iterative_reasoning_engine",
    "EntityCentricRetriever",
    "get_entity_centric_retriever",
    "LateInteractionRetriever",
    "LateInteractionResult",
    "get_late_interaction_retriever",
    "DiagramRetriever",
    "DiagramSearchResult",
    "DiagramRetrievalResult",
    "get_diagram_retriever",
    "ColBERTIndexer",
    "ColBERTIndexResult",
    "ColBERTRetriever",
    "get_colbert_indexer",
    "get_colbert_retriever",
]
