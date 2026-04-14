"""Tests for ColPali visual integration with UI sketches."""

import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import torch


def _mock_colpali_module(**kwargs):
    """Install a fake documents.colpali module in sys.modules to avoid real imports."""
    mock_get_client = MagicMock()
    if "client" in kwargs:
        mock_get_client.return_value = kwargs["client"]

    mock_module = SimpleNamespace(
        get_colpali_client=mock_get_client,
    )
    sys.modules["documents.colpali"] = mock_module
    return mock_get_client


def _unmock_colpali_module():
    """Remove the fake documents.colpali module from sys.modules."""
    sys.modules.pop("documents.colpali", None)


def _reset_indexer():
    """Reset the module-level singleton so each test gets a fresh instance."""
    # Reload the module to clear the singleton
    import importlib
    import ui.colpali_integration
    ui.colpali_integration._indexer = None
    importlib.reload(ui.colpali_integration)


class TestUISketchVisualIndexer:
    """Tests for UISketchVisualIndexer ColPali wrapper."""

    def test_get_embedding_returns_embedding(self):
        """Mocks ColPali client, returns embedding with vectors."""
        _reset_indexer()

        fake_embedding = SimpleNamespace(
            embeddings=torch.tensor([[0.1, 0.2], [0.3, 0.4]]),
            num_tokens=2,
            model_name="vidore/colqwen2-v1.0",
        )
        mock_client = MagicMock()
        mock_client.available = True
        mock_client.get_document_embeddings.return_value = fake_embedding

        _mock_colpali_module(client=mock_client)
        try:
            from ui.colpali_integration import get_ui_visual_indexer
            indexer = get_ui_visual_indexer()
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(indexer.get_embedding("https://example.com/sketch.png"))
            loop.close()

            assert result is not None
            assert result.embeddings is not None
            assert result.num_tokens == 2
        finally:
            _unmock_colpali_module()

    def test_get_embedding_returns_none_when_unavailable(self):
        """Mocks client.available = False."""
        _reset_indexer()

        mock_client = MagicMock()
        mock_client.available = False

        _mock_colpali_module(client=mock_client)
        try:
            from ui.colpali_integration import get_ui_visual_indexer
            indexer = get_ui_visual_indexer()
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(indexer.get_embedding("https://example.com/sketch.png"))
            loop.close()

            assert result is None
        finally:
            _unmock_colpali_module()

    def test_get_embedding_returns_none_on_exception(self):
        """Mocks client to raise Exception."""
        _reset_indexer()

        mock_client = MagicMock()
        mock_client.available = True
        mock_client.get_document_embeddings.side_effect = RuntimeError("model load failed")

        _mock_colpali_module(client=mock_client)
        try:
            from ui.colpali_integration import get_ui_visual_indexer
            indexer = get_ui_visual_indexer()
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(indexer.get_embedding("https://example.com/sketch.png"))
            loop.close()

            assert result is None
        finally:
            _unmock_colpali_module()

    def test_compute_similarity_returns_score(self):
        """Mocks score_retrieval, returns 0.95."""
        _reset_indexer()

        mock_client = MagicMock()
        mock_client.available = True
        mock_client.score_retrieval.return_value = torch.tensor(0.95)

        embedding_a = [[0.1, 0.2], [0.3, 0.4]]
        embedding_b = [[0.11, 0.19], [0.31, 0.39]]

        _mock_colpali_module(client=mock_client)
        try:
            from ui.colpali_integration import get_ui_visual_indexer
            indexer = get_ui_visual_indexer()
            loop = asyncio.new_event_loop()
            score = loop.run_until_complete(
                indexer.compute_similarity(embedding_a, embedding_b)
            )
            loop.close()

            assert score == pytest.approx(0.95, abs=1e-5)
        finally:
            _unmock_colpali_module()

    def test_compute_similarity_returns_zero_on_failure(self):
        """Mocks to raise Exception, returns 0.0."""
        _reset_indexer()

        mock_client = MagicMock()
        mock_client.available = True
        mock_client.score_retrieval.side_effect = ValueError("tensor mismatch")

        embedding_a = [[0.1, 0.2]]
        embedding_b = [[0.3, 0.4]]

        _mock_colpali_module(client=mock_client)
        try:
            from ui.colpali_integration import get_ui_visual_indexer
            indexer = get_ui_visual_indexer()
            loop = asyncio.new_event_loop()
            score = loop.run_until_complete(
                indexer.compute_similarity(embedding_a, embedding_b)
            )
            loop.close()

            assert score == 0.0
        finally:
            _unmock_colpali_module()

    def test_get_ui_visual_indexer_singleton(self):
        """Same instance returned twice."""
        _reset_indexer()

        from ui.colpali_integration import get_ui_visual_indexer

        indexer_a = get_ui_visual_indexer()
        indexer_b = get_ui_visual_indexer()

        assert indexer_a is indexer_b
