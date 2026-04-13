"""Background task runner and WebSocket management."""

import asyncio
import time
from typing import Any, Awaitable, Dict, List, Optional

from dataclasses import dataclass, field


@dataclass
class BackgroundTask:
    id: str
    name: str
    status: str
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    _asyncio_task: Optional[asyncio.Task] = field(default=None, repr=False)


class BackgroundTaskRunner:
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self._tasks: Dict[str, BackgroundTask] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def submit(
        self,
        task_id: str,
        name: str,
        coro: Awaitable[Any],
    ) -> str:
        task = BackgroundTask(
            id=task_id,
            name=name,
            status="pending",
            created_at=time.time(),
        )
        self._tasks[task_id] = task

        async_task = asyncio.create_task(self._run_task(task_id, coro))
        task._asyncio_task = async_task
        return task_id

    async def _run_task(self, task_id: str, coro: Awaitable[Any]) -> None:
        async with self._semaphore:
            task = self._tasks.get(task_id)
            if not task:
                return

            task.status = "running"
            task.started_at = time.time()

            try:
                task.result = await coro
                task.status = "completed"
            except asyncio.CancelledError:
                task.status = "cancelled"
                task.error = "Task was cancelled"
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
            finally:
                task.completed_at = time.time()

    def get(self, task_id: str) -> Optional[BackgroundTask]:
        return self._tasks.get(task_id)

    def list(self, status: Optional[str] = None) -> List[BackgroundTask]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task and task._asyncio_task and not task._asyncio_task.done():
            task._asyncio_task.cancel()
            task.status = "cancelled"
            task.error = "Cancelled by user"
            task.completed_at = time.time()
            return True
        return False

    def delete(self, task_id: str) -> bool:
        if task_id in self._tasks:
            task = self._tasks[task_id]
            # Attempt cancellation if still running
            if task._asyncio_task and not task._asyncio_task.done():
                task._asyncio_task.cancel()
            del self._tasks[task_id]
            return True
        return False


class WebSocketManager:
    def __init__(self):
        self._connections: Dict[str, Any] = {}

    async def connect(self, client_id: str, websocket) -> None:
        await websocket.accept()
        self._connections[client_id] = websocket

    async def disconnect(self, client_id: str) -> None:
        if client_id in self._connections:
            try:
                await self._connections[client_id].close()
            except Exception:
                pass
            del self._connections[client_id]

    async def send(self, client_id: str, message: Dict[str, Any]) -> None:
        ws = self._connections.get(client_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                # Client disconnected; remove from connections
                await self.disconnect(client_id)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        for client_id in list(self._connections.keys()):
            await self.send(client_id, message)

    async def send_progress(
        self, client_id: str, progress: float, message: str
    ) -> None:
        await self.send(
            client_id,
            {
                "type": "progress",
                "progress": progress,
                "message": message,
            },
        )

    async def send_result(self, client_id: str, result: Any) -> None:
        await self.send(
            client_id,
            {
                "type": "result",
                "result": result,
            },
        )

    async def send_error(self, client_id: str, error: str) -> None:
        await self.send(
            client_id,
            {
                "type": "error",
                "error": error,
            },
        )

    @property
    def connected_count(self) -> int:
        return len(self._connections)


_runner: Optional[BackgroundTaskRunner] = None
_ws_manager: Optional[WebSocketManager] = None


def get_task_runner() -> BackgroundTaskRunner:
    global _runner
    if _runner is None:
        _runner = BackgroundTaskRunner()
    return _runner


def get_ws_manager() -> WebSocketManager:
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager
