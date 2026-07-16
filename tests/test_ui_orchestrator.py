"""Tests for UI_SKETCH retrieval in orchestrator."""

import pytest
from retrieval.orchestrator import RetrievalSource


class TestRetrievalSource:
    def test_ui_sketch_exists(self):
        """UI_SKETCH enum value exists."""
        assert hasattr(RetrievalSource, "UI_SKETCH")
        assert RetrievalSource.UI_SKETCH.value == "ui_sketch"

    def test_ui_sketch_in_default_sources(self):
        """UI_SKETCH is in RetrievalRouter default sources."""
        from retrieval.orchestrator import get_retrieval_router
        router = get_retrieval_router()
        assert RetrievalSource.UI_SKETCH in router.default_sources

    def test_diagram_in_default_sources(self):
        """DIAGRAM is in RetrievalRouter default sources."""
        from retrieval.orchestrator import get_retrieval_router
        router = get_retrieval_router()
        assert RetrievalSource.DIAGRAM in router.default_sources
