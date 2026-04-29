"""
CodeGraph Retriever - Code-specific graph queries via CodeGraphContext.

CodeGraphContext CLI integration (v0.4+):
- cgc find pattern <query> - Find code elements
- cgc analyze callers <target> - Find function callers
- cgc analyze calls <target> - Find callees
- cgc find dead-code - Find unused functions
- cgc find complex - Find complex functions

Ingestion support (via CLI):
- git repositories (with branch/tag support)
- ZIP archives (downloaded or uploaded)
- Markdown/Confluence content
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiohttp
import httpx

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

# Check for CLI availability
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

# Log availability status
if _cgc_available:
    logger.info("CodeGraphContext CLI available")
    try:
        version = subprocess.run(
            ["cgc", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        logger.info(f"CodeGraphContext version: {version}")
    except Exception:
        pass
else:
    logger.info("CodeGraphContext CLI not installed (optional)")

CODEGRAPH_AVAILABLE = _cgc_available
CODEGRAPH_FULL_AVAILABLE = _cgc_available


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
    if not _cgc_available:
        return {"results": [], "error": "CodeGraphContext CLI not installed"}
    result = await _cgc_find_pattern(query)
    if result.get("success"):
        data = result.get("results", [])
        return {"results": data[:limit], "total": len(data)}
    return {"results": [], "error": result.get("error")}


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
    if not _cgc_available:
        return {"results": [], "error": "CodeGraphContext CLI not installed"}
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
    if not _cgc_available:
        return {"results": [], "error": "CodeGraphContext CLI not installed"}
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


# Ingestion methods for API endpoints


async def index_git_repository(
    url: str,
    branch: str = "main",
    depth: int = 1,
) -> Dict[str, Any]:
    """Index a git repository by URL with optional branch."""
    if not _cgc_available:
        return {"success": False, "error": "CodeGraphContext CLI not installed"}
    
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            subprocess.run(
                ["git", "clone", "--branch", branch, "--depth", str(depth), url, tmpdir],
                capture_output=True,
                timeout=120,
                check=True,
            )
            result = await add_code_to_graph(tmpdir)
            return {
                "success": result.get("success", False),
                "repo_url": url,
                "branch": branch,
                "error": result.get("error"),
            }
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": f"Git clone failed: {e.stderr}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


async def index_zip_archive(
    content: bytes,
    filename: str = "archive.zip",
) -> Dict[str, Any]:
    """Index a ZIP archive (uploaded or downloaded)."""
    if not _cgc_available:
        return {"success": False, "error": "CodeGraphContext CLI not installed"}
    
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / filename
        zip_path.write_bytes(content)
        
        import zipfile
        extract_dir = Path(tmpdir) / "extracted"
        extract_dir.mkdir()
        
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)
            
            result = await add_code_to_graph(str(extract_dir))
            return {
                "success": result.get("success", False),
                "files": len(list(extract_dir.rglob("*"))),
                "error": result.get("error"),
            }
        except zipfile.BadZipFile:
            return {"success": False, "error": "Invalid ZIP file"}
        except Exception as e:
            return {"success": False, "error": str(e)}


async def index_from_url(
    url: str,
    url_type: str = "zip",
) -> Dict[str, Any]:
    """Download and index from URL (ZIP, raw, etc.)."""
    if not _cgc_available:
        return {"success": False, "error": "CodeGraphContext CLI not installed"}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return {"success": False, "error": f"Download failed: {response.status}"}
                
                content = await response.read()
                
                if url_type == "zip" or url.endswith(".zip"):
                    return await index_zip_archive(content, Path(url).name)
                elif url_type == "markdown" or url.endswith((".md", ".markdown")):
                    return await index_markdown_content(content.decode("utf-8"))
                else:
                    return {"success": False, "error": f"Unsupported URL type: {url_type}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


async def index_markdown_content(
    content: str,
    source_name: str = "document.md",
) -> Dict[str, Any]:
    """Index markdown document content."""
    if not _cgc_available:
        return {"success": False, "error": "CodeGraphContext CLI not installed"}
    
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / source_name
        doc_path.write_text(content, encoding="utf-8")
        
        result = await add_code_to_graph(tmpdir)
        return {
            "success": result.get("success", False),
            "source": source_name,
            "chars": len(content),
            "error": result.get("error"),
        }


async def index_confluence_page(
    base_url: str,
    page_id: str,
    api_token: str,
    email: str,
) -> Dict[str, Any]:
    """Index Confluence page content via REST API."""
    if not _cgc_available:
        return {"success": False, "error": "CodeGraphContext CLI not installed"}
    
    auth = aiohttp.BasicAuth(email, api_token)
    url = f"{base_url.rstrip('/')}/rest/api/content/{page_id}?expand=body.storage"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, auth=auth) as response:
                if response.status != 200:
                    return {"success": False, "error": f"Confluence API: {response.status}"}
                
                data = await response.json()
                content_html = data.get("body", {}).get("storage", {}).get("value", "")
                
                content = _html_to_markdown(content_html)
                
                entities_indexed = 0
                relationships_indexed = 0
                
                plantuml_blocks = _extract_plantuml_blocks(content)
                for block in plantuml_blocks:
                    try:
                        from documents.diagram_formats import PlantUMLParser
                        result = PlantUMLParser().parse(block)
                        if result.entities:
                            for entity in result.entities:
                                entity_result = await index_markdown_content(
                                    f"ENTITY: {entity.get('name', '')}\n"
                                    f"TYPE: {entity.get('type', 'node')}\n"
                                    f"SOURCE: confluence_{page_id}_plantuml\n"
                                    f"DIAGRAM_TYPE: plantuml_{result.diagram_type}",
                                    f"confluence_{page_id}_entity_{entities_indexed}.md"
                                )
                                if entity_result.get("success"):
                                    entities_indexed += 1
                        if result.relationships:
                            relationships_indexed += len(result.relationships)
                    except Exception:
                        pass
                
                drawio_blocks = _extract_drawio_blocks(content_html)
                for block in drawio_blocks:
                    try:
                        from documents.diagram_formats import DrawIOParser
                        result = DrawIOParser().parse(block)
                        if result.nodes:
                            for node in result.nodes:
                                node_result = await index_markdown_content(
                                    f"ENTITY: {node.get('id', node.get('label', ''))}\n"
                                    f"TYPE: node\n"
                                    f"LABEL: {node.get('label', '')}\n"
                                    f"SOURCE: confluence_{page_id}_drawio",
                                    f"confluence_{page_id}_drawio_{entities_indexed}.md"
                                )
                                if node_result.get("success"):
                                    entities_indexed += 1
                        if result.edges:
                            for edge in result.edges:
                                rel_result = await index_markdown_content(
                                    f"RELATIONSHIP: {edge.get('source', '')} -> {edge.get('target', '')}\n"
                                    f"TYPE: {edge.get('style', 'arrow')}\n"
                                    f"SOURCE: confluence_{page_id}_drawio",
                                    f"confluence_{page_id}_rel_{relationships_indexed}.md"
                                )
                                if rel_result.get("success"):
                                    relationships_indexed += 1
                    except Exception:
                        pass
                
                md_result = await index_markdown_content(content, f"confluence_{page_id}.md")
                
                return {
                    "success": md_result.get("success", False),
                    "page_id": page_id,
                    "content_indexed": md_result.get("success", False),
                    "diagram_entities_indexed": entities_indexed,
                    "diagram_relationships_indexed": relationships_indexed,
                    "plantuml_blocks_found": len(plantuml_blocks),
                    "drawio_blocks_found": len(drawio_blocks),
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


def _html_to_markdown(html: str) -> str:
    """Basic HTML to Markdown conversion."""
    import re
    
    md = html
    md = re.sub(r"<h1[^>]*>(.*?)</h1>", r"# \1\n", md, flags=re.DOTALL)
    md = re.sub(r"<h2[^>]*>(.*?)</h2>", r"## \1\n", md, flags=re.DOTALL)
    md = re.sub(r"<h3[^>]*>(.*?)</h3>", r"### \1\n", md, flags=re.DOTALL)
    md = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n\n", md, flags=re.DOTALL)
    md = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", md, flags=re.DOTALL)
    md = re.sub(r"<pre[^>]*>(.*?)</pre>", r"```\n\1```", md, flags=re.DOTALL)
    md = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", md, flags=re.DOTALL)
    md = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", md, flags=re.DOTALL)
    md = re.sub(r"<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", r"[\2](\1)", md, flags=re.DOTALL)
    md = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", md, flags=re.DOTALL)
    md = re.sub(r"<br\s*/?>", r"\n", md, flags=re.DOTALL)
    md = re.sub(r"<!--.*?-->", "", md, flags=re.DOTALL)
    md = re.sub(r"<[^>]+>", "", md)
    
    return md.strip()


def _extract_plantuml_blocks(md: str) -> List[str]:
    """Extract PlantUML code blocks from markdown content."""
    import re
    blocks = []
    
    pattern = r"```plantuml\n(.*?)```"
    matches = re.findall(pattern, md, re.DOTALL)
    blocks.extend(matches)
    
    pattern = r"@startuml(.*?)@enduml"
    matches = re.findall(pattern, md, re.DOTALL)
    blocks.extend(matches)
    
    return blocks


def _extract_drawio_blocks(html: str) -> List[str]:
    """Extract draw.io XML from Confluence HTML."""
    import re
    blocks = []
    
    pattern = r'<ac:structured-macro ac:name="diagram"[^>]*>.*?<ac:parameter ac:name="xml">(.*?)</ac:parameter>'
    matches = re.findall(pattern, html, re.DOTALL)
    for xml in matches:
        if "mxfile" in xml or "diagram" in xml:
            blocks.append(xml)
    
    pattern = r'<div[^>]*data-model[^>]*>(.*?)</div>'
    matches = re.findall(pattern, html, re.DOTALL)
    for xml in matches:
        if "<diagram" in xml or "<mxfile" in xml:
            blocks.append(xml)
    
    pattern = r'<mxfile[^>]*>(.*?)</mxfile>'
    matches = re.findall(pattern, html, re.DOTALL)
    blocks.extend(matches)
    
    return blocks

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
                "error": "CodeGraphContext CLI not installed",
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
                "error": "CodeGraphContext CLI not installed",
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
                "error": "CodeGraphContext CLI not installed",
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
                "error": "CodeGraphContext CLI not installed",
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
                "error": "CodeGraphContext CLI not installed",
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
                "error": "CodeGraphContext CLI not installed",
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
                "error": "CodeGraphContext CLI not installed",
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
                "error": "CodeGraphContext CLI not installed",
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
                "error": "CodeGraphContext CLI not installed",
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
                "error": "CodeGraphContext CLI not installed",
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
                "error": "CodeGraphContext CLI not installed",
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
            return {"source": "code_graph", "action": "watch_directory", "watching": False, "error": "CodeGraphContext CLI not installed"}

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
            return {"source": "code_graph", "action": "add_code_to_graph", "indexed": False, "error": "CodeGraphContext CLI not installed"}

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
            return {"source": "code_graph", "action": "switch_context", "switched": False, "error": "CodeGraphContext CLI not installed"}

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
            return {"source": "code_graph", "action": "discover_contexts", "contexts": [], "error": "CodeGraphContext CLI not installed"}

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
            return {"source": "code_graph", "action": "list_repositories", "repositories": [], "error": "CodeGraphContext CLI not installed"}

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
            return {"source": "code_graph", "action": "load_bundle", "loaded": False, "error": "CodeGraphContext CLI not installed"}

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
            return {"source": "code_graph", "action": "search_bundles", "bundles": [], "error": "CodeGraphContext CLI not installed"}

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
            return {"source": "code_graph", "action": "add_package", "added": False, "error": "CodeGraphContext CLI not installed"}

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
            return {"source": "code_graph", "action": "execute_cypher", "results": [], "error": "CodeGraphContext CLI not installed"}

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
            return {"source": "code_graph", "action": "visualize", "url": None, "error": "CodeGraphContext CLI not installed"}

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
            return {"source": "code_graph", "query": f"module_deps:{module_name}", "dependencies": [], "error": "CodeGraphContext CLI not installed"}

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
            return {"source": "code_graph", "query": f"call_chain:{function_name}", "chain": [], "error": "CodeGraphContext CLI not installed"}

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
