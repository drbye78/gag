"""Structured error hierarchy for the Engineering Intelligence System."""

import functools
import logging
from typing import Any, Callable, Dict, Generic, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Result(Generic[T]):
    """Type-safe result container for success/error states."""
    
    __slots__ = ()
    
    def __init__(self, value: Any, error: Optional[str]):
        self._v = value
        self._e = error
    
    @staticmethod
    def ok(value: T) -> "Result[T]":
        r: Result[T] = object.__new__(Result)
        r._v = value
        r._e = None
        return r
    
    @staticmethod
    def err(error: str) -> "Result[T]":
        r: Result[T] = object.__new__(Result)
        r._v = None
        r._e = error
        return r
    
    @property
    def is_ok(self) -> bool:
        return self._e is None
    
    @property
    def is_err(self) -> bool:
        return self._e is not None
    
    @property
    def value(self) -> T:
        if self._e:
            raise ValueError(f"Result is error: {self._e}")
        return self._v
    
    @property
    def error(self) -> str:
        return self._e or "Unknown"
    
    def unwrap_or(self, default: T) -> T:
        return self._v if self.is_ok else default
    
    def __repr__(self) -> str:
        if self.is_ok:
            return f"Ok({self._v!r})"
        return f"Err({self._e!r})"


def handle_errors(
    default_return: Any = None,
    log_level: str = "error",
    capture_details: bool = True,
):
    """Decorator that catches exceptions and returns structured error results.
    
    Usage:
        @handle_errors(default_return=[], log_level="warning")
        async def fetch_data():
            ...
    
    Args:
        default_return: Value to return on exception
        log_level: Log level for exception (debug, info, warning, error)
        capture_details: Whether to include exception details in logging
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                getattr(logger, log_level)(
                    f"{func.__name__} failed: {e}",
                    exc_info=capture_details,
                )
                return default_return
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                getattr(logger, log_level)(
                    f"{func.__name__} failed: {e}",
                    exc_info=capture_details,
                )
                return default_return
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


class EISError(Exception):
    """Base exception for all EIS system errors."""

    code: str = "EIS_ERROR"
    status_code: int = 500
    is_retryable: bool = False

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause
        self._log()

    def _log(self) -> None:
        if self.cause:
            logger.error(
                "%s: %s (cause=%s, details=%s)",
                self.code,
                self.message,
                type(self.cause).__name__,
                self.details,
            )
        else:
            logger.error("%s: %s (details=%s)", self.code, self.message, self.details)


class ConfigurationError(EISError):
    """Invalid configuration at startup."""

    code = "CONFIG_ERROR"
    status_code = 500
    is_retryable = False


class ServiceUnavailableError(EISError):
    """External dependency (DB, LLM, etc.) is unavailable."""

    code = "SERVICE_UNAVAILABLE"
    status_code = 503
    is_retryable = True


class StorageError(EISError):
    """Vector or graph database operation failed."""

    code = "STORAGE_ERROR"
    status_code = 500
    is_retryable = True


class RetrievalError(EISError):
    """Retrieval operation failed."""

    code = "RETRIEVAL_ERROR"
    status_code = 500
    is_retryable = True


class IngestionError(EISError):
    """Document ingestion pipeline failed."""

    code = "INGESTION_ERROR"
    status_code = 500
    is_retryable = False


class AuthenticationError(EISError):
    """Authentication or authorization failed."""

    code = "AUTH_ERROR"
    status_code = 401
    is_retryable = False


class RateLimitError(EISError):
    """Rate limit exceeded."""

    code = "RATE_LIMIT"
    status_code = 429
    is_retryable = True


class ValidationError(EISError):
    """Input validation failed."""

    code = "VALIDATION_ERROR"
    status_code = 400
    is_retryable = False


class OrchestrationError(EISError):
    """Orchestration pipeline failed."""

    code = "ORCHESTRATION_ERROR"
    status_code = 500
    is_retryable = True


class PlanningError(OrchestrationError):
    """Planning step failed."""

    code = "PLANNING_ERROR"
    status_code = 500
    is_retryable = False


class ReasoningError(OrchestrationError):
    """Reasoning step failed."""

    code = "REASONING_ERROR"
    status_code = 500
    is_retryable = True


class ToolExecutionError(OrchestrationError):
    """Tool execution failed."""

    code = "TOOL_EXECUTION_ERROR"
    status_code = 500
    is_retryable = True


class IRBuilderError(EISError):
    """IR building failed."""

    code = "IR_BUILD_ERROR"
    status_code = 500
    is_retryable = False


# Re-export for convenience
EISErrors = {
    "configuration": ConfigurationError,
    "service_unavailable": ServiceUnavailableError,
    "storage": StorageError,
    "retrieval": RetrievalError,
    "ingestion": IngestionError,
    "auth": AuthenticationError,
    "rate_limit": RateLimitError,
    "validation": ValidationError,
    "orchestration": OrchestrationError,
    "planning": PlanningError,
    "reasoning": ReasoningError,
    "tool_execution": ToolExecutionError,
    "ir_builder": IRBuilderError,
}


def error_response(exc: EISError) -> dict:
    """Convert exception to API response dict."""
    return {
        "error": exc.code,
        "message": exc.message,
        "details": exc.details,
    }