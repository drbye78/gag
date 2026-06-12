"""
Retriever Registry - Self-registering retriever factory.

Allows retrievers to register themselves on import, enabling
new retrievers to be added without modifying the orchestrator.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class RetrieverRegistry:
    """
    Central registry for retrieval components.

    Retrievers self-register via the @register_retriever decorator
    or by calling registry.register() at module level.
    """

    def __init__(self):
        self._retrievers: Dict[str, Callable[[], Any]] = {}
        self._retriever_names: Dict[str, str] = {}  # name -> module path
        self._initialized: bool = False

    def register(
        self,
        name: str,
        factory: Callable[[], Any],
        module_path: Optional[str] = None,
    ) -> None:
        """
        Register a retriever factory.

        Args:
            name: Unique identifier for the retriever (e.g., "docs", "code")
            factory: Callable that returns a retriever instance
            module_path: Optional module path for debugging
        """
        if name in self._retrievers:
            logger.warning(
                "Retriever '%s' already registered, replacing (from %s)",
                name,
                self._retriever_names.get(name, "unknown"),
            )

        self._retrievers[name] = factory
        self._retriever_names[name] = module_path or "unknown"
        logger.debug("Registered retriever: %s (from %s)", name, module_path)

    def get_retriever(self, name: str) -> Any:
        """
        Get a retriever instance by name.

        Args:
            name: The retriever name

        Returns:
            Retriever instance

        Raises:
            KeyError: If retriever not found
        """
        if name not in self._retrievers:
            raise KeyError(
                f"Retriever '{name}' not found. Available: {list(self._retrievers.keys())}"
            )
        return self._retrievers[name]()

    def get_retriever_factory(self, name: str) -> Callable[[], Any]:
        """
        Get the factory function for a retriever without instantiating.

        Args:
            name: The retriever name

        Returns:
            Factory callable

        Raises:
            KeyError: If retriever not found
        """
        if name not in self._retrievers:
            raise KeyError(
                f"Retriever '{name}' not found. Available: {list(self._retrievers.keys())}"
            )
        return self._retrievers[name]

    def list_retrievers(self) -> List[str]:
        """List all registered retriever names."""
        return list(self._retrievers.keys())

    def get_retriever_info(self) -> Dict[str, str]:
        """Get mapping of retriever names to their module paths."""
        return dict(self._retriever_names)

    def is_registered(self, name: str) -> bool:
        """Check if a retriever is registered."""
        return name in self._retrievers

    def clear(self) -> None:
        """Clear all registered retrievers (mainly for testing)."""
        self._retrievers.clear()
        self._retriever_names.clear()
        self._initialized = False


# Global registry instance
_registry: Optional[RetrieverRegistry] = None


def get_registry() -> RetrieverRegistry:
    """Get the global retriever registry instance."""
    global _registry
    if _registry is None:
        _registry = RetrieverRegistry()
    return _registry


def register_retriever(
    name: str,
    module_path: Optional[str] = None,
) -> Callable[[Callable[[], Any]], Callable[[], Any]]:
    """
    Decorator to register a retriever factory.

    Usage:
        @register_retriever("docs", "retrieval.docs")
        def get_docs_retriever():
            return DocsRetriever()
    """

    def decorator(factory: Callable[[], Any]) -> Callable[[], Any]:
        registry = get_registry()
        registry.register(name, factory, module_path)
        return factory

    return decorator


# Import all retriever modules to trigger self-registration
def _load_all_retrievers() -> None:
    """Load all retriever modules to trigger their self-registration."""
    # Core retrievers - always available

    # Optional retrievers - may fail on import due to missing deps
    try:
        from retrieval import diagram
    except ImportError:
        logger.debug("Diagram retriever not available (missing optional deps)")

    try:
        from retrieval import colbert
    except ImportError:
        logger.debug("ColBERT retriever not available (missing optional deps)")

    try:
        from retrieval import hybrid
    except ImportError:
        logger.debug("Hybrid retriever not available (missing optional deps)")

    try:
        from retrieval import classifier
    except ImportError:
        logger.debug("Classifier not available (missing optional deps)")

    # UI retriever is in a separate module
    try:
        from ui import retriever as ui_retriever
    except ImportError:
        logger.debug("UI retriever not available (missing optional deps)")


def initialize_registry() -> RetrieverRegistry:
    """
    Initialize the registry by loading all retriever modules.

    This is called once at startup to register all available retrievers.
    """
    registry = get_registry()
    if not registry._initialized:
        _load_all_retrievers()
        registry._initialized = True
        logger.info(
            "Initialized retriever registry with: %s",
            registry.list_retrievers(),
        )
    return registry
