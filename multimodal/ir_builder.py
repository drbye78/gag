import asyncio
import hashlib
import logging
from typing import Any, Callable, Dict, List, Optional

from models.ir import (
    ArchitectureIR,
    ArtifactStatus,
    DocumentIR,
    IRNode,
    UIIR,
    CodeIR,
)

logger = logging.getLogger(__name__)

_indexing: Optional[Any] = None
_embedder: Optional[Any] = None
_ingestion_callbacks: List[Callable[..., Any]] = []


def _get_indexer() -> tuple:
    global _indexing
    if _indexing is None:
        from ingestion.indexer import VectorIndexer, GraphIndexer

        _indexing = (VectorIndexer, GraphIndexer)
    return _indexing  # type: ignore[return-value]


def _get_embedder():
    global _embedder
    if _embedder is None:
        from ingestion.embedder import get_embedding_pipeline

        _embedder = get_embedding_pipeline()
    return _embedder


def register_ingestion_callback(callback: Callable[..., Any]) -> None:
    if callback not in _ingestion_callbacks:
        _ingestion_callbacks.append(callback)


def unregister_ingestion_callback(callback: Callable[..., Any]) -> None:
    if callback in _ingestion_callbacks:
        _ingestion_callbacks.remove(callback)


def _notify_ingestion_callbacks(source: str, nodes: List[IRNode]) -> None:
    for callback in _ingestion_callbacks:
        try:
            callback(source, nodes)
        except Exception as e:
            logger.error("Ingestion callback failed for source %s: %s", source, e)


class IRBuilder:
    def __init__(self):
        self._nodes: List[IRNode] = []
        self._seen_ids: set = set()

    def _generate_id(self, content: str, prefix: str = "ir") -> str:
        hash_str = hashlib.sha256(content.encode()).hexdigest()[:12]
        return f"{prefix}_{hash_str}"

    def _deduplicate(self, node: IRNode) -> bool:
        if node.id in self._seen_ids:
            return False
        self._seen_ids.add(node.id)
        return True

    def add_architecture(
        self,
        content: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        architecture_type: Optional[str] = None,
        **kwargs,
    ) -> Optional[ArchitectureIR]:
        ir_id = self._generate_id(content, "arch")
        node = ArchitectureIR(
            id=ir_id,
            content=content,
            title=title or "Architecture",
            description=description,
            architecture_type=architecture_type,
            status=ArtifactStatus.PROCESSED,
            **kwargs,
        )
        if self._deduplicate(node):
            self._nodes.append(node)
            return node
        return None

    def add_ui(
        self,
        content: str,
        title: Optional[str] = None,
        ui_type: Optional[str] = None,
        framework: Optional[str] = None,
        **kwargs,
    ) -> Optional[UIIR]:
        ir_id = self._generate_id(content, "ui")
        node = UIIR(
            id=ir_id,
            content=content,
            title=title or "UI Component",
            ui_type=ui_type,
            framework=framework,
            status=ArtifactStatus.PROCESSED,
            **kwargs,
        )
        if self._deduplicate(node):
            self._nodes.append(node)
            # Graph-first: build graph nodes if extraction result available
            if "extraction_result" in kwargs:
                try:
                    from ui.graph_builder import UIGraphBuilder
                    from ui.pattern_matcher import get_pattern_matcher
                    builder = UIGraphBuilder()
                    er = kwargs["extraction_result"]
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(builder.build(er))
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(builder.build(er))
                        finally:
                            loop.close()
                    node.graph_node_id = er.sketch.sketch_id
                    node.element_count = len(er.elements)
                    matcher = get_pattern_matcher()
                    matches = matcher.match_patterns(er)
                    node.pattern_matches = [m.pattern_name for m in matches]
                except Exception as e:
                    logging.getLogger(__name__).warning("UI graph build failed: %s", e)
            return node
        return None

    def add_code(
        self,
        content: str,
        title: Optional[str] = None,
        language: Optional[str] = None,
        file_path: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_name: Optional[str] = None,
        **kwargs,
    ) -> Optional[CodeIR]:
        ir_id = self._generate_id(content, "code")
        node = CodeIR(
            id=ir_id,
            content=content,
            title=title,
            language=language,
            file_path=file_path,
            entity_type=entity_type,
            entity_name=entity_name,
            status=ArtifactStatus.PROCESSED,
            **kwargs,
        )
        if self._deduplicate(node):
            self._nodes.append(node)
            return node
        return None

    def add_document(
        self,
        content: str,
        title: Optional[str] = None,
        doc_type: Optional[str] = None,
        url: Optional[str] = None,
        **kwargs,
    ) -> Optional[DocumentIR]:
        ir_id = self._generate_id(content, "doc")
        node = DocumentIR(
            id=ir_id,
            content=content,
            title=title or "Document",
            doc_type=doc_type,
            url=url,
            status=ArtifactStatus.PROCESSED,
            **kwargs,
        )
        if self._deduplicate(node):
            self._nodes.append(node)
            return node
        return None

    def build(self) -> List[IRNode]:
        return self._nodes

    async def index_ir_nodes(
        self,
        source: str = "ir_builder",
        vector_indexer: Optional[Any] = None,
        graph_indexer: Optional[Any] = None,
    ) -> Dict[str, Any]:
        if not self._nodes:
            return {"indexed": 0, "errors": ["No nodes to index"]}

        nodes = self._nodes
        text_content = [node.content for node in nodes]
        results = {"indexed": 0, "errors": [], "source": source}

        try:
            VectorIndexerCls, GraphIndexerCls = _get_indexer()
            embed = _get_embedder()

            vi = vector_indexer or VectorIndexerCls()

            embeddings = []
            for text in text_content:
                emb = await embed.embed(text)
                embeddings.append(emb)

            for i, node in enumerate(nodes):
                node.status = ArtifactStatus.INDEXED

            index_result = await vi.index_chunks(
                [f"{node.id}: {node.content[:200]}" for node in nodes],
                [node.id for node in nodes],
                [
                    node.artifact_type.value if node.artifact_type else "unknown"
                    for node in nodes
                ],
            )
            results["indexed"] = (
                index_result.indexed_count
                if hasattr(index_result, "indexed_count")
                else len(nodes)
            )
            results["errors"] = (
                index_result.errors if hasattr(index_result, "errors") else []
            )

            _notify_ingestion_callbacks(source, nodes)

        except Exception as e:
            results["errors"].append(str(e))

        return results

    def validate(self, node: IRNode) -> bool:
        if not node.id or not node.content:
            return False
        if not node.artifact_type:
            return False
        return True

    def process_batch(self, raw_outputs: List[Dict[str, Any]]) -> List[IRNode]:
        for raw in raw_outputs:
            content = raw.get("content", "")
            ir_type = raw.get("type", "document")
            metadata = raw.get("metadata", {})

            if ir_type == "architecture":
                self.add_architecture(content, **metadata)
            elif ir_type == "ui":
                self.add_ui(content, **metadata)
            elif ir_type == "code":
                self.add_code(content, **metadata)
            else:
                self.add_document(content, doc_type=ir_type, **metadata)

        return self._nodes


_default_builder: Optional[IRBuilder] = None


def get_ir_builder() -> IRBuilder:
    global _default_builder
    if _default_builder is None:
        _default_builder = IRBuilder()
    return _default_builder
