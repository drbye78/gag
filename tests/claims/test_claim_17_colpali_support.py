"""
README claim: "ColPali Support: Visual embeddings for UI sketch similarity"
Source: README.md line 110
"""
import pytest
import inspect


@pytest.mark.claim
def test_colpali_module_exists():
    from documents import colpali
    assert colpali is not None


@pytest.mark.claim
def test_colpali_torch_import_is_conditional():
    from documents import colpali
    source = inspect.getsource(colpali)
    assert "import torch" in source, "ColPali module doesn't import torch"
    assert "except" in source, "torch import is not conditional -- will crash if torch not installed"


@pytest.mark.claim
def test_colpali_search_method_exists():
    # UISketchVisualIndexer is in ui/colpali_integration, not documents/colpali
    from ui.colpali_integration import UISketchVisualIndexer
    assert hasattr(UISketchVisualIndexer, "search"), "ColPali indexer must have search method"
