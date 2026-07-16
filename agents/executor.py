"""
Tool Executor - Pipeline-based tool execution with retry logic.

Manages concurrent tool execution, timeout handling, and retry logic
with metrics tracking.
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from tools.base import get_tool_registry, BaseTool, ToolOutput


class ToolStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ToolResult:
    tool: str
    status: ToolStatus = ToolStatus.PENDING
    output: Any = None
    error: Optional[str] = None
    took_ms: int = 0
    retries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "took_ms": self.took_ms,
            "retries": self.retries,
        }


class ToolPipeline:
    def __init__(
        self,
        tools: List[str],
        args: Dict[str, Any],
        on_failure: str = "continue",
    ):
        self.tools = tools
        self.args = args
        self.on_failure = on_failure
        self.results: Dict[str, ToolResult] = {}

    def add_result(self, tool: str, result: ToolResult):
        self.results[tool] = result

    def get_result(self, tool: str) -> Optional[ToolResult]:
        return self.results.get(tool)

    def is_complete(self) -> bool:
        return len(self.results) == len(self.tools)

    def has_failures(self) -> bool:
        return any(r.status == ToolStatus.FAILED for r in self.results.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tools": self.tools,
            "args": self.args,
            "results": {k: v.to_dict() for k, v in self.results.items()},
            "complete": self.is_complete(),
            "has_failures": self.has_failures(),
        }


class ToolExecutor:
    def __init__(
        self,
        max_concurrent: int = 3,
        default_timeout: int = 60,
        max_retries: int = 2,
    ):
        self.registry = get_tool_registry()
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self._semaphore = asyncio.Semaphore(max_concurrent)

        self._metrics = {
            "total_executions": 0,
            "successful": 0,
            "failed": 0,
            "retries": 0,
            "total_time_ms": 0,
        }

    async def execute(
        self,
        tool_name: str,
        args: Dict[str, Any],
        timeout: Optional[int] = None,
    ) -> ToolResult:
        start_time = asyncio.get_event_loop().time()

        result = ToolResult(tool=tool_name)

        for attempt in range(self.max_retries + 1):
            try:
                tool = self.registry.get(tool_name)
                if not tool:
                    result.status = ToolStatus.FAILED
                    result.error = f"Tool not found: {tool_name}"
                    break

                if not tool.validate_input(args):
                    result.status = ToolStatus.FAILED
                    result.error = "Invalid input"
                    break

                async with self._semaphore:
                    tool_output = await asyncio.wait_for(
                        tool.execute(args),
                        timeout=timeout or self.default_timeout,
                    )

                result.status = ToolStatus.COMPLETED
                result.output = tool_output.result
                result.error = None
                result.retries = attempt
                break

            except asyncio.TimeoutError:
                result.status = ToolStatus.FAILED
                result.error = "Timeout"
                if attempt < self.max_retries:
                    self._metrics["retries"] += 1
            except Exception as e:
                result.status = ToolStatus.FAILED
                result.error = str(e)
                if attempt < self.max_retries:
                    self._metrics["retries"] += 1
            finally:
                result.took_ms = int(
                    (asyncio.get_event_loop().time() - start_time) * 1000
                )

        self._update_metrics(result)
        return result

    async def execute_parallel(
        self,
        tools: List[str],
        args: Dict[str, Any],
    ) -> Dict[str, ToolResult]:
        tasks = [self.execute(tool, args) for tool in tools]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = {}
        for tool, result in zip(tools, results):
            if isinstance(result, Exception):
                output[tool] = ToolResult(
                    tool=tool,
                    status=ToolStatus.FAILED,
                    error=str(result),
                )
            else:
                output[tool] = result

        return output

    async def execute_sequential(
        self,
        tools: List[str],
        args: Dict[str, Any],
        fail_fast: bool = True,
    ) -> Dict[str, ToolResult]:
        output = {}

        for tool in tools:
            result = await self.execute(tool, args)
            output[tool] = result

            if fail_fast and result.status == ToolStatus.FAILED:
                break

        return output

    async def execute_pipeline(
        self,
        pipeline: ToolPipeline,
    ) -> ToolPipeline:
        for tool_name in pipeline.tools:
            result = await self.execute(tool_name, pipeline.args)
            pipeline.add_result(tool_name, result)

            if pipeline.on_failure == "stop" and result.status == ToolStatus.FAILED:
                break

        return pipeline

    def _update_metrics(self, result: ToolResult):
        self._metrics["total_executions"] += 1
        if result.status == ToolStatus.COMPLETED:
            self._metrics["successful"] += 1
        else:
            self._metrics["failed"] += 1

        self._metrics["total_time_ms"] += result.took_ms

    def get_metrics(self) -> Dict[str, Any]:
        avg_time = (
            self._metrics["total_time_ms"] / self._metrics["total_executions"]
            if self._metrics["total_executions"] > 0
            else 0
        )
        return {
            **self._metrics,
            "success_rate": (
                self._metrics["successful"] / self._metrics["total_executions"]
                if self._metrics["total_executions"] > 0
                else 0
            ),
            "avg_time_ms": int(avg_time),
        }

    def list_tools(self) -> List[Dict[str, str]]:
        return self.registry.list_tools()


def get_tool_executor() -> ToolExecutor:
    return ToolExecutor()
