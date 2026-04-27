"""
MCP Handler - JSON-RPC 2.0 MCP protocol implementation.

Handles initialize, tools/list, tools/call, and query
methods for MCP client integration.
"""

import json
import time
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
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._subscriptions: Dict[str, Dict[str, Any]] = {}
        self._rate_limits: Dict[str, List[float]] = {}

    def _response_id(self) -> Optional[str]:
        return self._request_id or str(uuid.uuid4())

    def _get_or_create_session(self, session_id: Optional[str]) -> str:
        if not session_id:
            session_id = str(uuid.uuid4())
            self._sessions[session_id] = {"created_at": time.time(), "state": {}}
        elif session_id not in self._sessions:
            self._sessions[session_id] = {"created_at": time.time(), "state": {}}
        return session_id

    def _check_rate_limit(self, client_id: str, max_calls: int = 100, window_seconds: int = 60) -> bool:
        now = time.time()
        if client_id not in self._rate_limits:
            self._rate_limits[client_id] = []
        self._rate_limits[client_id] = [t for t in self._rate_limits[client_id] if now - t < window_seconds]
        if len(self._rate_limits[client_id]) >= max_calls:
            return False
        self._rate_limits[client_id].append(now)
        return True

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        self._request_id = request.id
        method = request.method
        params = request.params or {}
        client_id = params.get("client_id", "default") if params else "default"

        if not self._check_rate_limit(client_id):
            return MCPResponse(
                jsonrpc="2.0",
                id=request.id,
                error={"code": MCPErrorCode.RATELIMITED, "message": "Rate limit exceeded"},
            )

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
        elif method == "notifications/listen":
            return await self._handle_notifications_listen(params)
        elif method == "notifications/unsubscribe":
            return await self._handle_notifications_unsubscribe(params)
        elif method == "session/get":
            return await self._handle_session_get(params)
        elif method == "session/set":
            return await self._handle_session_set(params)
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
                    "sessions": True,
                    "notifications": True,
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
                output.append({
                    "index": i,
                    "error": result.error,
                    "isError": True,
                })
            else:
                output.append({
                    "index": i,
                    "result": result.result,
                    "isError": False,
                })

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

    async def _handle_notifications_listen(self, params: Dict[str, Any]) -> MCPResponse:
        topics = params.get("topics", [])
        stream = params.get("stream", False)
        subscription_id = f"sub_{uuid.uuid4().hex[:8]}"
        self._subscriptions[subscription_id] = {
            "topics": topics,
            "created_at": time.time(),
        }
        return MCPResponse(
            jsonrpc="2.0",
            id=self._response_id(),
            result={"subscription_id": subscription_id, "topics": topics},
        )

    async def _handle_notifications_unsubscribe(self, params: Dict[str, Any]) -> MCPResponse:
        subscription_id = params.get("subscription_id", "")
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            return MCPResponse(jsonrpc="2.0", id=self._response_id(), result={"success": True})
        return MCPResponse(
            jsonrpc="2.0",
            id=self._response_id(),
            error={"code": MCPErrorCode.RESOURCE_NOT_FOUND, "message": "Subscription not found"},
        )

    async def _handle_session_get(self, params: Dict[str, Any]) -> MCPResponse:
        session_id = params.get("session_id")
        key = params.get("key")
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            if key:
                return MCPResponse(jsonrpc="2.0", id=self._response_id(), result={"value": session["state"].get(key)})
            return MCPResponse(jsonrpc="2.0", id=self._response_id(), result={"state": session["state"]})
        return MCPResponse(
            jsonrpc="2.0",
            id=self._response_id(),
            error={"code": MCPErrorCode.SESSION_EXPIRED, "message": "Session not found"},
        )

    async def _handle_session_set(self, params: Dict[str, Any]) -> MCPResponse:
        session_id = self._get_or_create_session(params.get("session_id"))
        key = params.get("key")
        value = params.get("value")
        if key:
            self._sessions[session_id]["state"][key] = value
            return MCPResponse(jsonrpc="2.0", id=self._response_id(), result={"session_id": session_id})
        return MCPResponse(
            jsonrpc="2.0",
            id=self._response_id(),
            error={"code": MCPErrorCode.INVALID_PARAMS, "message": "Missing key/value"},
        )


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