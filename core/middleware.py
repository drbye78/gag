"""Middleware for rate limiting, error handling, and input sanitization."""

import time
from typing import Callable, Dict, Optional

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from core.config import get_settings


class RateLimiter:
    def __init__(self, requests: int = 100, window: int = 60, max_clients: int = 10000):
        self.requests = requests
        self.window = window
        self.max_clients = max_clients
        self._clients: Dict[str, list] = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 300

    def _get_client_id(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _clean_old_requests(self, client_id: str) -> None:
        now = time.time()
        if client_id in self._clients:
            self._clients[client_id] = [
                ts for ts in self._clients[client_id] if now - ts < self.window
            ]
            if not self._clients[client_id]:
                del self._clients[client_id]

    def _cleanup_stale_clients(self) -> None:
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        stale_keys = [
            cid for cid, timestamps in self._clients.items()
            if not timestamps or (now - timestamps[-1]) > self.window
        ]
        for key in stale_keys:
            del self._clients[key]

        if len(self._clients) > self.max_clients:
            sorted_clients = sorted(
                self._clients.items(),
                key=lambda x: x[1][-1] if x[1] else 0
            )
            for cid, _ in sorted_clients[:len(self._clients) - self.max_clients]:
                del self._clients[cid]

        self._last_cleanup = now

    async def check(self, request: Request) -> bool:
        self._cleanup_stale_clients()
        client_id = self._get_client_id(request)
        self._clean_old_requests(client_id)

        if client_id not in self._clients:
            self._clients[client_id] = []

        if len(self._clients[client_id]) >= self.requests:
            return False

        self._clients[client_id].append(time.time())
        return True

    async def __call__(self, request: Request) -> None:
        if not await self.check(request):
            raise HTTPException(
                status_code=429, detail="Rate limit exceeded. Please try again later."
            )


_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    settings = get_settings()
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            settings.rate_limit_requests, settings.rate_limit_window
        )
    return _rate_limiter


def sanitize_input(text: str, max_length: int = 10000) -> str:
    text = text.strip()
    if len(text) > max_length:
        text = text[:max_length]
    return text


def sanitize_prompt_input(text: str) -> str:
    """Remove common prompt injection patterns from user input."""
    import re

    # Common prompt injection patterns to block/filter
    injection_patterns = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"ignore\s+(all\s+)?(your\s+)?(system\s+)?(instructions?|directives?)",
        r"system:\s*",
        r"you\s+are\s+(now\s+)?",
        r"act\s+as\s+",
        r"pretend\s+(to\s+be|you\s+are)",
        r"forget\s+(everything|all|your)",
        r"new\s+instructions",
        r"override\s+(your\s+)?instructions",
        r"disregard\s+(your\s+)?(previous\s+)?(instructions?|rules?)",
        r"\[INST\]|\[/INST\]",
        r"<<SYS>>|<<\/SYS>>",
        r"<\|system\|>|<\|user\|>|<\|assistant\|>",
    ]

    for pattern in injection_patterns:
        text = re.sub(pattern, "[FILTERED]", text, flags=re.IGNORECASE)

    return text


def sanitize_html(text: str) -> str:
    import html

    text = html.escape(text)
    return text


class ErrorHandler:
    def __init__(self):
        self._errors: Dict[int, str] = {
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            422: "Validation Error",
            429: "Rate Limited",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
        }

    async def handle(self, request: Request, exc: Exception) -> JSONResponse:
        from core.config import get_settings
        from core.config import get_logger

        logger = get_logger("error")
        logger.error(f"{request.method} {request.url}: {exc}")

        if isinstance(exc, HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": self._errors.get(exc.status_code, "Error"),
                    "detail": exc.detail,
                    "status_code": exc.status_code,
                },
            )

        if get_settings().debug:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "detail": str(exc),
                    "status_code": 500,
                },
            )

        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": "An unexpected error occurred",
                "status_code": 500,
            },
        )


_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def setup_middleware(app) -> None:
    """Attach rate limiting and error handling middleware to a FastAPI app."""
    from fastapi import FastAPI

    if not isinstance(app, FastAPI):
        raise TypeError("setup_middleware expects a FastAPI application")

    rate_limiter = get_rate_limiter()

    @app.middleware("http")
    async def rate_limit_middleware(request, call_next):
        await rate_limiter(request)
        response = await call_next(request)
        return response

    error_handler = get_error_handler()
    app.add_exception_handler(Exception, error_handler.handle)

    app.state.middleware_configured = True
