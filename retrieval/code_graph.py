"""
CodeGraph Retriever - Code-specific graph queries via CodeGraphContext.

Wraps CodeGraphContext MCP for precise code relationships,
complexity metrics, and navigation (find_callers, callees, etc.).
"""

import time
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from CodeGraphContext_find_code import find_code
    from CodeGraphContext_analyze_code_relationships import (
        analyze_code_relationships,
    )
    from CodeGraphContext_find_dead_code import find_dead_code
    from CodeGraphContext_find_most_complex_functions import (
        find_most_complex_functions,
    )
    from CodeGraphContext_calculate_cyclomatic_complexity import (
        calculate_cyclomatic_complexity,
    )

    CODEGRAPH_AVAILABLE = True
except ImportError:
    CODEGRAPH_AVAILABLE = False
    find_code = None
    analyze_code_relationships = None
    find_dead_code = None
    find_most_complex_functions = None
    calculate_cyclomatic_complexity = None


class CodeGraphQueryType(str, Enum):
    FIND_CALLERS = "find_callers"
    FIND_CALLEES = "find_callees"
    FIND_ALL_CALLERS = "find_all_callers"
    FIND_ALL_CALLEES = "find_all_callees"
    FIND_IMPORTERS = "find_importers"
    CLASS_HIERARCHY = "class_hierarchy"
    OVERRIDES = "overrides"
    DEAD_CODE = "dead_code"
    COMPLEXITY = "complexity"
    CALL_CHAIN = "call_chain"
    MODULE_DEPS = "module_deps"
    FIND_DEFINITION = "find_definition"
    FIND_REFERENCES = "find_references"


class CodeGraphRetriever:
    """Code-specific retriever using CodeGraphContext MCP."""

    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = repo_path

    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generic code search via content matching."""
        if not CODEGRAPH_AVAILABLE:
            return {
                "source": "code_graph",
                "query": query,
                "results": [],
                "total": 0,
                "took_ms": 0,
                "error": "CodeGraphContext not available",
            }

        start = int(time.time() * 1000)

        result = await find_code(query=query, repo_path=self.repo_path)

        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "query": query,
            "results": result.get("ranked_results", []),
            "total": result.get("total_matches", 0),
            "took_ms": took,
        }

    async def find_callers(
        self,
        function_name: str,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Find functions that call the given function."""
        if not CODEGRAPH_AVAILABLE:
            return {
                "source": "code_graph",
                "query": f"callers_of:{function_name}",
                "results": [],
                "total": 0,
                "took_ms": 0,
                "error": "CodeGraphContext not available",
            }

        start = int(time.time() * 1000)

        result = await analyze_code_relationships(
            query_type=CodeGraphQueryType.FIND_CALLERS.value,
            target=function_name,
            context=self.repo_path,
        )

        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "query": f"callers_of:{function_name}",
            "results": result.get("results", []),
            "total": len(result.get("results", [])),
            "took_ms": took,
        }

    async def find_callees(
        self,
        function_name: str,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Find functions called by the given function."""
        if not CODEGRAPH_AVAILABLE:
            return {
                "source": "code_graph",
                "query": f"callees_of:{function_name}",
                "results": [],
                "total": 0,
                "took_ms": 0,
                "error": "CodeGraphContext not available",
            }

        start = int(time.time() * 1000)

        result = await analyze_code_relationships(
            query_type=CodeGraphQueryType.FIND_CALLEES.value,
            target=function_name,
            context=self.repo_path,
        )

        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "query": f"callees_of:{function_name}",
            "results": result.get("results", []),
            "total": len(result.get("results", [])),
            "took_ms": took,
        }

    async def find_all_callers(
        self,
        function_name: str,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Find all callers (transitive) of the given function."""
        if not CODEGRAPH_AVAILABLE:
            return {
                "source": "code_graph",
                "query": f"all_callers_of:{function_name}",
                "results": [],
                "total": 0,
                "took_ms": 0,
                "error": "CodeGraphContext not available",
            }

        start = int(time.time() * 1000)

        result = await analyze_code_relationships(
            query_type=CodeGraphQueryType.FIND_ALL_CALLERS.value,
            target=function_name,
            context=self.repo_path,
        )

        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "query": f"all_callers_of:{function_name}",
            "results": result.get("results", []),
            "total": len(result.get("results", [])),
            "took_ms": took,
        }

    async def find_all_callees(
        self,
        function_name: str,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Find all callees (transitive) of the given function."""
        if not CODEGRAPH_AVAILABLE:
            return {
                "source": "code_graph",
                "query": f"all_callees_of:{function_name}",
                "results": [],
                "total": 0,
                "took_ms": 0,
                "error": "CodeGraphContext not available",
            }

        start = int(time.time() * 1000)

        result = await analyze_code_relationships(
            query_type=CodeGraphQueryType.FIND_ALL_CALLEES.value,
            target=function_name,
            context=self.repo_path,
        )

        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "query": f"all_callees_of:{function_name}",
            "results": result.get("results", []),
            "total": len(result.get("results", [])),
            "took_ms": took,
        }

    async def find_importers(
        self,
        module_name: str,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Find files that import the given module."""
        if not CODEGRAPH_AVAILABLE:
            return {
                "source": "code_graph",
                "query": f"importers_of:{module_name}",
                "results": [],
                "total": 0,
                "took_ms": 0,
                "error": "CodeGraphContext not available",
            }

        start = int(time.time() * 1000)

        result = await analyze_code_relationships(
            query_type=CodeGraphQueryType.FIND_IMPORTERS.value,
            target=module_name,
            context=self.repo_path,
        )

        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "query": f"importers_of:{module_name}",
            "results": result.get("results", []),
            "total": len(result.get("results", [])),
            "took_ms": took,
        }

    async def get_class_hierarchy(
        self,
        class_name: str,
    ) -> Dict[str, Any]:
        """Get class hierarchy (parent classes)."""
        if not CODEGRAPH_AVAILABLE:
            return {
                "source": "code_graph",
                "query": f"hierarchy:{class_name}",
                "results": [],
                "took_ms": 0,
                "error": "CodeGraphContext not available",
            }

        start = int(time.time() * 1000)

        result = await analyze_code_relationships(
            query_type=CodeGraphQueryType.CLASS_HIERARCHY.value,
            target=class_name,
            context=self.repo_path,
        )

        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "query": f"hierarchy:{class_name}",
            "results": result.get("results", []),
            "took_ms": took,
        }

    async def get_overrides(
        self,
        method_name: str,
    ) -> Dict[str, Any]:
        """Find methods that override the given method."""
        if not CODEGRAPH_AVAILABLE:
            return {
                "source": "code_graph",
                "query": f"overrides:{method_name}",
                "results": [],
                "took_ms": 0,
                "error": "CodeGraphContext not available",
            }

        start = int(time.time() * 1000)

        result = await analyze_code_relationships(
            query_type=CodeGraphQueryType.OVERRIDES.value,
            target=method_name,
            context=self.repo_path,
        )

        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "query": f"overrides:{method_name}",
            "results": result.get("results", []),
            "took_ms": took,
        }

    async def get_dead_code(
        self,
        exclude_decorated_with: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Find potentially unused functions."""
        if not CODEGRAPH_AVAILABLE:
            return {
                "source": "code_graph",
                "query": "dead_code",
                "results": [],
                "total": 0,
                "took_ms": 0,
                "error": "CodeGraphContext not available",
            }

        start = int(time.time() * 1000)

        result = await find_dead_code(
            exclude_decorated_with=exclude_decorated_with or [],
            repo_path=self.repo_path,
        )

        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "query": "dead_code",
            "results": result.get("functions", []),
            "total": len(result.get("functions", [])),
            "took_ms": took,
        }

    async def get_most_complex_functions(
        self,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Get most complex functions by cyclomatic complexity."""
        if not CODEGRAPH_AVAILABLE:
            return {
                "source": "code_graph",
                "query": "most_complex",
                "results": [],
                "total": 0,
                "took_ms": 0,
                "error": "CodeGraphContext not available",
            }

        start = int(time.time() * 1000)

        result = await find_most_complex_functions(
            limit=limit,
            repo_path=self.repo_path,
        )

        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "query": "most_complex",
            "results": result.get("functions", []),
            "total": len(result.get("functions", [])),
            "took_ms": took,
        }

    async def get_complexity(
        self,
        function_name: str,
        path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get cyclomatic complexity of a specific function."""
        if not CODEGRAPH_AVAILABLE:
            return {
                "source": "code_graph",
                "query": f"complexity:{function_name}",
                "complexity": 0,
                "took_ms": 0,
                "error": "CodeGraphContext not available",
            }

        start = int(time.time() * 1000)

        result = await calculate_cyclomatic_complexity(
            function_name=function_name,
            path=path or self.repo_path,
        )

        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "query": f"complexity:{function_name}",
            "complexity": result.get("complexity", 0),
            "took_ms": took,
        }

    async def execute_query(
        self,
        query_type: str,
        target: str,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Execute any CodeGraphContext query by type."""
        query_map = {
            CodeGraphQueryType.FIND_CALLERS.value: self.find_callers,
            CodeGraphQueryType.FIND_CALLEES.value: self.find_callees,
            CodeGraphQueryType.FIND_ALL_CALLERS.value: self.find_all_callers,
            CodeGraphQueryType.FIND_ALL_CALLEES.value: self.find_all_callees,
            CodeGraphQueryType.FIND_IMPORTERS.value: self.find_importers,
            CodeGraphQueryType.CLASS_HIERARCHY.value: self.get_class_hierarchy,
            CodeGraphQueryType.OVERRIDES.value: self.get_overrides,
            CodeGraphQueryType.DEAD_CODE.value: lambda: self.get_dead_code(),
            CodeGraphQueryType.COMPLEXITY.value: lambda: (
                self.get_most_complex_functions(limit)
            ),
            CodeGraphQueryType.FIND_DEFINITION.value: lambda: self.search(
                target, limit
            ),
        }

        if query_type in query_map:
            return await query_map[query_type](target, limit)

        return await self.search(target, limit)


_code_graph_retriever: Optional[CodeGraphRetriever] = None


def get_code_graph_retriever(repo_path: Optional[str] = None) -> CodeGraphRetriever:
    global _code_graph_retriever
    if _code_graph_retriever is None:
        _code_graph_retriever = CodeGraphRetriever(repo_path=repo_path)
    return _code_graph_retriever
