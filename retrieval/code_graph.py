"""
CodeGraph Retriever - Code-specific graph queries via CodeGraphContext MCP.

Architecture:
- MCP client via persistent subprocess using JSON-RPC 2.0 protocol
- Falls back to CLI spawn if MCP unavailable
- Connection pooling for parallel queries

MCP Tools: find_code, analyze_code_relationships, find_dead_code,
calculate_cyclomatic_complexity, execute_cypher_query, visualize_graph_query
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import tempfile
import time
from enum import StrEnum
from pathlib import Path
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

CGC_COMMAND = os.environ.get("CGC_COMMAND", "codegraphcontext")
CGC_POOL_SIZE = int(os.environ.get("CGC_POOL_SIZE", "3"))
CGC_TIMEOUT = float(os.environ.get("CGC_TIMEOUT", "30.0"))


def _check_cgc_available() -> bool:
    try:
        result = subprocess.run(
            [CGC_COMMAND, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


_cgc_available: bool | None = None


def _is_cgc_available() -> bool:
    global _cgc_available
    if _cgc_available is None:
        _cgc_available = _check_cgc_available()
    return _cgc_available


CODEGRAPH_AVAILABLE = False
CODEGRAPH_FULL_AVAILABLE = False


# =============================================================================
# MCP Client Implementation
# =============================================================================

_CGC_ARG_RE = re.compile(r"^[A-Za-z0-9._\-/]+$")


async def _mcp_execute(method: str, params: dict | None = None) -> dict[str, Any]:
    """Execute via CLI - MCP stdin/stdout not fully async-compatible in cgc v0.4."""
    cli_args = _MCP_TO_CLI.get(method, [])
    if params:
        cli_args.extend(_params_to_cli_args(method, params))
    return await _cli_execute(cli_args)


async def _cli_execute(args: list[str]) -> dict[str, Any]:
    """Execute CLI command as fallback with concurrency control."""
    loop = asyncio.get_event_loop()
    async with _cli_semaphore:
        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    [CGC_COMMAND, *args],
                    capture_output=True,
                    text=True,
                    timeout=CGC_TIMEOUT,
                )
            )
            if result.returncode == 0:
                try:
                    return {"success": True, "data": json.loads(result.stdout)}
                except json.JSONDecodeError:
                    lines = result.stdout.strip().split("\n")
                    matches = []
                    for line in lines:
                        if "│" in line and "─" not in line:
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


_cli_semaphore: asyncio.Semaphore = asyncio.Semaphore(CGC_POOL_SIZE)


# MCP method to CLI args mapping
_MCP_TO_CLI = {
    "find_code": ["find", "pattern"],
    "analyze_code_relationships": ["analyze", "callers"],
    "find_dead_code": ["find", "dead-code"],
    "calculate_cyclomatic_complexity": ["analyze", "complex"],
    "find_most_complex_functions": ["analyze", "complexity"],
    "add_code_to_graph": ["index"],
    "switch_context": ["switch"],
    "discover_codegraph_contexts": ["discover"],
    "list_indexed_repositories": ["stats"],
    "load_bundle": ["load"],
    "search_registry_bundles": ["search", "bundles"],
    "watch_directory": ["watch"],
    "unwatch_directory": ["unwatch"],
    "add_package_to_graph": ["add", "package"],
    "get_repository_stats": ["stats"],
    "execute_cypher_query": ["cypher"],
    "visualize_graph_query": ["visualize"],
}


def _params_to_cli_args(method: str, params: dict[str, Any]) -> list[str]:
    args = []
    if method == "find_code":
        args.append(params.get("query", ""))
    elif method == "analyze_code_relationships":
        args.append(params.get("query_type", ""))
        args.append(params.get("target", ""))
    elif method == "find_dead_code":
        if exclude := params.get("exclude_decorated_with"):
            for e in exclude:
                args.extend(["--decorator", e])
    elif method == "calculate_cyclomatic_complexity":
        args.append(params.get("function_name", ""))
    elif method == "find_most_complex_functions":
        args.append("--limit")
        args.append(str(params.get("limit", 10)))
    elif method == "add_code_to_graph":
        args.append(params.get("path", ""))
        if params.get("is_dependency"):
            args.append("--dependency")
    elif method == "switch_context":
        args.append(params.get("context_path", ""))
    elif method == "discover_codegraph_contexts":
        if params.get("max_depth"):
            args.extend(["--max-depth", str(params["max_depth"])])
    elif method == "load_bundle":
        args.append(params.get("bundle_name", ""))
        if params.get("clear_existing"):
            args.append("--clear")
    elif method == "search_registry_bundles":
        args.extend([params.get("query", ""), "--unique"] if params.get("unique_only") else [params.get("query", "")])
    elif method == "execute_cypher_query":
        args.append(params.get("cypher_query", ""))
    elif method == "visualize_graph_query":
        args.append("--visual")
        args.append(params.get("cypher_query", ""))
    elif method == "add_package_to_graph":
        args.append(params.get("package_name", ""))
        args.append("--language")
        args.append(params.get("language", "python"))
    return args
_CLI_TO_MCP = {
    ("find", "pattern"): "find_code",
    ("analyze", "callers"): "analyze_code_relationships",
    ("analyze", "calls"): "analyze_code_relationships",
    ("analyze", "tree"): "analyze_code_relationships",
    ("analyze", "deps"): "analyze_code_relationships",
    ("find", "dead-code"): "find_dead_code",
    ("analyze", "complexity"): "find_most_complex_functions",
    ("analyze", "complex"): "calculate_cyclomatic_complexity",
    ("index",): "add_code_to_graph",
    ("switch",): "switch_context",
    ("discover",): "discover_codegraph_contexts",
    ("stats",): "list_indexed_repositories",
}


def _build_params(args: list[str]) -> dict[str, Any]:
    """Build MCP params from CLI args."""
    params = {}
    i = 0
    while i < len(args):
        if args[i] == "--limit" and i + 1 < len(args):
            params["limit"] = int(args[i + 1])
            i += 2
        elif args[i] == "--decorator" and i + 1 < len(args):
            params.setdefault("exclude_decorated_with", []).append(args[i + 1])
            i += 2
        elif args[i] == "--dependency":
            params["is_dependency"] = True
            i += 1
        elif args[i] == "--language" and i + 1 < len(args):
            params["language"] = args[i + 1]
            i += 2
        elif args[i] == "--save" and args[i + 1] == "false":
            params["save"] = False
            i += 2
        elif args[i] == "--max-depth" and i + 1 < len(args):
            params["max_depth"] = int(args[i + 1])
            i += 2
        else:
            if "query" not in params:
                params["query"] = args[i]
            elif "target" not in params:
                params["target"] = args[i]
            elif "query_type" not in params:
                params["query_type"] = args[i]
            i += 1
    return params


def _validate_cgc_arg(arg: str) -> str:
    """Validate a cgc CLI argument contains only safe characters.

    Only allows alphanumeric, dots, dashes, underscores, and forward slashes.
    Prevents shell injection via user-controlled strings.

    Args:
        arg: The argument to validate.

    Returns:
        The validated argument string.

    Raises:
        ValueError: If the argument contains disallowed characters.
    """
    if not arg:
        raise ValueError("cgc argument cannot be empty")
    if not _CGC_ARG_RE.match(arg):
        raise ValueError(
            f"Invalid cgc argument '{arg}': must contain only alphanumeric chars, "
            f"dots, dashes, underscores, and forward slashes"
        )
    return arg


def _run_cgc(args: list[str], timeout: int = 30) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["cgc", *args],
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


async def _run_cgc_async(args: list[str], timeout: int = 30) -> dict[str, Any]:
    """Try MCP first, fallback to CLI spawn."""
    if _is_cgc_available():
        method = _CLI_TO_MCP.get(tuple(args[:2]))
        if method:
            params = _build_params(args[2:])
            result = await _mcp_execute(method, params)
            if "error" not in result:
                return {"success": True, "data": result}
    return await _cli_execute(args)


async def find_code(query: str, limit: int = 10) -> dict[str, Any]:
    if not _is_cgc_available():
        return {"results": [], "error": "CodeGraphContext CLI not installed"}
    result = await _cgc_find_pattern(query)
    if result.get("success"):
        data = result.get("results", [])
        return {"results": data[:limit], "total": len(data)}
    return {"results": [], "error": result.get("error")}


async def _cgc_find_pattern(pattern: str) -> dict[str, Any]:
    """Call cgc find pattern and parse results."""
    _validate_cgc_arg(pattern)
    result = await _run_cgc_async(["find", "pattern", pattern])
    if not result.get("success"):
        return {"success": False, "results": []}
    output = result.get("data", {})
    # If data is already a list of matches, return it
    if isinstance(output, list):
        return {"success": True, "results": output}
    # Otherwise return the parsed data
    data = result.get("data", {})
    if isinstance(data, list):
        return {"success": True, "results": data}
    return {"success": True, "results": []}


async def analyze_code_relationships(
    query_type: str,
    target: str,
    context: str | None = None,
) -> dict[str, Any]:
    if not _is_cgc_available():
        return {"results": [], "error": "CodeGraphContext CLI not installed"}
    _validate_cgc_arg(target)
    cmd_map = {
        "find_callers": ["analyze", "callers", target],
        "find_callees": ["analyze", "calls", target],
        "class_hierarchy": ["analyze", "tree", target],
        "module_deps": ["analyze", "deps", target],
    }
    args = cmd_map.get(query_type, ["find", "pattern", target])
    result = await _run_cgc_async(args)
    if result.get("success"):
        data = result.get("data", {})
        return {"results": data.get("results", []) if isinstance(data, dict) else []}
    return {"results": [], "error": result.get("error")}


async def find_dead_code(
    exclude_decorators: list[str] | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    if not _is_cgc_available():
        return {"results": [], "error": "CodeGraphContext CLI not installed"}
    args = ["find", "dead-code"]
    if exclude_decorators:
        for dec in exclude_decorators:
            _validate_cgc_arg(dec)
            args.extend(["--decorator", dec])
    args.extend(["--limit", str(limit)])
    result = await _run_cgc_async(args)
    if result.get("success"):
        data = result.get("data", {})
        return {"results": data.get("results", []) if isinstance(data, dict) else []}
    return {"results": [], "error": result.get("error")}


async def find_most_complex_functions(limit: int = 10) -> dict[str, Any]:
    result = await _run_cgc_async(["analyze", "complexity", "--limit", str(limit)])
    if result.get("success"):
        data = result.get("data", {})
        return {"results": data.get("results", []) if isinstance(data, dict) else []}
    return {"results": [], "error": result.get("error")}


async def calculate_cyclomatic_complexity(
    function_name: str,
    path: str | None = None,
) -> dict[str, Any]:
    _validate_cgc_arg(function_name)
    args = ["analyze", "complexity", function_name]
    result = await _run_cgc_async(args)
    if result.get("success"):
        data = result.get("data", {})
        return {"results": data.get("results", []) if isinstance(data, dict) else []}
    return {"results": [], "error": result.get("error")}


async def watch_directory(path: str) -> dict[str, Any]:
    _validate_cgc_arg(path)
    result = await _cli_execute(["watch", path])
    return {"success": result.get("success"), "error": result.get("error")}


async def execute_cypher_query(cypher_query: str) -> dict[str, Any]:
    """Execute a read-only Cypher query against the code graph."""
    if not _is_cgc_available():
        return {"results": [], "error": "CodeGraphContext CLI not installed"}
    result = await _cli_execute(["cypher", cypher_query])
    if result.get("success"):
        data = result.get("data", {})
        return {"results": data.get("results", []) if isinstance(data, dict) else []}
    return {"results": [], "error": result.get("error")}


async def visualize_graph_query(cypher_query: str) -> dict[str, Any]:
    """Generate visualization URL from Cypher query."""
    if not _is_cgc_available():
        return {"url": None, "mermaid": None, "error": "CodeGraphContext CLI not installed"}
    result = await _cli_execute(["visualize", cypher_query])
    if result.get("success"):
        data = result.get("data", {})
        url = data.get("url") if isinstance(data, dict) else None
        mermaid = data.get("mermaid") if isinstance(data, dict) else None
        return {"url": url, "mermaid": mermaid}
    return {"url": None, "mermaid": None, "error": result.get("error")}


async def add_code_to_graph(path: str, is_dependency: bool = False) -> dict[str, Any]:
    _validate_cgc_arg(path)
    args = ["index", path]
    if is_dependency:
        args.append("--dependency")
    result = await _run_cgc_async(args)
    return {"success": result.get("success"), "error": result.get("error")}


# Ingestion methods for API endpoints


async def index_git_repository(
    url: str,
    branch: str = "main",
    depth: int = 1,
) -> dict[str, Any]:
    """Index a git repository by URL with optional branch."""
    if not _is_cgc_available():
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
) -> dict[str, Any]:
    """Index a ZIP archive (uploaded or downloaded)."""
    if not _is_cgc_available():
        return {"success": False, "error": "CodeGraphContext CLI not installed"}

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / filename
        zip_path.write_bytes(content)

        import zipfile
        extract_dir = Path(tmpdir) / "extracted"
        extract_dir.mkdir()

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # SECURITY: Validate each member path to prevent zip-slip attacks.
                # Reject absolute paths, paths with ".." components, or paths
                # that would escape the extract directory.
                extract_dir_resolved = extract_dir.resolve()
                for member in zf.infolist():
                    member_path = (extract_dir / member.filename).resolve()
                    if not str(member_path).startswith(str(extract_dir_resolved)):
                        logger.warning(
                            "Skipping zip member '%s': path escapes target directory",
                            member.filename,
                        )
                        continue
                    # Also skip absolute paths and paths with '..' components
                    if member.filename.startswith("/") or ".." in Path(member.filename).parts:
                        logger.warning(
                            "Skipping zip member '%s': absolute path or '..' component",
                            member.filename,
                        )
                        continue
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
) -> dict[str, Any]:
    """Download and index from URL (ZIP, raw, etc.)."""
    if not _is_cgc_available():
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
) -> dict[str, Any]:
    """Index markdown document content."""
    if not _is_cgc_available():
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
) -> dict[str, Any]:
    """Index Confluence page content via REST API."""
    if not _is_cgc_available():
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
                        for elem in result.elements:
                            node_result = await index_markdown_content(
                                f"ENTITY: {elem.element_id}\n"
                                f"TYPE: node\n"
                                f"LABEL: {elem.value}\n"
                                f"SOURCE: confluence_{page_id}_drawio",
                                f"confluence_{page_id}_drawio_{entities_indexed}.md"
                            )
                            if node_result.get("success"):
                                entities_indexed += 1
                        for conn in result.connections:
                            src = conn.get("source", "") if isinstance(conn, dict) else ""
                            tgt = conn.get("target", "") if isinstance(conn, dict) else ""
                            rel_result = await index_markdown_content(
                                f"RELATIONSHIP: {src} -> {tgt}\n"
                                f"TYPE: arrow\n"
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


def _extract_plantuml_blocks(md: str) -> list[str]:
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


def _extract_drawio_blocks(html: str) -> list[str]:
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


async def switch_context(context_path: str) -> dict[str, Any]:
    _validate_cgc_arg(context_path)
    result = await _run_cgc_async(["switch", context_path])
    return {"success": result.get("success"), "error": result.get("error")}


async def discover_codegraph_contexts(
    max_depth: int = 1,
) -> list[dict[str, Any]]:
    result = await _run_cgc_async(["discover", "--max-depth", str(max_depth)])
    if result.get("success"):
        data = result.get("data", [])
        return data if isinstance(data, list) else []
    return []


async def list_indexed_repositories() -> list[str]:
    result = await _run_cgc_async(["stats"])
    if result.get("success"):
        data = result.get("data", {})
        return data.get("repositories", [])
    return []


async def load_bundle(bundle_name: str, clear_existing: bool = False) -> dict[str, Any]:
    _validate_cgc_arg(bundle_name)
    args = ["load", bundle_name]
    if clear_existing:
        args.append("--clear")
    result = await _run_cgc_async(args)
    return {"success": result.get("success"), "error": result.get("error")}


async def search_registry_bundles(query: str) -> list[dict[str, Any]]:
    _validate_cgc_arg(query)
    result = await _run_cgc_async(["search", "bundles", query])
    if result.get("success"):
        data = result.get("data", [])
        return data if isinstance(data, list) else []
    return []


async def add_package_to_graph(
    package_name: str,
    language: str,
    is_dependency: bool = True,
) -> dict[str, Any]:
    _validate_cgc_arg(package_name)
    _validate_cgc_arg(language)
    args = ["add", "package", package_name, "--language", language]
    if is_dependency:
        args.append("--dependency")
    result = await _run_cgc_async(args)
    return {"success": result.get("success"), "error": result.get("error")}


class CodeGraphQueryType(StrEnum):
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

    def __init__(self, repo_path: str | None = None):
        self.repo_path = repo_path

    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
        method: str | None = None,
    ) -> dict[str, Any]:
        if not _is_cgc_available():
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
    ) -> dict[str, Any]:
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
    ) -> dict[str, Any]:

        if method == "find_callers":
            func_name = self._extract_function_name(query)
            return await self.find_callers(func_name, limit)
        elif method == "find_callees":
            func_name = self._extract_function_name(query)
            return await self.find_callees(func_name, limit)
        elif method == "dead_code":
            return await find_dead_code(limit=limit)
        elif method == "complexity":
            func_name = self._extract_function_name(query)
            return await self.get_complexity(func_name)
        elif method == "class_hierarchy":
            class_name = self._extract_class_name(query)
            return await self.get_class_hierarchy(class_name)
        elif method == "module_deps":
            module = self._extract_module(query)
            return await self.get_module_deps(module)
        elif method == "call_chain":
            func_name = self._extract_function_name(query)
            return await self.get_call_chain(func_name)
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
    ) -> dict[str, Any]:
        """Find functions that call the given function."""
        if not _is_cgc_available():
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
    ) -> dict[str, Any]:
        """Find functions called by the given function."""
        if not _is_cgc_available():
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
    ) -> dict[str, Any]:
        """Find all callers (transitive) of the given function."""
        if not _is_cgc_available():
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
    ) -> dict[str, Any]:
        """Find all callees (transitive) of the given function."""
        if not _is_cgc_available():
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
    ) -> dict[str, Any]:
        """Find files that import the given module."""
        if not _is_cgc_available():
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
    ) -> dict[str, Any]:
        """Get class hierarchy (parent classes)."""
        if not _is_cgc_available():
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
    ) -> dict[str, Any]:
        """Find methods that override the given method."""
        if not _is_cgc_available():
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
        exclude_decorated_with: list[str] | None = None,
    ) -> dict[str, Any]:
        """Find potentially unused functions."""
        if not _is_cgc_available():
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
            exclude_decorators=exclude_decorated_with,
            limit=20,
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
    ) -> dict[str, Any]:
        """Get most complex functions by cyclomatic complexity."""
        if not _is_cgc_available():
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
        path: str | None = None,
    ) -> dict[str, Any]:
        """Get cyclomatic complexity of a specific function."""
        if not _is_cgc_available():
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

    async def watch_directory(self, path: str) -> dict[str, Any]:
        """Start watching a directory for live code indexing."""
        if not _is_cgc_available():
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

    async def add_code_to_graph(self, path: str, is_dependency: bool = False) -> dict[str, Any]:
        """Add code to graph index."""
        if not _is_cgc_available():
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

    async def switch_context(self, context_path: str, save: bool = True) -> dict[str, Any]:
        """Switch to a different repository context."""
        if not _is_cgc_available():
            return {"source": "code_graph", "action": "switch_context", "switched": False, "error": "CodeGraphContext CLI not installed"}

        start = int(time.time() * 1000)
        result = await switch_context(context_path)
        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "action": "switch_context",
            "path": context_path,
            "switched": result.get("success", False),
            "took_ms": took,
        }

    async def discover_contexts(self, path: str = ".", max_depth: int = 1) -> dict[str, Any]:
        """Discover indexed code graph contexts in subdirectories."""
        if not _is_cgc_available():
            return {"source": "code_graph", "action": "discover_contexts", "contexts": [], "error": "CodeGraphContext CLI not installed"}

        start = int(time.time() * 1000)
        result = await discover_codegraph_contexts(max_depth=max_depth)
        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "action": "discover_contexts",
            "path": path,
            "contexts": result,
            "took_ms": took,
        }

    async def list_repositories(self) -> dict[str, Any]:
        """List all indexed repositories."""
        if not _is_cgc_available():
            return {"source": "code_graph", "action": "list_repositories", "repositories": [], "error": "CodeGraphContext CLI not installed"}

        start = int(time.time() * 1000)
        result = await list_indexed_repositories()
        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "action": "list_repositories",
            "repositories": result,
            "took_ms": took,
        }

    async def load_bundle(self, bundle_name: str, clear_existing: bool = False) -> dict[str, Any]:
        """Load a pre-indexed bundle."""
        if not _is_cgc_available():
            return {"source": "code_graph", "action": "load_bundle", "loaded": False, "error": "CodeGraphContext CLI not installed"}

        start = int(time.time() * 1000)
        result = await load_bundle(bundle_name, clear_existing)
        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "action": "load_bundle",
            "bundle": bundle_name,
            "loaded": result.get("success", False),
            "took_ms": took,
        }

    async def search_registry_bundles(self, query: str = "", unique_only: bool = True) -> dict[str, Any]:
        """Search available bundles in the registry."""
        if not _is_cgc_available():
            return {"source": "code_graph", "action": "search_bundles", "bundles": [], "error": "CodeGraphContext CLI not installed"}

        start = int(time.time() * 1000)
        result = await search_registry_bundles(query)
        took = int(time.time() * 1000) - start

        return {
            "source": "code_graph",
            "action": "search_bundles",
            "query": query,
            "bundles": result,
            "took_ms": took,
        }

    async def add_package_to_graph(self, package_name: str, language: str = "python") -> dict[str, Any]:
        """Add a package to the graph."""
        if not _is_cgc_available():
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

    async def execute_cypher(self, cypher_query: str) -> dict[str, Any]:
        """Execute raw Cypher query against the code graph."""
        if not _is_cgc_available():
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

    async def visualize(self, cypher_query: str) -> dict[str, Any]:
        """Generate Mermaid diagram from Cypher query."""
        if not _is_cgc_available():
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

    async def get_module_deps(self, module_name: str) -> dict[str, Any]:
        """Get module dependencies for a given module."""
        if not _is_cgc_available():
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

    async def get_call_chain(self, function_name: str) -> dict[str, Any]:
        """Get full call chain for a function."""
        if not _is_cgc_available():
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
    ) -> dict[str, Any]:
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


_code_graph_retriever: CodeGraphRetriever | None = None


def get_code_graph_retriever(repo_path: str | None = None) -> CodeGraphRetriever:
    global _code_graph_retriever
    if _code_graph_retriever is None:
        _code_graph_retriever = CodeGraphRetriever(repo_path=repo_path)
    return _code_graph_retriever


from retrieval.registry import get_registry
registry = get_registry()
registry.register("code_graph", get_code_graph_retriever, "retrieval.code_graph")
