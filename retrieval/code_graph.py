"""
CodeGraph Retriever - Code-specific graph queries via CodeGraphContext.

Wraps CodeGraphContext MCP for precise code relationships,
complexity metrics, and navigation (find_callers, callees, etc.).
Uses CLI fallback when MCP unavailable.
"""

import json
import logging
import subprocess
import time
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Check for CLI availability (fallback)
def _check_cgc_available() -> bool:
    try:
        result = subprocess.run(
            ["cgc", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

_cgc_available = _check_cgc_available()

# Try MCP imports first, fall back to CLI
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

    from CodeGraphContext_watch_directory import watch_directory
    from CodeGraphContext_add_code_to_graph import add_code_to_graph
    from CodeGraphContext_switch_context import switch_context
    from CodeGraphContext_discover_codegraph_contexts import discover_codegraph_contexts
    from CodeGraphContext_list_indexed_repositories import list_indexed_repositories
    from CodeGraphContext_load_bundle import load_bundle
    from CodeGraphContext_search_registry_bundles import search_registry_bundles
    from CodeGraphContext_add_package_to_graph import add_package_to_graph
    from CodeGraphContext_execute_cypher_query import execute_cypher_query
    from CodeGraphContext_visualize_graph_query import visualize_graph_query

    CODEGRAPH_AVAILABLE = True
    CODEGRAPH_FULL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"CodeGraphContext MCP not available: {e}")
    CODEGRAPH_AVAILABLE = _cgc_available
    CODEGRAPH_FULL_AVAILABLE = _cgc_available

    # CLI fallback functions
    def _run_cgc(args: List[str], timeout: int = 30) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["cgc"] + args,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode == 0:
                output = result.stdout
                # Try JSON first
                try:
                    return {"success": True, "data": json.loads(output)}
                except json.JSONDecodeError:
                    # Parse table output
                    lines = output.strip().split("\n")
                    matches = []
                    for line in lines:
                        # Parse table rows: | Name | Type | Location | Source |
                        if "│" in line and "─" not in line and "╭" not in line and "╰" not in line and "Name" not in line:
                            parts = [p.strip() for p in line.split("│")]
                            if len(parts) >= 3 and parts[1]:
                                matches.append({
                                    "name": parts[1],
                                    "type": parts[2] if len(parts) > 2 else "",
                                    "location": parts[3] if len(parts) > 3 else "",
                                })
                    return {"success": True, "data": matches}
            return {"success": False, "error": result.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def find_code(query: str, limit: int = 10) -> Dict[str, Any]:
        result = await _cgc_find_pattern(query)  # Use the helper
        if result.get("success"):
            data = result.get("results", [])
            return {"results": data[:limit], "total": len(data)}
        return {"results": [], "error": result.get("error")}

    # Helper function to avoid duplicate definitions
    async def _cgc_find_pattern(pattern: str) -> Dict[str, Any]:
        """Call cgc find pattern and parse results."""
        result = subprocess.run(
            ["cgc", "find", "pattern", pattern],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Table output goes to stderr
        combined = result.stdout + "\n" + result.stderr
        lines = combined.strip().split("\n")
        matches = []
        for line in lines:
            if "│" in line and "─" not in line and "╭" not in line and "╰" not in line and "Name" not in line and "Type" not in line:
                parts = [p.strip() for p in line.split("│")]
                if len(parts) >= 3 and parts[1]:
                    matches.append({
                        "name": parts[1],
                        "type": parts[2] if len(parts) > 2 else "",
                        "location": parts[3] if len(parts) > 3 else "",
                    })
        return {"success": result.returncode == 0, "results": matches}

    async def analyze_code_relationships(
        query_type: str,
        target: str,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        cmd_map = {
            "find_callers": ["analyze", "callers", target],
            "find_callees": ["analyze", "calls", target],
            "class_hierarchy": ["analyze", "tree", target],
            "module_deps": ["analyze", "deps", target],
        }
        args = cmd_map.get(query_type, ["find", "pattern", target])
        result = _run_cgc(args)
        if result.get("success"):
            data = result.get("data", {})
            return {"results": data.get("results", []) if isinstance(data, dict) else []}
        return {"results": [], "error": result.get("error")}

    async def find_dead_code(
        exclude_decorators: Optional[List[str]] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        args = ["find", "dead-code"]
        if exclude_decorators:
            for dec in exclude_decorators:
                args.extend(["--decorator", dec])
        args.extend(["--limit", str(limit)])
        result = _run_cgc(args)
        if result.get("success"):
            data = result.get("data", {})
            return {"results": data.get("results", []) if isinstance(data, dict) else []}
        return {"results": [], "error": result.get("error")}

    async def find_most_complex_functions(limit: int = 10) -> Dict[str, Any]:
        result = _run_cgc(["analyze", "complexity", "--limit", str(limit)])
        if result.get("success"):
            data = result.get("data", {})
            return {"results": data.get("results", []) if isinstance(data, dict) else []}
        return {"results": [], "error": result.get("error")}

    async def calculate_cyclomatic_complexity(
        function_name: str,
        path: Optional[str] = None,
    ) -> Dict[str, Any]:
        args = ["analyze", "complexity", function_name]
        result = _run_cgc(args)
        if result.get("success"):
            data = result.get("data", {})
            return {"results": data.get("results", []) if isinstance(data, dict) else []}
        return {"results": [], "error": result.get("error")}

    async def watch_directory(path: str) -> Dict[str, Any]:
        result = _run_cgc(["watch", path])
        return {"success": result.get("success"), "error": result.get("error")}

    async def add_code_to_graph(path: str, is_dependency: bool = False) -> Dict[str, Any]:
        args = ["index", path]
        if is_dependency:
            args.append("--dependency")
        result = _run_cgc(args)
        return {"success": result.get("success"), "error": result.get("error")}

    async def switch_context(context_path: str) -> Dict[str, Any]:
        result = _run_cgc(["switch", context_path])
        return {"success": result.get("success"), "error": result.get("error")}

    async def discover_codegraph_contexts(
        max_depth: int = 1,
    ) -> List[Dict[str, Any]]:
        result = _run_cgc(["discover", "--max-depth", str(max_depth)])
        if result.get("success"):
            data = result.get("data", [])
            return data if isinstance(data, list) else []
        return []

    async def list_indexed_repositories() -> List[str]:
        result = _run_cgc(["stats"])
        if result.get("success"):
            data = result.get("data", {})
            return data.get("repositories", [])
        return []

    async def load_bundle(bundle_name: str, clear_existing: bool = False) -> Dict[str, Any]:
        args = ["load", bundle_name]
        if clear_existing:
            args.append("--clear")
        result = _run_cgc(args)
        return {"success": result.get("success"), "error": result.get("error")}

    async def search_registry_bundles(query: str) -> List[Dict[str, Any]]:
        result = _run_cgc(["search", "bundles", query])
        if result.get("success"):
            data = result.get("data", [])
            return data if isinstance(data, list) else []
        return []

    async def add_package_to_graph(
        package_name: str,
        language: str,
        is_dependency: bool = True,
    ) -> Dict[str, Any]:
        args = ["add", "package", package_name, "--language", language]
        if is_dependency:
            args.append("--dependency")
        result = _run_cgc(args)
        return {"success": result.get("success"), "error": result.get("error")}

    async def execute_cypher_query(cypher: str) -> Dict[str, Any]:
        result = _run_cgc(["cypher", cypher])
        if result.get("success"):
            return {"results": result.get("data")}
        return {"error": result.get("error")}

    async def visualize_graph_query(cypher: str) -> str:
        result = _run_cgc(["viz", cypher])
        return result.get("data", "") if result.get("success") else ""

if CODEGRAPH_AVAILABLE:
    logger.info("CodeGraphContext available (MCP: %s, CLI: %s)",
               "yes" if CODEGRAPH_FULL_AVAILABLE else "no",
               "yes" if _cgc_available else "no")


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
        method: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not CODEGRAPH_AVAILABLE:
            return {
                "source": "code_graph",
                "query": query,
                "results": [],
                "total": 0,
                "took_ms": 0,
                "error": "CodeGraphContext not available",
            }

        if method:
            return await self._route_to_method(method, query, limit)

        return await self._content_search(query, limit)

    async def _content_search(
        self,
        query: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        start = int(time.time() * 1000)
        result = await find_code(query=query)
        took = int(time.time() * 1000) - start
        return {
            "source": "code_graph",
            "query": query,
            "results": result.get("ranked_results", []),
            "total": result.get("total_matches", 0),
            "took_ms": took,
        }

    async def _route_to_method(
        self,
        method: str,
        query: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        import re

        if method == "find_callers":
            func_name = self._extract_function_name(query)
            return await self.find_callers(func_name, limit)
        elif method == "find_callees":
            func_name = self._extract_function_name(query)
            return await self.find_callees(func_name, limit)
        elif method == "dead_code":
            return await self.find_dead_code(limit)
        elif method == "complexity":
            func_name = self._extract_function_name(query)
            return await self.get_complexity(func_name)
        elif method == "class_hierarchy":
            class_name = self._extract_class_name(query)
            return await self.get_class_hierarchy(class_name, limit)
        elif method == "module_deps":
            module = self._extract_module(query)
            return await self.get_module_deps(module)
        elif method == "call_chain":
            func_name = self._extract_function_name(query)
            return await self.get_call_chain(func_name, limit)
        else:
            return await self._content_search(query, limit)

    def _extract_function_name(self, query: str) -> str:
        import re
        match = re.search(r"(?:of|for|to)\s+(\w+)", query, re.IGNORECASE)
        if match:
            return match.group(1)
        words = query.split()
        for i, w in enumerate(words):
            if w.lower() in ("find", "get", "show", "calls", "callees"):
                if i + 1 < len(words):
                    return words[i + 1]
        return query

    def _extract_class_name(self, query: str) -> str:
        import re
        match = re.search(r"(?:class|parent)\s+(\w+)", query, re.IGNORECASE)
        if match:
            return match.group(1)
        return self._extract_function_name(query)

    def _extract_module(self, query: str) -> str:
        import re
        match = re.search(r"(?:module|import)\s+(\w+)", query, re.IGNORECASE)
        if match:
            return match.group(1)
        return self._extract_function_name(query)

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

    async def watch_directory(self, path: str) -> Dict[str, Any]:
        """Start watching a directory for live code indexing."""
        if not CODEGRAPH_FULL_AVAILABLE:
            return {"source": "code_graph", "action": "watch_directory", "watching": False, "error": "CodeGraphContext not available"}

        start = int(time.time() * 1000)
        result = await watch_directory(path=path)
        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "action": "watch_directory",
            "path": path,
            "watching": result.get("job_id") is not None,
            "job_id": result.get("job_id"),
            "took_ms": took,
        }

    async def add_code_to_graph(self, path: str, is_dependency: bool = False) -> Dict[str, Any]:
        """Add code to graph index."""
        if not CODEGRAPH_FULL_AVAILABLE:
            return {"source": "code_graph", "action": "add_code_to_graph", "indexed": False, "error": "CodeGraphContext not available"}

        start = int(time.time() * 1000)
        result = await add_code_to_graph(path=path, is_dependency=is_dependency)
        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "action": "add_code_to_graph",
            "path": path,
            "indexed": result.get("job_id") is not None,
            "job_id": result.get("job_id"),
            "took_ms": took,
        }

    async def switch_context(self, context_path: str, save: bool = True) -> Dict[str, Any]:
        """Switch to a different repository context."""
        if not CODEGRAPH_FULL_AVAILABLE:
            return {"source": "code_graph", "action": "switch_context", "switched": False, "error": "CodeGraphContext not available"}

        start = int(time.time() * 1000)
        result = await switch_context(context_path=context_path, save=save)
        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "action": "switch_context",
            "path": context_path,
            "switched": result.get("success", False),
            "took_ms": took,
        }

    async def discover_contexts(self, path: str = ".", max_depth: int = 1) -> Dict[str, Any]:
        """Discover indexed code graph contexts in subdirectories."""
        if not CODEGRAPH_FULL_AVAILABLE:
            return {"source": "code_graph", "action": "discover_contexts", "contexts": [], "error": "CodeGraphContext not available"}

        start = int(time.time() * 1000)
        result = await discover_codegraph_contexts(path=path, max_depth=max_depth)
        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "action": "discover_contexts",
            "path": path,
            "contexts": result.get("contexts", []),
            "took_ms": took,
        }

    async def list_repositories(self) -> Dict[str, Any]:
        """List all indexed repositories."""
        if not CODEGRAPH_FULL_AVAILABLE:
            return {"source": "code_graph", "action": "list_repositories", "repositories": [], "error": "CodeGraphContext not available"}

        start = int(time.time() * 1000)
        result = await list_indexed_repositories()
        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "action": "list_repositories",
            "repositories": result.get("repositories", []),
            "took_ms": took,
        }

    async def load_bundle(self, bundle_name: str, clear_existing: bool = False) -> Dict[str, Any]:
        """Load a pre-indexed bundle."""
        if not CODEGRAPH_FULL_AVAILABLE:
            return {"source": "code_graph", "action": "load_bundle", "loaded": False, "error": "CodeGraphContext not available"}

        start = int(time.time() * 1000)
        result = await load_bundle(bundle_name=bundle_name, clear_existing=clear_existing)
        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "action": "load_bundle",
            "bundle": bundle_name,
            "loaded": result.get("success", False),
            "took_ms": took,
        }

    async def search_registry_bundles(self, query: str = "", unique_only: bool = True) -> Dict[str, Any]:
        """Search available bundles in the registry."""
        if not CODEGRAPH_FULL_AVAILABLE:
            return {"source": "code_graph", "action": "search_bundles", "bundles": [], "error": "CodeGraphContext not available"}

        start = int(time.time() * 1000)
        result = await search_registry_bundles(query=query, unique_only=unique_only)
        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "action": "search_bundles",
            "query": query,
            "bundles": result.get("bundles", []),
            "took_ms": took,
        }

    async def add_package_to_graph(self, package_name: str, language: str = "python") -> Dict[str, Any]:
        """Add a package to the graph."""
        if not CODEGRAPH_FULL_AVAILABLE:
            return {"source": "code_graph", "action": "add_package", "added": False, "error": "CodeGraphContext not available"}

        start = int(time.time() * 1000)
        result = await add_package_to_graph(package_name=package_name, language=language)
        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "action": "add_package",
            "package": package_name,
            "language": language,
            "added": result.get("job_id") is not None,
            "job_id": result.get("job_id"),
            "took_ms": took,
        }

    async def execute_cypher(self, cypher_query: str) -> Dict[str, Any]:
        """Execute raw Cypher query against the code graph."""
        if not CODEGRAPH_FULL_AVAILABLE:
            return {"source": "code_graph", "action": "execute_cypher", "results": [], "error": "CodeGraphContext not available"}

        dangerous = ["DELETE", "DROP", "ALTER", "CREATE", "SET", "REMOVE"]
        if any(p in cypher_query.upper() for p in dangerous):
            return {"source": "code_graph", "action": "execute_cypher", "results": [], "error": "Query contains dangerous operations"}

        start = int(time.time() * 1000)
        result = await execute_cypher_query(cypher_query=cypher_query)
        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "action": "execute_cypher",
            "query": cypher_query,
            "results": result.get("results", []),
            "took_ms": took,
        }

    async def visualize(self, cypher_query: str) -> Dict[str, Any]:
        """Generate Mermaid diagram from Cypher query."""
        if not CODEGRAPH_FULL_AVAILABLE:
            return {"source": "code_graph", "action": "visualize", "url": None, "error": "CodeGraphContext not available"}

        dangerous = ["DELETE", "DROP", "ALTER", "CREATE", "SET", "REMOVE", "FOREACH", "MERGE", "CALL"]
        upper = cypher_query.upper()
        if any(p in upper for p in dangerous):
            return {"source": "code_graph", "action": "visualize", "query": cypher_query, "url": None, "error": "Query contains write operations"}
        
        if "MATCH" not in upper and "RETURN" not in upper:
            return {"source": "code_graph", "action": "visualize", "query": cypher_query, "url": None, "error": "Only MATCH/RETURN queries allowed"}

        start = int(time.time() * 1000)
        result = await visualize_graph_query(cypher_query=cypher_query)
        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "action": "visualize",
            "query": cypher_query,
            "url": result.get("url"),
            "mermaid": result.get("mermaid"),
            "took_ms": took,
        }

    async def get_module_deps(self, module_name: str) -> Dict[str, Any]:
        """Get module dependencies for a given module."""
        if not CODEGRAPH_AVAILABLE:
            return {"source": "code_graph", "query": f"module_deps:{module_name}", "dependencies": [], "error": "CodeGraphContext not available"}

        start = int(time.time() * 1000)
        result = await analyze_code_relationships(
            query_type=CodeGraphQueryType.MODULE_DEPS.value,
            target=module_name,
            context=self.repo_path,
        )
        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "query": f"module_deps:{module_name}",
            "dependencies": result.get("results", []),
            "took_ms": took,
        }

    async def get_call_chain(self, function_name: str) -> Dict[str, Any]:
        """Get full call chain for a function."""
        if not CODEGRAPH_AVAILABLE:
            return {"source": "code_graph", "query": f"call_chain:{function_name}", "chain": [], "error": "CodeGraphContext not available"}

        start = int(time.time() * 1000)
        result = await analyze_code_relationships(
            query_type=CodeGraphQueryType.CALL_CHAIN.value,
            target=function_name,
            context=self.repo_path,
        )
        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "query": f"call_chain:{function_name}",
            "chain": result.get("results", []),
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
            CodeGraphQueryType.MODULE_DEPS.value: self.get_module_deps,
            CodeGraphQueryType.CALL_CHAIN.value: self.get_call_chain,
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
