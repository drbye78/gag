import contextvars
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class TraceContext:
    def __init__(self, trace_id: Optional[str] = None):
        self.trace_id = trace_id or self._generate_trace_id()
        self.started_at = datetime.now(timezone.utc)
        self.steps: List[TraceStep] = []
    
    def _generate_trace_id(self) -> str:
        import uuid
        return f"trace-{uuid.uuid4().hex[:12]}"
    
    def add_step(
        self,
        name: str,
        input_summary: Dict[str, Any],
        output_summary: Dict[str, Any],
        latency_ms: int,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.steps.append(TraceStep(
            trace_id=self.trace_id,
            step_name=name,
            input_summary=input_summary,
            output_summary=output_summary,
            latency_ms=latency_ms,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {},
        ))


class TraceStep:
    def __init__(
        self,
        trace_id: str,
        step_name: str,
        input_summary: Dict[str, Any],
        output_summary: Dict[str, Any],
        latency_ms: int,
        timestamp: datetime,
        metadata: Dict[str, Any],
    ):
        self.trace_id = trace_id
        self.step_name = step_name
        self.input_summary = input_summary
        self.output_summary = output_summary
        self.latency_ms = latency_ms
        self.timestamp = timestamp
        self.metadata = metadata


class TraceLogger:
    def __init__(self, log_file: str = "traces.jsonl"):
        self.log_file = log_file
        self.logger = logging.getLogger("trace")
        self.logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)
    
    def log(self, context: TraceContext):
        entry = {
            "trace_id": context.trace_id,
            "started_at": context.started_at.isoformat(),
            "duration_ms": sum(s.latency_ms for s in context.steps),
            "step_count": len(context.steps),
            "steps": [
                {
                    "name": s.step_name,
                    "latency_ms": s.latency_ms,
                    "input": s.input_summary,
                    "output": s.output_summary,
                    "timestamp": s.timestamp.isoformat(),
                }
                for s in context.steps
            ],
        }
        
        self.logger.info(json.dumps(entry))


class MetricsCollector:
    MAX_SAMPLES_PER_KEY = 10000

    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._gauges: Dict[str, float] = {}
    
    def record_latency(self, operation: str, latency_ms: float):
        if operation not in self._histograms:
            self._histograms[operation] = []
        self._histograms[operation].append(latency_ms)
        if len(self._histograms[operation]) > self.MAX_SAMPLES_PER_KEY:
            self._histograms[operation] = self._histograms[operation][-self.MAX_SAMPLES_PER_KEY:]
    
    def record_error(self, operation: str, error_type: str):
        key = f"{operation}.{error_type}"
        self._counters[key] = self._counters.get(key, 0) + 1
    
    def increment(self, metric: str, value: int = 1):
        self._counters[metric] = self._counters.get(metric, 0) + value
    
    def gauge(self, metric: str, value: float):
        self._gauges[metric] = value
    
    def _percentile(self, values: List[float], p: float) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        idx = int(len(sorted_vals) * p)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]
    
    def get_metrics(self) -> Dict[str, Any]:
        return {
            "latencies": {
                op: {
                    "p50": self._percentile(vals, 0.5),
                    "p95": self._percentile(vals, 0.95),
                    "p99": self._percentile(vals, 0.99),
                    "count": len(vals),
                }
                for op, vals in self._histograms.items()
            },
            "counters": self._counters,
            "gauges": self._gauges,
        }


_trace_logger: Optional[TraceLogger] = None
_metrics_collector: Optional[MetricsCollector] = None


def get_trace_logger() -> TraceLogger:
    global _trace_logger
    if _trace_logger is None:
        _trace_logger = TraceLogger()
    return _trace_logger

def get_metrics_collector() -> MetricsCollector:
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


OTEL_AVAILABLE = False
try:
    from opentelemetry import trace as _otel_trace
    from opentelemetry.sdk.trace import TracerProvider as _Tp
    from opentelemetry.sdk.trace.export import BatchSpanProcessor as _Bsp, ConsoleSpanExporter as _Cse
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as _Otlp
    from opentelemetry.sdk.resources import Resource as _Res, SERVICE_NAME as _SvcName
    from opentelemetry.trace import Status as _St, StatusCode as _Sc
    
    trace = _otel_trace
    TracerProvider = _Tp
    BatchSpanProcessor = _Bsp
    ConsoleSpanExporter = _Cse
    OTLPSpanExporter = _Otlp
    Resource = _Res
    SERVICE_NAME = _SvcName
    Status = _St
    StatusCode = _Sc
    OTEL_AVAILABLE = True
except ImportError:
    pass

_tracer_provider: Optional["TracerProvider"] = None
_active_span_slot: contextvars.ContextVar[Optional[Any]] = contextvars.ContextVar("active_span", default=None)

def setup_otel_tracing(settings) -> Optional["TracerProvider"]:
    global _tracer_provider
    if not OTEL_AVAILABLE or not settings.enable_tracing:
        return None
    resource = Resource.create({SERVICE_NAME: settings.otel_service_name})
    provider = TracerProvider(resource=resource)
    if settings.otel_exporter_console:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    if settings.otel_exporter_otlp_endpoint:
        exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
            insecure=settings.otel_exporter_otlp_insecure,
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _tracer_provider = provider
    return provider

def get_tracer(name: str = "eis"):
    if not OTEL_AVAILABLE:
        return None
    return trace.get_tracer(name)

def start_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    tracer = get_tracer()
    if tracer is None:
        return None
    span = tracer.start_span(name, attributes=attributes or {})
    _active_span_slot.set(span)
    return span

def end_span(span, error: Optional[Exception] = None):
    if span is None:
        return
    if error:
        span.set_status(Status(StatusCode.ERROR, str(error)))
        span.record_exception(error)
    span.end()

def with_trace(name: str, attributes: Optional[Dict[str, Any]] = None):
    tracer = get_tracer()
    if tracer is None:
        return lambda f: f
    def decorator(func):
        def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(name, attributes=attributes or {}) as span:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        return wrapper
    return decorator

__all__ = [
    "TraceContext",
    "TraceStep", 
    "TraceLogger",
    "MetricsCollector",
    "get_trace_logger",
    "get_metrics_collector",
    "setup_otel_tracing",
    "get_tracer",
    "start_span",
    "end_span",
    "with_trace",
    "OTEL_AVAILABLE",
]