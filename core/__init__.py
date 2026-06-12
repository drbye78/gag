# Core infrastructure modules
from core.auth import get_rbac_manager, get_token_manager
from core.background import get_task_runner, get_ws_manager
from core.cache import get_cache, get_cache_wrapper
from core.config import get_logger, get_settings, setup_logging
from core.health import get_health_checker
from core.middleware import (
    get_error_handler,
    get_rate_limiter,
    sanitize_html,
    sanitize_input,
)
from core.observability import MetricsCollector, get_metrics_collector


def get_metrics() -> MetricsCollector:
    return get_metrics_collector()


def observe_request(method: str, path: str, status: int, duration: float) -> None:
    get_metrics_collector().record_request(method, path, status, duration)


def observe_retrieval(source: str, duration: float, count: int) -> None:
    get_metrics_collector().record_retrieval(source, duration, count)


def observe_llm(duration: float, model: str, tokens: int) -> None:
    get_metrics_collector().record_llm(duration, model, tokens)
