"""
Code Analysis Tools - MCP tools for code analysis using CodeGraphContext.

This module provides a unified interface to code analysis capabilities
powered by CodeGraphContext. All functionality is backed by
retrieval.code_graph module functions.
"""

from typing import Any

from retrieval.code_graph import (
    CodeGraphRetriever,
)


class CodeAnalysisTools:
    """CodeGraphContext-powered analysis tools.

    Provides unified access to code quality analysis, impact analysis,
    and architecture understanding via CodeGraphContext.
    """

    def __init__(self, repo_path: str | None = None):
        """Initialize with optional repo_path for targeted analysis."""
        self.retriever = CodeGraphRetriever(repo_path=repo_path)

    async def analyze_complexity(self, function_name: str) -> dict[str, Any]:
        """Get cyclomatic complexity for a specific function.

        Args:
            function_name: Name of the function to analyze.

        Returns:
            Dict with complexity score and metadata.
        """
        return await self.retriever.get_complexity(function_name)

    async def find_dead_code(
        self,
        exclude_decorators: list[str] | None = None,
    ) -> dict[str, Any]:
        """Find potentially unused/unreachable functions.

        Args:
            exclude_decorators: List of decorator names to exclude from results.

        Returns:
            Dict with list of potentially dead code functions.
        """
        return await self.retriever.get_dead_code(
            exclude_decorated_with=exclude_decorators,
        )

    async def find_callers(self, function_name: str) -> dict[str, Any]:
        """Find functions that call the given function.

        Args:
            function_name: Name of the function to find callers for.

        Returns:
            Dict with list of calling functions.
        """
        return await self.retriever.find_callers(function_name)

    async def find_callees(self, function_name: str) -> dict[str, Any]:
        """Find functions called by the given function.

        Args:
            function_name: Name of the function to find callees for.

        Returns:
            Dict with list of called functions.
        """
        return await self.retriever.find_callees(function_name)

    async def analyze_dependencies(self, module_name: str) -> dict[str, Any]:
        """Get module dependencies for a given module.

        Args:
            module_name: Name of the module to analyze.

        Returns:
            Dict with list of dependencies.
        """
        return await self.retriever.get_module_deps(module_name)

    async def analyze_class_hierarchy(self, class_name: str) -> dict[str, Any]:
        """Get class inheritance tree.

        Args:
            class_name: Name of the class to analyze.

        Returns:
            Dict with class hierarchy information.
        """
        return await self.retriever.get_class_hierarchy(class_name)

    async def get_call_chain(self, function_name: str) -> dict[str, Any]:
        """Get full call chain for a function.

        Args:
            function_name: Name of the function.

        Returns:
            Dict with call chain (who it calls and who calls it).
        """
        return await self.retriever.get_call_chain(function_name)

    async def get_most_complex(self, limit: int = 10) -> dict[str, Any]:
        """Get most complex functions by cyclomatic complexity."""
        return await self.retriever.get_most_complex_functions(limit=limit)


def get_code_analysis_tools(repo_path: str | None = None) -> CodeAnalysisTools:
    """Factory function to get CodeAnalysisTools instance."""
    return CodeAnalysisTools(repo_path=repo_path)
