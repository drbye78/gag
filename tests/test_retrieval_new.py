"""
Tests for the new retrieval modules: rerank, citations, entity_aware, iterative.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestRerankProvider:
    """Tests for RerankProvider enum values."""

    def test_rerank_provider_values(self):
        from retrieval.rerank.base import RerankProvider

        assert RerankProvider.COHERE.value == "cohere"
        assert RerankProvider.BGE.value == "bge-reranker"
        assert RerankProvider.LLAMA_INDEX.value == "llama_index"
        assert RerankProvider.SENTENCE_TRANSFORMER.value == "sentence_transformer"
        assert RerankProvider.CROSS_ENCODER.value == "cross_encoder"
        assert RerankProvider.JINA.value == "jina"

    def test_rerank_provider_is_string_enum(self):
        from retrieval.rerank.base import RerankProvider

        provider = RerankProvider.COHERE
        assert isinstance(provider, str)
        assert provider.value == "cohere"


class TestRerankConfig:
    """Tests for RerankConfig default values."""

    def test_default_values(self):
        from retrieval.rerank.pipeline import RerankConfig, RerankStrategy

        config = RerankConfig()
        assert config.strategy == RerankStrategy.CASCADE
        assert config.top_k == 10
        assert config.min_score == 0.0

    def test_default_providers(self):
        from retrieval.rerank.pipeline import RerankConfig
        from retrieval.rerank.base import RerankProvider

        config = RerankConfig()
        assert config.providers is not None
        assert RerankProvider.COHERE in config.providers
        assert RerankProvider.BGE in config.providers
        assert RerankProvider.LLAMA_INDEX in config.providers

    def test_custom_providers(self):
        from retrieval.rerank.pipeline import RerankConfig, RerankStrategy
        from retrieval.rerank.base import RerankProvider

        config = RerankConfig(
            strategy=RerankStrategy.SINGLE,
            top_k=5,
            min_score=0.3,
            providers=[RerankProvider.JINA],
        )
        assert config.strategy == RerankStrategy.SINGLE
        assert config.top_k == 5
        assert config.min_score == 0.3
        assert config.providers == [RerankProvider.JINA]


class TestRerankStrategy:
    """Tests for RerankStrategy enum values."""

    def test_rerank_strategy_values(self):
        from retrieval.rerank.pipeline import RerankStrategy

        assert RerankStrategy.SINGLE.value == "single"
        assert RerankStrategy.CASCADE.value == "cascade"
        assert RerankStrategy.ENSEMBLE.value == "ensemble"


class TestRerankResult:
    """Tests for RerankResult dataclass."""

    def test_rerank_result_creation(self):
        from retrieval.rerank.base import RerankResult

        result = RerankResult(
            node_id="test-1",
            content="Test content",
            score=0.95,
            original_rank=5,
            new_rank=1,
            source="test",
            metadata={"key": "value"},
        )
        assert result.node_id == "test-1"
        assert result.content == "Test content"
        assert result.score == 0.95
        assert result.original_rank == 5
        assert result.new_rank == 1
        assert result.source == "test"
        assert result.metadata == {"key": "value"}


class TestRerankPipeline:
    """Tests for RerankPipeline.rerank() with mock results."""

    @pytest.mark.asyncio
    async def test_rerank_empty_results(self):
        from retrieval.rerank.pipeline import RerankPipeline

        pipeline = RerankPipeline()
        results = await pipeline.rerank("query", [])
        assert results == []

    @pytest.mark.asyncio
    async def test_rerank_with_fallback(self):
        from retrieval.rerank.pipeline import RerankPipeline
        from retrieval.rerank.base import RerankResult

        pipeline = RerankPipeline()
        mock_results = [
            {"id": "1", "content": "Content 1", "score": 0.9},
            {"id": "2", "content": "Content 2", "score": 0.8},
        ]

        with patch(
            "retrieval.rerank.pipeline.get_available_rerankers", return_value={}
        ):
            results = await pipeline.rerank("test query", mock_results)
            assert len(results) == 2
            assert isinstance(results[0], RerankResult)

    @pytest.mark.asyncio
    async def test_single_strategy(self):
        from retrieval.rerank.pipeline import (
            RerankPipeline,
            RerankConfig,
            RerankStrategy,
        )
        from retrieval.rerank.base import RerankProvider

        config = RerankConfig(
            strategy=RerankStrategy.SINGLE, providers=[RerankProvider.COHERE]
        )
        pipeline = RerankPipeline(config)

        mock_results = [
            {"id": "1", "content": "Content 1", "score": 0.9},
        ]

        with patch(
            "retrieval.rerank.pipeline.get_available_rerankers", return_value={}
        ):
            results = await pipeline.rerank("query", mock_results)
            assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_cascade_strategy(self):
        from retrieval.rerank.pipeline import (
            RerankPipeline,
            RerankConfig,
            RerankStrategy,
        )
        from retrieval.rerank.base import RerankProvider

        config = RerankConfig(
            strategy=RerankStrategy.CASCADE, providers=[RerankProvider.COHERE]
        )
        pipeline = RerankPipeline(config)

        mock_results = [
            {"id": "1", "content": "Content 1", "score": 0.9},
            {"id": "2", "content": "Content 2", "score": 0.8},
        ]

        with patch(
            "retrieval.rerank.pipeline.get_available_rerankers", return_value={}
        ):
            results = await pipeline.rerank("query", mock_results)
            assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_ensemble_strategy(self):
        from retrieval.rerank.pipeline import (
            RerankPipeline,
            RerankConfig,
            RerankStrategy,
        )
        from retrieval.rerank.base import RerankProvider

        config = RerankConfig(
            strategy=RerankStrategy.ENSEMBLE, providers=[RerankProvider.COHERE]
        )
        pipeline = RerankPipeline(config)

        mock_results = [
            {"id": "1", "content": "Content 1", "score": 0.9},
        ]

        with patch(
            "retrieval.rerank.pipeline.get_available_rerankers", return_value={}
        ):
            results = await pipeline.rerank("query", mock_results)
            assert len(results) >= 1


class TestBaseReranker:
    """Tests for BaseReranker abstract class."""

    def test_base_reranker_is_abc(self):
        from retrieval.rerank.base import BaseReranker
        from abc import ABC

        assert issubclass(BaseReranker, ABC)

    def test_rerank_result_dataclass(self):
        from retrieval.rerank.base import RerankResult
        from dataclasses import is_dataclass

        assert is_dataclass(RerankResult)


class TestCitationStyle:
    """Tests for CitationStyle enum values."""

    def test_citation_style_values(self):
        from retrieval.citations.base import CitationStyle

        assert CitationStyle.VERBATIM.value == "verbatim"
        assert CitationStyle.PARENTHETICAL.value == "parenthetical"
        assert CitationStyle.FOOTNOTE.value == "footnote"
        assert CitationStyle.HIGHLIGHT.value == "highlight"
        assert CitationStyle.STRUCTURED.value == "structured"


class TestCitationSource:
    """Tests for CitationSource dataclass."""

    def test_citation_source_creation(self):
        from retrieval.citations.base import CitationSource

        source = CitationSource(
            source_id="src-1",
            content="Test source content",
            source_type="document",
            source_name="Test Doc",
            url="https://example.com",
            line_start=10,
            line_end=20,
            page=1,
            chunk_index=0,
            score=0.95,
            metadata={"key": "value"},
        )
        assert source.source_id == "src-1"
        assert source.content == "Test source content"
        assert source.source_type == "document"
        assert source.source_name == "Test Doc"
        assert source.url == "https://example.com"
        assert source.line_start == 10
        assert source.line_end == 20
        assert source.page == 1
        assert source.chunk_index == 0
        assert source.score == 0.95
        assert source.metadata == {"key": "value"}

    def test_citation_source_default_values(self):
        from retrieval.citations.base import CitationSource

        source = CitationSource(
            source_id="src-1",
            content="Content",
            source_type="doc",
            source_name="Doc",
        )
        assert source.url is None
        assert source.line_start is None
        assert source.line_end is None
        assert source.page is None
        assert source.chunk_index is None
        assert source.score == 0.0
        assert source.metadata == {}
        assert source.accessed_at is not None


class TestCitation:
    """Tests for Citation dataclass."""

    def test_citation_creation(self):
        from retrieval.citations.base import Citation, CitationSource

        source = CitationSource(
            source_id="src-1",
            content="Content",
            source_type="doc",
            source_name="Doc",
        )
        citation = Citation(
            id="cit-1",
            source=source,
            spans=[{"start": 0, "end": 10}],
            confidence=0.9,
        )
        assert citation.id == "cit-1"
        assert citation.source == source
        assert citation.spans == [{"start": 0, "end": 10}]
        assert citation.confidence == 0.9


class TestAnnotatedAnswer:
    """Tests for AnnotatedAnswer dataclass."""

    def test_annotated_answer_creation(self):
        from retrieval.citations.base import (
            AnnotatedAnswer,
            Citation,
            CitationSource,
            CitationStyle,
        )

        source = CitationSource(
            source_id="src-1",
            content="Content",
            source_type="doc",
            source_name="Doc",
        )
        citation = Citation(id="cit-1", source=source, spans=[], confidence=0.9)

        answer = AnnotatedAnswer(
            answer="Test answer",
            citations=[citation],
            sources=[source],
            style=CitationStyle.PARENTHETICAL,
            metadata={"key": "value"},
        )
        assert answer.answer == "Test answer"
        assert len(answer.citations) == 1
        assert len(answer.sources) == 1
        assert answer.style == CitationStyle.PARENTHETICAL
        assert answer.metadata == {"key": "value"}


class TestCitationBuilder:
    """Tests for CitationBuilder.build() with mock answer."""

    def test_build_with_empty_results(self):
        from retrieval.citations.builder import CitationBuilder
        from retrieval.citations.base import CitationStyle

        builder = CitationBuilder(style=CitationStyle.PARENTHETICAL)
        result = builder.build("Test answer", [])
        assert result.answer == "Test answer"
        assert result.citations == []
        assert result.sources == []

    def test_build_with_results(self):
        from retrieval.citations.builder import CitationBuilder
        from retrieval.citations.base import CitationStyle

        builder = CitationBuilder(style=CitationStyle.PARENTHETICAL)
        mock_results = [
            {
                "content": "Source content 1",
                "source": "doc",
                "source_name": "Doc 1",
                "score": 0.9,
            },
            {
                "content": "Source content 2",
                "source": "wiki",
                "source_name": "Wiki 1",
                "score": 0.8,
            },
        ]
        result = builder.build("Test answer", mock_results)

        assert result.answer is not None
        assert len(result.sources) == 2
        assert result.sources[0].content == "Source content 1"
        assert result.sources[1].content == "Source content 2"

    def test_build_with_max_citations(self):
        from retrieval.citations.builder import CitationBuilder
        from retrieval.citations.base import CitationStyle

        builder = CitationBuilder(style=CitationStyle.PARENTHETICAL, max_citations=2)
        mock_results = [
            {
                "content": f"Content {i}",
                "source": "doc",
                "source_name": f"Doc {i}",
                "score": 0.9,
            }
            for i in range(5)
        ]
        result = builder.build("Answer", mock_results)
        assert len(result.sources) == 2

    def test_build_footnote_style(self):
        from retrieval.citations.builder import CitationBuilder
        from retrieval.citations.base import CitationStyle

        builder = CitationBuilder(style=CitationStyle.FOOTNOTE)
        result = builder.build(
            "Answer", [{"content": "Content", "source": "doc", "source_name": "Doc"}]
        )
        assert result.style == CitationStyle.FOOTNOTE


class TestCitationFormatter:
    """Tests for CitationFormatter.format_annotated() and format()."""

    def test_format_verbatim(self):
        from retrieval.citations.formatter import CitationFormatter
        from retrieval.citations.base import CitationSource, CitationStyle

        sources = [
            CitationSource(
                source_id="1",
                content="This is the source content",
                source_type="doc",
                source_name="Test Doc",
            )
        ]
        result = CitationFormatter.format(
            "Test answer", sources, CitationStyle.VERBATIM
        )
        assert "Test answer" in result
        assert "Sources:" in result

    def test_format_parenthetical(self):
        from retrieval.citations.formatter import CitationFormatter
        from retrieval.citations.base import CitationSource, CitationStyle

        sources = [
            CitationSource(
                source_id="1",
                content="Content",
                source_type="doc",
                source_name="Doc",
            )
        ]
        result = CitationFormatter.format(
            "Test answer", sources, CitationStyle.PARENTHETICAL
        )
        assert "Test answer" in result
        assert "[1]" in result

    def test_format_footnote(self):
        from retrieval.citations.formatter import CitationFormatter
        from retrieval.citations.base import CitationSource, CitationStyle

        sources = [
            CitationSource(
                source_id="1",
                content="Content",
                source_type="doc",
                source_name="Doc",
            )
        ]
        result = CitationFormatter.format(
            "Test answer", sources, CitationStyle.FOOTNOTE
        )
        assert "Test answer" in result

    def test_format_highlight(self):
        from retrieval.citations.formatter import CitationFormatter
        from retrieval.citations.base import CitationSource, CitationStyle

        sources = [
            CitationSource(
                source_id="1",
                content="Content",
                source_type="doc",
                source_name="Doc",
            )
        ]
        result = CitationFormatter.format(
            "Test answer", sources, CitationStyle.HIGHLIGHT
        )
        assert "Test answer" in result
        assert "Sources:" in result


class TestGraphPathType:
    """Tests for GraphPathType enum."""

    def test_graph_path_type_values(self):
        from retrieval.reasoning.entity_aware import GraphPathType

        assert GraphPathType.DIRECT.value == "direct"
        assert GraphPathType.TRANSITIVE.value == "transitive"
        assert GraphPathType.CYCLIC.value == "cyclic"
        assert GraphPathType.BI_DIRECTIONAL.value == "bi_directional"


class TestEntityRelation:
    """Tests for EntityRelation dataclass."""

    def test_entity_relation_creation(self):
        from retrieval.reasoning.entity_aware import EntityRelation

        relation = EntityRelation(
            source="EntityA",
            target="EntityB",
            relation_type="depends_on",
            weight=0.8,
            properties={"key": "value"},
        )
        assert relation.source == "EntityA"
        assert relation.target == "EntityB"
        assert relation.relation_type == "depends_on"
        assert relation.weight == 0.8
        assert relation.properties == {"key": "value"}

    def test_entity_relation_default_weight(self):
        from retrieval.reasoning.entity_aware import EntityRelation

        relation = EntityRelation(source="A", target="B", relation_type="links")
        assert relation.weight == 1.0
        assert relation.properties == {}


class TestEntityContext:
    """Tests for EntityContext dataclass."""

    def test_entity_context_creation(self):
        from retrieval.reasoning.entity_aware import EntityContext, EntityRelation

        relations = [
            EntityRelation("A", "B", "depends_on"),
            EntityRelation("B", "C", "links"),
        ]
        context = EntityContext(
            entities={"A", "B", "C"},
            relations=relations,
            graph_paths={"A": ["B", "C"]},
        )
        assert context.entities == {"A", "B", "C"}
        assert len(context.relations) == 2
        assert context.graph_paths == {"A": ["B", "C"]}

    def test_entity_context_defaults(self):
        from retrieval.reasoning.entity_aware import EntityContext

        context = EntityContext()
        assert context.entities == set()
        assert context.relations == []
        assert context.graph_paths == {}


class TestReasoningStepEnhanced:
    """Tests for ReasoningStepEnhanced dataclass."""

    def test_reasoning_step_creation(self):
        from retrieval.reasoning.entity_aware import ReasoningStepEnhanced

        step = ReasoningStepEnhanced(
            step_id="1",
            thought="I need to find the answer",
            action="search",
            observation="Found results",
            score=0.9,
            entities_involved=["EntityA"],
            graph_paths_used=["path1"],
            children=[],
            parent_id=None,
        )
        assert step.step_id == "1"
        assert step.thought == "I need to find the answer"
        assert step.action == "search"
        assert step.observation == "Found results"
        assert step.score == 0.9
        assert step.entities_involved == ["EntityA"]
        assert step.graph_paths_used == ["path1"]


class TestEntityAwareReasoningEngine:
    """Tests for EntityAwareReasoningEngine.reason() with mock facts."""

    @pytest.mark.asyncio
    async def test_reason_basic(self):
        from retrieval.reasoning.entity_aware import EntityAwareReasoningEngine

        engine = EntityAwareReasoningEngine()
        mock_facts = [
            {"content": "Fact about EntityA", "score": 0.9, "source": "doc"},
            {"content": "Fact about EntityB", "score": 0.8, "source": "wiki"},
        ]
        result = await engine.reason("What about EntityA?", mock_facts)

        assert result is not None
        assert "answer" in result
        assert result["reasoning_mode"] == "entity_aware"
        assert "entities" in result

    @pytest.mark.asyncio
    async def test_reason_with_entity_graph(self):
        from retrieval.reasoning.entity_aware import (
            EntityAwareReasoningEngine,
            EntityRelation,
        )

        engine = EntityAwareReasoningEngine()
        mock_facts = [
            {"content": "EntityA is important", "score": 0.9, "source": "doc"}
        ]
        entity_graph = {
            "EntityA": [EntityRelation("EntityA", "EntityB", "depends_on", 0.7)],
        }
        result = await engine.reason("Tell me about EntityA", mock_facts, entity_graph)

        assert result is not None
        assert "graph_paths" in result

    @pytest.mark.asyncio
    async def test_reason_empty_facts(self):
        from retrieval.reasoning.entity_aware import EntityAwareReasoningEngine

        engine = EntityAwareReasoningEngine()
        result = await engine.reason("Query", [])

        assert result is not None
        assert "answer" in result

    @pytest.mark.asyncio
    async def test_reason_max_hops(self):
        from retrieval.reasoning.entity_aware import EntityAwareReasoningEngine

        engine = EntityAwareReasoningEngine(max_hops=1)
        mock_facts = [{"content": "Fact", "score": 0.9, "source": "doc"}]
        result = await engine.reason("Query", mock_facts)

        assert result is not None


class TestExtractEntitiesFromQuery:
    """Tests for _extract_entities_from_query()."""

    def test_extract_capitalized_entities(self):
        from retrieval.reasoning.entity_aware import EntityAwareReasoningEngine

        engine = EntityAwareReasoningEngine()
        query = "What is EntityA and EntityB relationship?"
        entities = engine._extract_entities_from_query(query)

        assert "EntityA" in entities
        assert "EntityB" in entities

    def test_extract_single_entity(self):
        from retrieval.reasoning.entity_aware import EntityAwareReasoningEngine

        engine = EntityAwareReasoningEngine()
        query = "Tell me about AuthService"
        entities = engine._extract_entities_from_query(query)

        assert "AuthService" in entities

    def test_extract_no_entities(self):
        from retrieval.reasoning.entity_aware import EntityAwareReasoningEngine

        engine = EntityAwareReasoningEngine()
        query = "what is this"
        entities = engine._extract_entities_from_query(query)

        assert len(entities) == 0

    def test_extract_mixed_case(self):
        from retrieval.reasoning.entity_aware import EntityAwareReasoningEngine

        engine = EntityAwareReasoningEngine()
        query = "API Gateway handles requests"
        entities = engine._extract_entities_from_query(query)

        assert "API" in entities
        assert "Gateway" in entities


class TestIterationStrategy:
    """Tests for IterationStrategy enum."""

    def test_iteration_strategy_values(self):
        from retrieval.reasoning.iterative import IterationStrategy

        assert IterationStrategy.EXPAND.value == "expand"
        assert IterationStrategy.FOCUS.value == "focus"
        assert IterationStrategy.REWRITE.value == "rewrite"
        assert IterationStrategy.DECOMPOSE.value == "decompose"


class TestIterationResult:
    """Tests for IterationResult dataclass."""

    def test_iteration_result_creation(self):
        from retrieval.reasoning.iterative import IterationResult

        result = IterationResult(
            iteration=1,
            query="initial query",
            retrieved=[{"content": "fact", "score": 0.9}],
            refined_query="refined query",
            done=True,
            confidence=0.85,
            duration_ms=100,
        )
        assert result.iteration == 1
        assert result.query == "initial query"
        assert len(result.retrieved) == 1
        assert result.refined_query == "refined query"
        assert result.done is True
        assert result.confidence == 0.85
        assert result.duration_ms == 100


class TestIterativeRetrievalReasoner:
    """Tests for IterativeRetrievalReasoner.retrieve() with mock retriever."""

    @pytest.mark.asyncio
    async def test_retrieve_basic(self):
        from retrieval.reasoning.iterative import IterativeRetrievalReasoner

        reasoner = IterativeRetrievalReasoner(max_iterations=2)

        def mock_retriever(query: str):
            return [{"content": f"Result for {query}", "score": 0.9}]

        result = await reasoner.retrieve("test query", mock_retriever)

        assert result is not None
        assert "answer" in result
        assert result["reasoning_mode"] == "iterative"
        assert "iterations" in result

    @pytest.mark.asyncio
    async def test_retrieve_with_multiple_iterations(self):
        from retrieval.reasoning.iterative import IterativeRetrievalReasoner

        reasoner = IterativeRetrievalReasoner(max_iterations=3, min_results=2)

        call_count = 0

        def mock_retriever(query: str):
            nonlocal call_count
            call_count += 1
            return [{"content": f"Result {call_count}", "score": 0.9}]

        result = await reasoner.retrieve("query", mock_retriever)

        assert len(result["iterations"]) >= 1

    @pytest.mark.asyncio
    async def test_retrieve_early_stop(self):
        from retrieval.reasoning.iterative import IterativeRetrievalReasoner

        reasoner = IterativeRetrievalReasoner(
            max_iterations=5,
            confidence_threshold=0.95,
            min_results=1,
        )

        def mock_retriever(query: str):
            return [{"content": "High confidence result", "score": 1.0}]

        result = await reasoner.retrieve("query", mock_retriever)

        assert result["confidence"] >= 0

    @pytest.mark.asyncio
    async def test_retrieve_empty_results(self):
        from retrieval.reasoning.iterative import IterativeRetrievalReasoner

        reasoner = IterativeRetrievalReasoner()

        def mock_retriever(query: str):
            return []

        result = await reasoner.retrieve("query", mock_retriever)

        assert result is not None
        assert result["total_retrieved"] == 0


class TestCalculateConfidence:
    """Tests for _calculate_confidence()."""

    def test_calculate_confidence_basic(self):
        from retrieval.reasoning.iterative import IterativeRetrievalReasoner

        reasoner = IterativeRetrievalReasoner()
        new_facts = [
            {"content": "Fact 1", "score": 0.9},
            {"content": "Fact 2", "score": 0.8},
        ]
        all_facts = new_facts + [{"content": "Fact 3", "score": 0.7}]

        confidence = reasoner._calculate_confidence(new_facts, all_facts, iteration=0)

        assert 0.0 <= confidence <= 1.0

    def test_calculate_confidence_empty_facts(self):
        from retrieval.reasoning.iterative import IterativeRetrievalReasoner

        reasoner = IterativeRetrievalReasoner()
        confidence = reasoner._calculate_confidence([], [], iteration=0)

        assert confidence == 0.0

    def test_calculate_confidence_high_iteration(self):
        from retrieval.reasoning.iterative import IterativeRetrievalReasoner

        reasoner = IterativeRetrievalReasoner()
        facts = [{"content": "Fact", "score": 0.9}]

        confidence = reasoner._calculate_confidence(facts, facts, iteration=5)

        assert confidence < 0.9  # Should have iteration penalty


class TestQueryRefinementStrategies:
    """Tests for different query refinement strategies."""

    @pytest.mark.asyncio
    async def test_expand_strategy(self):
        from retrieval.reasoning.iterative import (
            IterativeRetrievalReasoner,
            IterationStrategy,
        )

        reasoner = IterativeRetrievalReasoner(strategy=IterationStrategy.EXPAND)

        def mock_retriever(query: str):
            return [{"content": "Some additional context about topic", "score": 0.9}]

        result = await reasoner.retrieve("topic", mock_retriever)
        assert result is not None

    @pytest.mark.asyncio
    async def test_focus_strategy(self):
        from retrieval.reasoning.iterative import (
            IterativeRetrievalReasoner,
            IterationStrategy,
        )

        reasoner = IterativeRetrievalReasoner(strategy=IterationStrategy.FOCUS)

        def mock_retriever(query: str):
            return [{"content": "Focused content result", "score": 0.9}]

        result = await reasoner.retrieve("query", mock_retriever)
        assert result is not None

    @pytest.mark.asyncio
    async def test_decompose_strategy(self):
        from retrieval.reasoning.iterative import (
            IterativeRetrievalReasoner,
            IterationStrategy,
        )

        reasoner = IterativeRetrievalReasoner(strategy=IterationStrategy.DECOMPOSE)

        def mock_retriever(query: str):
            return [{"content": "Result", "score": 0.9}]

        result = await reasoner.retrieve(
            "very long query with many words to decompose", mock_retriever
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_focus_strategy(self):
        from retrieval.reasoning.iterative import (
            IterativeRetrievalReasoner,
            IterationStrategy,
        )

        reasoner = IterativeRetrievalReasoner(strategy=IterationStrategy.FOCUS)

        async def mock_retriever(query: str):
            return [{"content": "Focused content result", "score": 0.9}]

        result = await reasoner.retrieve("query", mock_retriever)
        assert result is not None

    @pytest.mark.asyncio
    async def test_decompose_strategy(self):
        from retrieval.reasoning.iterative import (
            IterativeRetrievalReasoner,
            IterationStrategy,
        )

        reasoner = IterativeRetrievalReasoner(strategy=IterationStrategy.DECOMPOSE)

        async def mock_retriever(query: str):
            return [{"content": "Result", "score": 0.9}]

        result = await reasoner.retrieve(
            "very long query with many words to decompose", mock_retriever
        )
        assert result is not None


class TestCalculateFinalConfidence:
    """Tests for _calculate_final_confidence()."""

    def test_calculate_final_confidence_with_results(self):
        from retrieval.reasoning.iterative import (
            IterativeRetrievalReasoner,
            IterationResult,
        )

        reasoner = IterativeRetrievalReasoner()
        facts = [{"score": 0.9}, {"score": 0.8}]
        results = [
            IterationResult(
                iteration=1,
                query="q",
                retrieved=facts,
                confidence=0.85,
                duration_ms=100,
            )
        ]

        confidence = reasoner._calculate_final_confidence(facts, results)
        assert 0.0 <= confidence <= 1.0

    def test_calculate_final_confidence_empty_facts(self):
        from retrieval.reasoning.iterative import IterativeRetrievalReasoner

        reasoner = IterativeRetrievalReasoner()
        confidence = reasoner._calculate_final_confidence([], [])
        assert confidence == 0.0
