"""
MCP Handler - JSON-RPC 2.0 MCP protocol implementation.

Handles initialize, tools/list, tools/call, and query
methods for MCP client integration.
"""

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from models.mcp import (
    MCPRequest,
    MCPResponse,
    MCPToolDefinition,
    MCPToolCall,
    MCPToolResult,
    MCP_TOOLS,
)
from agents.orchestration import OrchestrationEngine
from tools.base import ToolRegistry, MCPErrorCode


class MCPHandler:
    def __init__(self):
        self.engine = OrchestrationEngine()
        self.tool_registry = ToolRegistry()
        self._request_id: Optional[str] = None

    def _response_id(self) -> Optional[str]:
        return self._request_id or str(uuid.uuid4())

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        self._request_id = request.id
        method = request.method
        params = request.params or {}

        if method == "initialize":
            return await self._handle_initialize(params)
        elif method == "tools/list":
            return await self._handle_tools_list()
        elif method == "tools/call":
            return await self._handle_tools_call(params)
        elif method == "tools/call/batch":
            return await self._handle_tools_batch(params)
        elif method == "resources/list":
            return await self._handle_resources_list()
        elif method == "resources/read":
            return await self._handle_resources_read(params)
        elif method == "prompts/list":
            return await self._handle_prompts_list()
        elif method == "prompts/get":
            return await self._handle_prompts_get(params)
        elif method == "query":
            return await self._handle_query(params)
        else:
            return MCPResponse(
                jsonrpc="2.0",
                id=request.id,
                error={
                    "code": MCPErrorCode.TOOL_NOT_FOUND,
                    "message": f"Method not found: {method}",
                },
            )

    async def _handle_initialize(self, params: Dict[str, Any]) -> MCPResponse:
        tools = self.tool_registry.list_tools()
        resources = self.tool_registry.list_resources()
        prompts = self.tool_registry.list_prompts()

        return MCPResponse(
            jsonrpc="2.0",
            id=self._response_id(),
            result={
                "protocol_version": "1.0",
                "capabilities": {
                    "tools": len(tools) > 0,
                    "resources": len(resources) > 0,
                    "prompts": len(prompts) > 0,
                    "batch_tools": True,
                },
                "server_info": {
                    "name": "Engineering Intelligence System",
                    "version": "3.2.0",
                },
                "tool_count": len(tools),
                "resource_count": len(resources),
                "prompt_count": len(prompts),
            },
        )

    async def _handle_tools_list(self) -> MCPResponse:
        tools = self.tool_registry.list_tools()

        return MCPResponse(jsonrpc="2.0", id=self._response_id(), result={"tools": tools})

    async def _handle_tools_call(self, params: Dict[str, Any]) -> MCPResponse:
        name = params.get("name")
        arguments = params.get("arguments", {})

        if not name:
            return MCPResponse(
                jsonrpc="2.0",
                id=self._response_id(),
                error={
                    "code": MCPErrorCode.INVALID_PARAMS,
                    "message": "Missing required parameter: name",
                },
            )

        result = await self.tool_registry.execute(name, arguments)

        if result.error:
            return MCPResponse(
                jsonrpc="2.0",
                id=self._response_id(),
                error={
                    "code": MCPErrorCode.EXECUTION_FAILED,
                    "message": result.error,
                },
            )

        content = [{"type": "text", "text": json.dumps(result.result)}]

        return MCPResponse(
            jsonrpc="2.0",
            id=self._response_id(),
            result={"content": content, "isError": False},
        )

    async def _handle_tools_batch(self, params: Dict[str, Any]) -> MCPResponse:
        calls = params.get("calls", [])

        if not calls:
            return MCPResponse(
                jsonrpc="2.0",
                id=self._response_id(),
                error={
                    "code": MCPErrorCode.INVALID_PARAMS,
                    "message": "Missing required parameter: calls",
                },
            )

        results = await self.tool_registry.execute_batch(calls)

        output = []
        for i, result in enumerate(results):
            if result.error:
                output.append(
                    {
                        "index": i,
                        "error": result.error,
                        "isError": True,
                    }
                )
            else:
                output.append(
                    {
                        "index": i,
                        "result": result.result,
                        "isError": False,
                    }
                )

        return MCPResponse(jsonrpc="2.0", id=self._response_id(), result={"results": output})

    async def _handle_resources_list(self) -> MCPResponse:
        resources = self.tool_registry.list_resources()
        return MCPResponse(jsonrpc="2.0", id=self._response_id(), result={"resources": resources})

    async def _handle_resources_read(self, params: Dict[str, Any]) -> MCPResponse:
        uri = params.get("uri", "")
        name = uri.replace("resource://", "") if uri.startswith("resource://") else uri

        resource = self.tool_registry.get_resource(name)
        if not resource:
            return MCPResponse(
                jsonrpc="2.0",
                id=self._response_id(),
                error={
                    "code": MCPErrorCode.RESOURCE_NOT_FOUND,
                    "message": f"Resource not found: {name}",
                },
            )

        return MCPResponse(jsonrpc="2.0", id=self._response_id(), result={"content": resource})

    async def _handle_prompts_list(self) -> MCPResponse:
        prompts = self.tool_registry.list_prompts()
        return MCPResponse(jsonrpc="2.0", id=self._response_id(), result={"prompts": prompts})

    async def _handle_prompts_get(self, params: Dict[str, Any]) -> MCPResponse:
        name = params.get("name", "")

        prompt = self.tool_registry.get_prompt(name)
        if not prompt:
            return MCPResponse(
                jsonrpc="2.0",
                id=self._response_id(),
                error={
                    "code": MCPErrorCode.PROMPT_NOT_FOUND,
                    "message": f"Prompt not found: {name}",
                },
            )

        return MCPResponse(jsonrpc="2.0", id=self._response_id(), result={"prompt": prompt})

    async def _handle_query(self, params: Dict[str, Any]) -> MCPResponse:
        query = params.get("query", "")

        result = await self.engine.execute(query)

        return MCPResponse(jsonrpc="2.0", id=self._response_id(), result=result)


def create_mcp_response(
    result: Optional[Dict[str, Any]] = None,
    error: Optional[Dict[str, Any]] = None,
    id: Optional[str] = None,
) -> JSONResponse:
    response = {"jsonrpc": "2.0", "id": id}

    if result:
        response["result"] = result
    if error:
        response["error"] = error

    return JSONResponse(content=response)


def create_error_response(
    code: int, message: str, id: Optional[str] = None
) -> JSONResponse:
    return create_mcp_response(error={"code": code, "message": message}, id=id)


MCP_JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "MCP Request",
    "type": "object",
    "required": ["jsonrpc", "method"],
    "properties": {
        "jsonrpc": {"type": "string", "enum": ["2.0"]},
        "id": {"oneOf": [{"type": "string"}, {"type": "number"}]},
        "method": {"type": "string"},
        "params": {"type": "object"},
    },
}


_handler: Optional[MCPHandler] = None


def get_mcp_handler() -> MCPHandler:
    global _handler
    if _handler is None:
        _handler = MCPHandler()
    return _handler
