"""
Semantic Chunker - LlamaIndex chunking integration.

Provides all LlamaIndex chunkers as alternatives:
- SemanticChunker (semantic)
- SentenceSplitter (basic)
- JSONSplitter, XMLSplitter (structured)
- HTMLTagSplitter (HTML)
"""

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from llama_index.core.node_parser import (
    SemanticSplitterNodeParser as LISemanticChunker,
    SentenceSplitter as LISentenceSplitter,
    JSONNodeParser as LIJSONSplitter,
    HTMLNodeParser as LIHTMLTagSplitter,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from ingestion.chunker import Chunk, ChunkResult, TextChunker


@dataclass
class SemanticChunkResult:
    chunks: List[Chunk]
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence_scores: List[float] = field(default_factory=list)


class LlamaIndexSentenceChunker(TextChunker):
    """Using LlamaIndex SentenceSplitter for basic text chunking."""

    def __init__(
        self,
        chunk_size: int = 1024,
        chunk_overlap: int = 200,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._parser = LISentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    @property
    def available(self) -> bool:
        return True

    def chunk(self, text: str, source_id: str) -> ChunkResult:
        start = time.time()
        parser = self._parser

        try:
            nodes = parser.get_nodes_from_documents([{"text": text}])
            chunks = [
                Chunk(
                    id=f"{source_id}_chunk_{i}",
                    content=node.text or "",
                    chunk_index=i,
                    start_char=0,
                    end_char=len(node.text or ""),
                    metadata={"node_id": node.id_},
                )
                for i, node in enumerate(nodes)
            ]
            return ChunkResult(
                source_id=source_id,
                source_type="llama_sentence",
                chunks=chunks,
                total_chars=sum(len(c.content) for c in chunks),
                took_ms=int((time.time() - start) * 1000),
            )
        except Exception:
            from ingestion.chunker import DocumentChunker

            fallback = DocumentChunker(chunk_size=self.chunk_size)
            return fallback.chunk(text, source_id)


class LlamaIndexJSONChunker(TextChunker):
    """Using LlamaIndex JSONSplitter."""

    def __init__(self, depth: int = 2, enablePagination: bool = True):
        self.depth = depth
        self.enablePagination = enablePagination
        self._parser = LIJSONSplitter(
            depth=depth,
            enablePagination=enablePagination,
        )

    @property
    def available(self) -> bool:
        return True

    def chunk(self, text: str, source_id: str) -> ChunkResult:
        start = time.time()
        parser = self._parser

        try:
            nodes = parser.get_nodes_from_documents([{"text": text}])
            chunks = [
                Chunk(
                    id=f"{source_id}_chunk_{i}",
                    content=node.text or "",
                    chunk_index=i,
                    start_char=0,
                    end_char=len(node.text or ""),
                    metadata={"node_id": node.id_, "type": "json"},
                )
                for i, node in enumerate(nodes)
            ]
            return ChunkResult(
                source_id=source_id,
                source_type="llama_json",
                chunks=chunks,
                total_chars=sum(len(c.content) for c in chunks),
                took_ms=int((time.time() - start) * 1000),
            )
        except Exception:
            return ChunkResult(
                source_id=source_id,
                source_type="json",
                chunks=[],
                total_chars=0,
                took_ms=0,
            )


class LlamaIndexHTMLChunker(TextChunker):
    """Using LlamaIndex HTMLTagSplitter."""

    def __init__(self, tags: Optional[List[str]] = None):
        self.tags = tags or ["p", "div", "section", "article"]
        self._parser = LIHTMLTagSplitter(tags=self.tags)

    @property
    def available(self) -> bool:
        return True

    def chunk(self, text: str, source_id: str) -> ChunkResult:
        start = time.time()
        parser = self._parser

        try:
            nodes = parser.get_nodes_from_documents([{"text": text}])
            chunks = [
                Chunk(
                    id=f"{source_id}_chunk_{i}",
                    content=node.text or "",
                    chunk_index=i,
                    start_char=0,
                    end_char=len(node.text or ""),
                    metadata={"node_id": node.id_, "type": "html"},
                )
                for i, node in enumerate(nodes)
            ]
            return ChunkResult(
                source_id=source_id,
                source_type="llama_html",
                chunks=chunks,
                total_chars=sum(len(c.content) for c in chunks),
                took_ms=int((time.time() - start) * 1000),
            )
        except Exception:
            return ChunkResult(
                source_id=source_id,
                source_type="html",
                chunks=[],
                total_chars=0,
                took_ms=0,
            )


class SemanticTextChunker(TextChunker):
    """Using LlamaIndex SemanticChunker for semantic chunking."""

    def __init__(
        self,
        embed_model: str = "BAAI/bge-small-en-v1.5",
        breakpoint_percentile_threshold: float = 95,
        buffer_size: int = 1,
    ):
        self.embed_model = embed_model
        self.breakpoint_percentile_threshold = breakpoint_percentile_threshold
        self.buffer_size = buffer_size
        self._parser = None

    @property
    def available(self) -> bool:
        return True

    def _get_parser(self):
        if self._parser is None:
            embed = HuggingFaceEmbedding(model_name=self.embed_model)
            self._parser = LISemanticChunker(
                embed_model=embed,
                breakpoint_percentile_threshold=self.breakpoint_percentile_threshold,
                buffer_size=self.buffer_size,
            )
        return self._parser

    def chunk(self, text: str, source_id: str) -> ChunkResult:
        start = time.time()
        parser = self._get_parser()

        try:
            nodes = parser.get_nodes_from_documents([{"text": text}])
            chunks = [
                Chunk(
                    id=f"{source_id}_chunk_{i}",
                    content=node.text or "",
                    chunk_index=i,
                    start_char=0,
                    end_char=len(node.text or ""),
                    metadata={"node_id": node.id_},
                )
                for i, node in enumerate(nodes)
            ]
            return ChunkResult(
                source_id=source_id,
                source_type="semantic",
                chunks=chunks,
                total_chars=sum(len(c.content) for c in chunks),
                took_ms=int((time.time() - start) * 1000),
            )
        except Exception:
            from ingestion.chunker import DocumentChunker

            fallback = DocumentChunker()
            return fallback.chunk(text, source_id)


class MarkdownImageExtractor:
    """Extract images from markdown and parse them."""

    def __init__(self):
        self._vision_parser = None

    @property
    def available(self) -> bool:
        return True

    def _get_vision_parser(self):
        if self._vision_parser is None:
            from documents.multimodal import get_multimodal_parser

            self._vision_parser = get_multimodal_parser()
        return self._vision_parser

    def extract_images(self, markdown_text: str) -> List[Dict[str, Any]]:
        """Extract all image references from markdown."""
        images = []
        for match in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", markdown_text):
            url = match.group(2)
            alt = match.group(1)
            if url:
                images.append(
                    {
                        "url": url.strip(),
                        "alt": alt.strip() if alt else "",
                        "context": markdown_text[max(0, match.start() - 200) : match.end() + 200],
                    }
                )
        return images

    async def parse_with_images(
        self,
        markdown_text: str,
        source_id: str,
    ) -> Dict[str, Any]:
        """Parse markdown and extract referenced images."""
        parts = {"markdown": "", "extracted_images": [], "diagram_results": []}
        parts["markdown"] = markdown_text

        images = self.extract_images(markdown_text)
        if images:
            vision_parser = self._get_vision_parser()
            for img in images[:5]:
                try:
                    if img["url"].startswith("http"):
                        result = await vision_parser.parse(img["url"])
                    else:
                        result = await vision_parser.parse_file(img["url"])
                    parts["diagram_results"].append(
                        {
                            "source": img["url"],
                            "text": result.text if hasattr(result, "text") else "",
                            "elements": getattr(result, "elements", []),
                            "context": img.get("context", "")[:100],
                        }
                    )
                except Exception:
                    pass
        return parts


class HTMLImageExtractor:
    """Extract images from HTML and parse them."""

    def __init__(self):
        self._vision_parser = None

    def _get_vision_parser(self):
        if self._vision_parser is None:
            from documents.multimodal import get_multimodal_parser

            self._vision_parser = get_multimodal_parser()
        return self._vision_parser

    def extract_images(self, html_text: str) -> List[Dict[str, Any]]:
        """Extract all image references from HTML."""
        images = []
        patterns = [
            r'<img[^>]+src="([^"]+)"',
            r"<img[^>]+src=([^\s>]+)",
            r'url\(["\']?([^"\'()]+)["\']?\)',
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, html_text, re.IGNORECASE):
                url = match.group(1)
                if url and any(
                    ext in url.lower() for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"]
                ):
                    images.append(
                        {
                            "url": url.strip(),
                            "context": html_text[max(0, match.start() - 100) : match.end() + 100],
                        }
                    )
        return images

    async def parse_with_images(
        self,
        html_text: str,
        source_id: str,
    ) -> Dict[str, Any]:
        """Parse HTML and extract referenced images."""
        parts = {"html": "", "extracted_images": [], "ui_results": []}
        parts["html"] = html_text

        images = self.extract_images(html_text)
        if images:
            vision_parser = self._get_vision_parser()
            for img in images[:5]:
                try:
                    result = await vision_parser.parse(img["url"])
                    parts["ui_results"].append(
                        {
                            "source": img["url"],
                            "text": result.text if hasattr(result, "text") else "",
                            "ui_elements": getattr(result, "ui_components", []),
                        }
                    )
                except Exception:
                    pass
        return parts


def get_sentence_chunker(
    chunk_size: int = 1024,
    chunk_overlap: int = 200,
) -> LlamaIndexSentenceChunker:
    """Get SentenceSplitter-based chunker."""
    return LlamaIndexSentenceChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def get_sentence_chunker_from_settings() -> LlamaIndexSentenceChunker:
    """Get SentenceSplitter chunker from config settings."""
    from core.config import get_settings

    settings = get_settings()
    return LlamaIndexSentenceChunker(
        chunk_size=settings.chunking_sentence_size,
        chunk_overlap=settings.chunking_sentence_overlap,
    )


def get_json_chunker(
    depth: int = 2,
    enablePagination: bool = True,
) -> LlamaIndexJSONChunker:
    """Get JSONSplitter-based chunker."""
    return LlamaIndexJSONChunker(depth=depth, enablePagination=enablePagination)


def get_html_chunker(
    tags: Optional[List[str]] = None,
) -> LlamaIndexHTMLChunker:
    """Get HTMLTagSplitter-based chunker."""
    return LlamaIndexHTMLChunker(tags=tags)


def get_semantic_chunker(
    embed_model: str = "BAAI/bge-small-en-v1.5",
    breakpoint_percentile_threshold: float = 95,
) -> SemanticTextChunker:
    """Get SemanticChunker-based chunker."""
    return SemanticTextChunker(
        embed_model=embed_model,
        breakpoint_percentile_threshold=breakpoint_percentile_threshold,
    )


def get_semantic_chunker_from_settings() -> SemanticTextChunker:
    """Get semantic chunker from config settings."""
    from core.config import get_settings

    settings = get_settings()
    return SemanticTextChunker(
        embed_model=settings.chunking_semantic_embed_model,
        breakpoint_percentile_threshold=int(settings.chunking_semantic_threshold * 100),
    )


def get_chunker_from_settings():
    """Get chunker based on config settings."""
    from core.config import get_settings

    settings = get_settings()
    chunk_type = settings.chunking_chunker_type

    chunkers = {
        "semantic": get_semantic_chunker_from_settings,
        "sentence": get_sentence_chunker_from_settings,
    }

    if chunk_type not in chunkers:
        import logging

        logging.getLogger(__name__).warning(
            f"Unknown chunker type '{chunk_type}', defaulting to semantic"
        )
        chunk_type = "semantic"

    return chunkers[chunk_type]()


def get_markdown_image_parser() -> MarkdownImageExtractor:
    """Get markdown image parser."""
    return MarkdownImageExtractor()


def get_html_image_parser() -> HTMLImageExtractor:
    """Get HTML image parser."""
    return HTMLImageExtractor()
