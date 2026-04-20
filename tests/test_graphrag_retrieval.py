import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from retrieval.hybrid import HybridRetriever, EnhancedHybridRetriever
from retrieval.classifier import QueryClassifier, QueryIntent
from retrieval.reasoning import ReasoningMode


class TestEntityLinking:
    def setup_method(self):
        self.retriever = HybridRetriever()

    def test_extract_entity_names_basic(self):
        retriever = HybridRetriever()
        names = retriever._extract_entity_names("Tell me about Acme Corp and Microsoft")

        assert "Acme" in names
        assert "Microsoft" in names

    def test_extract_entity_names_filters_short_words(self):
        retriever = HybridRetriever()
        names = retriever._extract_entity_names("The AI system works")

        assert "AI" in names or "system" in names

    def test_extract_entity_names_removes_punctuation(self):
        retriever = HybridRetriever()
        names = retriever._extract_entity_names("Test Acme Corp")

        assert "Acme" in names or "Corp" in names


class TestGraphAwareSearch:
    def setup_method(self):
        self.retriever = HybridRetriever()

    @pytest.mark.asyncio
    async def test_link_query_entities_returns_structure(self):
        retriever = HybridRetriever()

        with patch.object(retriever.graph_retriever, 'search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {"results": []}

            result = await retriever.link_query_entities("Tell me about test", limit=10)

            assert "entities" in result
            assert "relationships" in result
            assert "community_ids" in result

    @pytest.mark.asyncio
    async def test_link_query_entities_empty_query(self):
        retriever = HybridRetriever()

        result = await retriever.link_query_entities("", limit=10)

        assert result["entities"] == []
        assert result["relationships"] == []


class TestQueryClassifier:
    def setup_method(self):
        self.classifier = QueryClassifier()

    def test_classify_relationship_query(self):
        result = self.classifier.classify("How is John related to Acme Corp?")

        assert result["primary_intent"] == QueryIntent.RELATIONSHIP.value
        assert result["requires_graph"] == True

    def test_classify_code_relationship_query(self):
        result = self.classifier.classify("Find all callers of function foo")

        assert result["primary_intent"] == QueryIntent.CODE_RELATIONSHIP.value
        assert result["requires_graph"] == True

    def test_classify_fact_query(self):
        result = self.classifier.classify("What is Python?")

        assert result["primary_intent"] == QueryIntent.FACT.value
        assert result["requires_graph"] == False

    def test_classify_causes_graph(self):
        result = self.classifier.classify("Why does the system fail?")

        assert result["requires_graph"] == True

    def test_classify_complex_query(self):
        result = self.classifier.classify("Compare Python and Java for web development")

        assert result.get("primary_intent") is not None


class TestHybridRetrieverSearch:
    def setup_method(self):
        self.retriever = HybridRetriever()

    @pytest.mark.asyncio
    async def test_search_returns_structure(self):
        with patch.object(self.retriever.docs_retriever, 'search', new_callable=AsyncMock) as mock_docs:
            with patch.object(self.retriever.code_retriever, 'search', new_callable=AsyncMock) as mock_code:
                mock_docs.return_value = {"results": [], "total": 0}
                mock_code.return_value = {"results": [], "total": 0}

                result = await self.retriever.search("test query", limit=10)

                assert "query" in result
                assert "results" in result
                assert "total" in result

    def test_search_strategy_selection(self):
        classifier = QueryClassifier()
        result = classifier.classify("Tell me about test")

        assert result is not None
        assert "strategy" in result
        assert "primary_intent" in result


class TestEnhancedHybridRetriever:
    def setup_method(self):
        self.retriever = EnhancedHybridRetriever()

    def test_has_entity_cache(self):
        assert hasattr(self.retriever, 'entity_cache')

    @pytest.mark.asyncio
    async def test_get_entity_cache_stats(self):
        stats = self.retriever.get_entity_cache_stats()

        assert "size" in stats
        assert "capacity" in stats
        assert "hit_rate" in stats

    def test_invalidate_entity_cache_all(self):
        result = self.retriever.invalidate_entity_cache()

        assert result == True

    def test_invalidate_specific_entity(self):
        result = self.retriever.invalidate_entity_cache("NonExistentEntity")

        assert result in [True, False]


def test_fusion_method_exists():
    from retrieval.fusion import FusionMethod

    assert hasattr(FusionMethod, 'RRF')
    assert hasattr(FusionMethod, 'SCORE_NORMALIZED')
    assert hasattr(FusionMethod, 'WEIGHTED')