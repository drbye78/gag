"""
Structured logging configuration for production observability.

Provides JSON logging with correlation IDs for request tracing.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar

correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        corr_id = correlation_id.get()
        if corr_id:
            log_data["correlation_id"] = corr_id

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        extra = getattr(record, "extra", {})
        for key, value in extra.items():
            if key not in ("msg", "exc_info"):
                log_data[key] = value

        return json.dumps(log_data)


def setup_logging(level: str = "INFO", json_format: bool = False) -> None:
    """Configure logging for the application."""
    handler = logging.StreamHandler(sys.stdout)

    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.addHandler(handler)

    logging.getLogger("uvicorn").setLevel(logging.WARNING)


def set_correlation_id(corr_id: str) -> None:
    """Set correlation ID for current request context."""
    correlation_id.set(corr_id)


def get_correlation_id() -> Optional[str]:
    """Get correlation ID from current context."""
    return correlation_id.get()


def clear_correlation_id() -> None:
    """Clear correlation ID from current context."""
    correlation_id.set(None)
