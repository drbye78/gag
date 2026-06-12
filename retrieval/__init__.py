"""
Retrieval Module - Multi-source retrieval components.

Exports: DocsRetriever, CodeRetriever, GraphRetriever,
TicketRetriever, TelemetryRetriever, RetrievalOrchestrator.
"""

from retrieval.citations import (
    AnnotatedAnswer,
    Citation,
    CitationBuilder,
    CitationFormatter,
    CitationSource,
    CitationStyle,
)
from retrieval.code import CodeRetriever, get_code_retriever
from retrieval.code_graph import CodeGraphRetriever, get_code_graph_retriever
from retrieval.docs import DocsRetriever, get_docs_retriever
from retrieval.entity_centric import (
    EntityCentricRetriever,
    get_entity_centric_retriever,
)
from retrieval.graph import GraphRetriever, get_graph_retriever
from retrieval.orchestrator import (
    RetrievalOrchestrator,
    RetrievalRouter,
    RetrievalSource,
)
from retrieval.reasoning import ReasoningMode, get_reasoning_engine
from retrieval.reasoning.entity_aware import get_entity_aware_reasoning_engine
from retrieval.reasoning.iterative import (
    IterationStrategy,
    IterativeRetrievalReasoner,
    get_iterative_reasoning_engine,
)
from retrieval.rerank import (
    RerankConfig,
    RerankPipeline,
    RerankProvider,
    RerankResult,
    RerankStrategy,
    get_rerank_pipeline,
)
from retrieval.telemetry import TelemetryRetriever, get_telemetry_retriever
from retrieval.ticket import TicketRetriever, get_ticket_retriever

# Late interaction requires ColPali/torch — lazy import
try:
    from retrieval.late_interaction import (
        LateInteractionResult,
        LateInteractionRetriever,
        get_late_interaction_retriever,
    )
except ImportError:
    pass
# Diagram retrieval requires Pillow — lazy import
try:
    from retrieval.diagram import (
        DiagramGraphIndexer,
        DiagramQdrantIndexer,
        DiagramRetrievalResult,
        DiagramRetriever,
        DiagramSearchResult,
        get_diagram_graph_indexer,
        get_diagram_qdrant_indexer,
        get_diagram_retriever,
    )
except ImportError:
    pass

try:
    from retrieval.colbert import (
        ColBERTIndexer,
        ColBERTIndexResult,
        ColBERTQdrantIndexer,
        ColBERTQdrantRetriever,
        ColBERTRetriever,
        ColBERTSearchClient,
        get_colbert_indexer,
        get_colbert_qdrant_indexer,
        get_colbert_qdrant_retriever,
        get_colbert_retriever,
        get_colbert_search_client,
    )
except ImportError:
    pass

try:
    from retrieval.knowledge import (
        KnowledgeRetriever,
        get_knowledge_retriever,
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
    "KnowledgeRetriever",
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
