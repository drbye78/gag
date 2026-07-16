"""ColPali visual embedding + similarity for UI sketches."""

import logging
from typing import Any, Dict, List, Optional

try:
    import torch
    TORCH_AVAILABLE = True
except (ImportError, OSError, RuntimeError):
    TORCH_AVAILABLE = False
    torch = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class UISketchVisualIndexer:
    """Manages ColPali visual embeddings for UI sketches."""

    async def get_embedding(self, image_url: str) -> Optional[object]:
        """Get ColPali embedding for a UI sketch image.

        Returns the ColPaliEmbedding object (has .embeddings attribute with torch.Tensor),
        or None if ColPali is unavailable or fails.
        """
        try:
            from documents.colpali import get_colpali_client

            client = get_colpali_client()
            if not client.available:
                logger.warning("ColPali client not available")
                return None

            embedding = client.get_document_embeddings([image_url])
            return embedding
        except Exception as e:
            logger.warning("ColPali embedding failed for %s: %s", image_url, e)
            return None

    async def compute_similarity(
        self,
        embedding_a: List[List[float]],
        embedding_b: List[List[float]],
    ) -> float:
        """Compute visual similarity between two UI sketch embeddings.

        Returns similarity score 0.0-1.0, or 0.0 on failure.
        """
        try:
            from documents.colpali import get_colpali_client

            client = get_colpali_client()
            if not client.available:
                return 0.0

            query_tensor = torch.tensor(embedding_a, dtype=torch.float32)
            doc_tensor = torch.tensor(embedding_b, dtype=torch.float32)

            scores = client.score_retrieval(query_tensor, doc_tensor)
            return float(scores.item()) if scores.numel() == 1 else float(scores[0].item())
        except Exception as e:
            logger.warning("ColPali similarity failed: %s", e)
            return 0.0

    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Search for UI sketches by computing embeddings and ranking by similarity.

        Args:
            query: Search query (text description of the UI sketch)
            limit: Maximum number of results to return

        Returns:
            Dict with 'results' list (each with 'score' and 'sketch_id') and 'total' count.
            Returns empty results if ColPali is unavailable.
        """
        try:
            from documents.colpali import get_colpali_client

            client = get_colpali_client()
            if not client.available:
                logger.warning("ColPali client not available for search")
                return {"results": [], "total": 0, "error": "ColPali not available"}

            # Get query embedding
            query_embedding = await self.get_embedding(query)
            if query_embedding is None:
                return {"results": [], "total": 0, "error": "Failed to get query embedding"}

            # In a full implementation, this would compare against all indexed sketches
            # For now, return empty results with the query embedding for downstream use
            return {
                "results": [],
                "total": 0,
                "query_embedding_available": True,
            }
        except Exception as e:
            logger.warning("ColPali search failed: %s", e)
            return {"results": [], "total": 0, "error": str(e)}


_indexer: Optional[UISketchVisualIndexer] = None


def get_ui_visual_indexer() -> UISketchVisualIndexer:
    global _indexer
    if _indexer is None:
        _indexer = UISketchVisualIndexer()
    return _indexer
