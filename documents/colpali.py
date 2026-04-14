"""
ColPali Integration - Visual Document Retrieval with Late Interaction.

Implements ColPali/ColQwen2 for visual-first document retrieval.
Based on HuggingFace transformers ColVision architecture.

Models:
- vidore/colpali-v1.3-hf (3B, Gemma-based)
- vidore/colqwen2-v1.0 (Qwen-based)
- vidore/colSmol-500M (500M, lightweight)
"""

import io
import base64
import torch
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from PIL import Image


COLPALI_AVAILABLE = False
ColPaliForRetrieval = None
ColPaliProcessor = None
ColQwen2 = None
ColQwen2Processor = None

try:
    from transformers import ColPaliForRetrieval, ColPaliProcessor

    COLPALI_AVAILABLE = True
except ImportError:
    try:
        from colpali_engine.models import ColQwen2, ColQwen2Processor

        ColPaliForRetrieval = ColQwen2
        ColPaliProcessor = ColQwen2Processor
        COLPALI_AVAILABLE = True
    except ImportError:
        ColPaliForRetrieval = None
        ColPaliProcessor = None


class ColPaliModel(str, Enum):
    COLPALI_3B = "vidore/colpali-v1.3-hf"
    COLQWEN2 = "vidore/colqwen2-v1.0"
    COLSMOL_500M = "vidore/colsmol-500m"
    COLSMOL_256M = "vidore/colsmol-256m"


@dataclass
class ColPaliEmbedding:
    embeddings: torch.Tensor
    num_tokens: int
    model_name: str


@dataclass
class ColPaliSearchResult:
    doc_id: str
    score: float
    page_num: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ColPaliResult:
    query: str
    results: List[ColPaliSearchResult]
    query_embedding: Optional[torch.Tensor] = None
    documents_embedding: Optional[torch.Tensor] = None
    took_ms: int = 0
    error: Optional[str] = None


class ColPaliClient:
    def __init__(
        self,
        model_name: str = ColPaliModel.COLQWEN2.value,
        device: Optional[str] = None,
        torch_dtype: torch.dtype = torch.bfloat16,
    ):
        self.model_name = model_name
        self.device = device or _get_device()
        self.torch_dtype = torch_dtype
        self._model = None
        self._processor = None

    @property
    def available(self) -> bool:
        return COLPALI_AVAILABLE

    def _get_model(self):
        if not self.available:
            raise RuntimeError(
                "ColPali not available. Install: pip install colpali-engine"
            )

        if self._model is None:
            if "qwen" in self.model_name.lower():
                self._model = ColQwen2.from_pretrained(
                    self.model_name,
                    torch_dtype=self.torch_dtype,
                    device_map=self.device,
                ).eval()
            else:
                self._model = ColPaliForRetrieval.from_pretrained(
                    self.model_name,
                    torch_dtype=self.torch_dtype,
                    device_map=self.device,
                ).eval()

        return self._model

    def _get_processor(self):
        if not self.available:
            raise RuntimeError(
                "ColPali not available. Install: pip install colpali-engine"
            )

        if self._processor is None:
            if "qwen" in self.model_name.lower():
                self._processor = ColQwen2Processor.from_pretrained(self.model_name)
            else:
                self._processor = ColPaliProcessor.from_pretrained(self.model_name)

        return self._processor

    def _load_image(self, source: Any) -> Image.Image:
        if isinstance(source, Image.Image):
            return source
        elif isinstance(source, bytes):
            return Image.open(io.BytesIO(source))
        elif isinstance(source, str):
            if source.startswith("data:image"):
                b64 = source.split(",")[1]
                return Image.open(io.BytesIO(base64.b64decode(b64)))
            else:
                return Image.open(source)
        else:
            return Image.new("RGB", (448, 448), color="white")

    def get_query_embedding(self, queries: List[str]) -> ColPaliEmbedding:
        model = self._get_model()
        processor = self._get_processor()

        queries = [q if q else " " for q in queries]
        queries_tensor = processor(text=queries).to(model.device)

        with torch.no_grad():
            query_embeddings = model(**queries_tensor)

        return ColPaliEmbedding(
            embeddings=query_embeddings.embeddings,
            num_tokens=query_embeddings.embeddings.shape[1],
            model_name=self.model_name,
        )

    def get_document_embeddings(
        self,
        images: List[Any],
        return_tensors: bool = False,
    ) -> ColPaliEmbedding:
        model = self._get_model()
        processor = self._get_processor()

        pil_images = [self._load_image(img) for img in images]

        images_tensor = processor(images=pil_images).to(model.device)

        with torch.no_grad():
            doc_embeddings = model(**images_tensor)

        result = ColPaliEmbedding(
            embeddings=doc_embeddings.embeddings,
            num_tokens=doc_embeddings.embeddings.shape[1],
            model_name=self.model_name,
        )

        if return_tensors:
            return result

        return result

    def score_retrieval(
        self,
        query_embeddings: torch.Tensor,
        doc_embeddings: torch.Tensor,
    ) -> torch.Tensor:
        processor = self._get_processor()
        scores = processor.score_retrieval(query_embeddings, doc_embeddings)
        return scores

    async def index_document(
        self,
        source: Any,
        doc_id: str,
    ) -> Dict[str, Any]:
        try:
            import time

            start = int(time.time() * 1000)

            image = self._load_image(source)
            embedding = self.get_document_embeddings([image])

            return {
                "doc_id": doc_id,
                "embedding": embedding.embeddings.cpu().tolist(),
                "num_tokens": embedding.num_tokens,
                "model": self.model_name,
                "took_ms": int(time.time() * 1000) - start,
            }
        except Exception as e:
            return {"doc_id": doc_id, "error": str(e)}

    async def search(
        self,
        query: str,
        indexed_docs: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> ColPaliResult:
        import time

        start = int(time.time() * 1000)

        try:
            query_emb = self.get_query_embedding([query])
            doc_embeddings = []
            valid_docs = []

            for doc in indexed_docs:
                if "embedding" in doc:
                    emb = torch.tensor(
                        doc["embedding"],
                        dtype=query_emb.embeddings.dtype,
                        device=query_emb.embeddings.device,
                    )
                    doc_embeddings.append(emb)
                    valid_docs.append(doc)

            if not doc_embeddings:
                return ColPaliResult(
                    query=query,
                    results=[],
                    error="No documents with embeddings",
                )

            stacked_docs = torch.cat(doc_embeddings, dim=0)

            scores = self.score_retrieval(
                query_emb.embeddings,
                stacked_docs,
            )

            final_top_k = min(top_k, len(valid_docs))
            top_scores, top_indices = torch.topk(scores.squeeze(), final_top_k)

            results = []
            for i_idx in range(final_top_k):
                idx_val = top_indices[i_idx].item()
                score_val = top_scores[i_idx].item()
                doc = valid_docs[idx_val]
                results.append(
                    ColPaliSearchResult(
                        doc_id=doc.get("doc_id", f"doc_{idx_val}"),
                        score=score_val,
                        page_num=doc.get("page_num", 0),
                        metadata=doc.get("metadata", {}),
                    )
                )

            return ColPaliResult(
                query=query,
                results=results,
                took_ms=int(time.time() * 1000) - start,
            )

        except Exception as e:
            return ColPaliResult(
                query=query,
                results=[],
                error=str(e),
                took_ms=int(time.time() * 1000) - start,
            )


def _get_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    return "cpu"


_colpali_client: Optional[ColPaliClient] = None


def get_colpali_client(
    model: str = ColPaliModel.COLQWEN2.value,
) -> ColPaliClient:
    global _colpali_client
    if _colpali_client is None:
        _colpali_client = ColPaliClient(model_name=model)
    return _colpali_client
