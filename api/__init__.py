"""
API Module - FastAPI and MCP endpoints.

Exports: FastAPI app, MCP handler, and JSON schema.
"""

from api.main import app
from api.mcp import MCP_JSON_SCHEMA, MCPHandler, get_mcp_handler

__all__ = [
    "app",
    "MCPHandler",
    "get_mcp_handler",
    "MCP_JSON_SCHEMA",
]
