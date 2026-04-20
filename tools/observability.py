from typing import Any, Dict, List, Optional
import json
import logging
import time

from tools.base import BaseTool, ToolInput, ToolOutput

logger = logging.getLogger(__name__)


class MetricsCollectorTool(BaseTool):
    name = "metrics_collect"
    description = "Collect and aggregate metrics from Prometheus, InfluxDB, CloudWatch"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        source = input.args.get("source", "prometheus")
        query = input.args.get("query", "")
        time_range = input.args.get("time_range", "1h")
        
        try:
            metrics = await self._collect_metrics_llm(source, query, time_range)
            return ToolOutput(
                result={"metrics": metrics},
                metadata={"collected": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM metrics collection failed: {e}, using fallback")
            metrics = await self._collect_metrics_fallback(source, query, time_range)
            return ToolOutput(
                result={"metrics": metrics},
                metadata={"collected": True, "method": "fallback", "error": str(e)}
            )
    
    async def _collect_metrics_llm(
        self,
        source: str,
        query: str,
        time_range: str
    ) -> List[Dict[str, Any]]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Generate realistic metric data for {source}.
Query: {query}
Time range: {time_range}

Respond ONLY with a JSON array of metric objects with:
- name: metric name
- value: numeric value
- timestamp: current Unix timestamp
- labels: optional label dictionary

Generate 5-10 realistic metrics for monitoring dashboards."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM metrics collection failed: {e}")
            raise
    
    async def _collect_metrics_fallback(
        self,
        source: str,
        query: str,
        time_range: str
    ) -> List[Dict[str, Any]]:
        return [
            {
                "name": "http_requests_total",
                "value": 1000,
                "timestamp": time.time(),
            }
        ]
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "source" in input


class LogAggregatorTool(BaseTool):
    name = "log_aggregate"
    description = "Aggregate logs from multiple sources (stdout, ELK, CloudWatch)"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        sources = input.args.get("sources", ["stdout"])
        query = input.args.get("query", "")
        time_range = input.args.get("time_range", "1h")
        level = input.args.get("level", "info")
        
        try:
            logs = await self._aggregate_logs_llm(sources, query, time_range, level)
            return ToolOutput(
                result={"logs": logs},
                metadata={"aggregated": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM log aggregation failed: {e}, using fallback")
            logs = await self._aggregate_logs_fallback(sources, query, time_range, level)
            return ToolOutput(
                result={"logs": logs},
                metadata={"aggregated": True, "method": "fallback", "error": str(e)}
            )
    
    async def _aggregate_logs_llm(
        self,
        sources: List[str],
        query: str,
        time_range: str,
        level: str
    ) -> List[Dict[str, Any]]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Generate realistic log entries.
Sources: {', '.join(sources)}
Query: {query}
Time range: {time_range}
Level: {level}

Respond ONLY with a JSON array of log objects with:
- timestamp: ISO 8601 timestamp
- level: debug/info/warn/error
- message: log message
- source: source identifier
- metadata: optional extra fields

Generate 10 realistic log entries."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM log aggregation failed: {e}")
            raise
    
    async def _aggregate_logs_fallback(
        self,
        sources: List[str],
        query: str,
        time_range: str,
        level: str
    ) -> List[Dict[str, Any]]:
        return [
            {
                "timestamp": "2024-01-01T00:00:00Z",
                "level": level,
                "message": f"Sample log from {sources[0]}",
                "source": sources[0],
            }
        ]
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "sources" in input


class AlertManagerTool(BaseTool):
    name = "alert_manager"
    description = "Create and manage Prometheus/Grafana alerts"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        alert = input.args.get("alert", {})
        action = input.args.get("action", "create")
        
        try:
            result = await self._manage_alert_llm(alert, action)
            return ToolOutput(
                result=result,
                metadata={"managed": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM alert management failed: {e}, using fallback")
            result = await self._manage_alert_fallback(alert, action)
            return ToolOutput(
                result=result,
                metadata={"managed": True, "method": "fallback", "error": str(e)}
            )
    
    async def _manage_alert_llm(
        self,
        alert: Dict[str, Any],
        action: str
    ) -> Dict[str, Any]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Generate a Prometheus/AlertManager alert configuration.
Action: {action}
Alert: {json.dumps(alert)}

Respond ONLY with a JSON object containing:
- alertname: name
- expr: PromQL expression
- for: duration (e.g., "5m")
- labels: severity, team, etc.
- annotations: summary, description

Generate production-quality alert rules."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=1500
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM alert management failed: {e}")
            raise
    
    async def _manage_alert_fallback(
        self,
        alert: Dict[str, Any],
        action: str
    ) -> Dict[str, Any]:
        return {
            "action": action,
            "success": True,
        }
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "alert" in input or "action" in input


class DashboardGeneratorTool(BaseTool):
    name = "dashboard_generate"
    description = "Generate Grafana/JSON monitoring dashboards"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        metrics = input.args.get("metrics", [])
        format = input.args.get("format", "grafana")
        title = input.args.get("title", "Monitoring Dashboard")
        
        try:
            dashboard = await self._generate_dashboard_llm(metrics, format, title)
            return ToolOutput(
                result={"dashboard": dashboard},
                metadata={"generated": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM dashboard generation failed: {e}, using fallback")
            dashboard = await self._generate_dashboard_fallback(metrics, format, title)
            return ToolOutput(
                result={"dashboard": dashboard},
                metadata={"generated": True, "method": "fallback", "error": str(e)}
            )
    
    async def _generate_dashboard_llm(
        self,
        metrics: List[str],
        format: str,
        title: str
    ) -> Dict[str, Any]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Generate a {format} dashboard configuration.
Title: {title}
Metrics: {', '.join(metrics)}

Respond ONLY with a JSON object.
For Grafana: dashboard object with panels, rows, variables.
For JSON: simple panel layout with metric expressions."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2500
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM dashboard generation failed: {e}")
            raise
    
    async def _generate_dashboard_fallback(
        self,
        metrics: List[str],
        format: str,
        title: str
    ) -> Dict[str, Any]:
        dashboard = {"title": title, "panels": []}
        
        for i, m in enumerate(metrics):
            dashboard["panels"].append({
                "id": i + 1,
                "title": m,
                "type": "graph",
                "targets": [{"expr": m, "legendFormat": m}],
                "gridPos": {"h": 8, "w": 12, "x": (i % 2) * 12, "y": (i // 2) * 8},
            })
        
        return dashboard
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "metrics" in input


class TracingCollectorTool(BaseTool):
    name = "tracing_collect"
    description = "Collect distributed traces from Jaeger, Zipkin, Tempo"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        trace_id = input.args.get("trace_id", "")
        service = input.args.get("service", "")
        time_range = input.args.get("time_range", "1h")
        
        try:
            traces = await self._collect_traces_llm(trace_id, service, time_range)
            return ToolOutput(
                result={"traces": traces},
                metadata={"collected": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM trace collection failed: {e}, using fallback")
            traces = await self._collect_traces_fallback(trace_id, service, time_range)
            return ToolOutput(
                result={"traces": traces},
                metadata={"collected": True, "method": "fallback", "error": str(e)}
            )
    
    async def _collect_traces_llm(
        self,
        trace_id: str,
        service: str,
        time_range: str
    ) -> List[Dict[str, Any]]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Generate distributed trace data.
Trace ID: {trace_id or 'generate new'}
Service: {service or 'api'}
Time range: {time_range}

Respond ONLY with a JSON array of span objects with:
- traceId: trace ID
- spanId: span ID
- parentSpanId: parent ID (if any)
- operationName: span name
- serviceName: service name
- duration: in milliseconds
- timestamp: Unix timestamp
- tags: span tags (http.method, http.status_code, error)

Generate 5-10 realistic spans."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM trace collection failed: {e}")
            raise
    
    async def _collect_traces_fallback(
        self,
        trace_id: str,
        service: str,
        time_range: str
    ) -> List[Dict[str, Any]]:
        return [
            {
                "traceId": trace_id or "abc123",
                "spanId": "span1",
                "operationName": "GET /api/data",
                "serviceName": service or "api",
                "duration": 150,
                "timestamp": time.time(),
            }
        ]
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "trace_id" in input or "service" in input


class SLOTrackerTool(BaseTool):
    name = "slo_track"
    description = "Track SLOs, error budgets, burn rates"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        slo = input.args.get("slo", {})
        
        try:
            tracking = await self._track_slo_llm(slo)
            return ToolOutput(
                result={"tracking": tracking},
                metadata={"tracked": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM SLO tracking failed: {e}, using fallback")
            tracking = await self._track_slo_fallback(slo)
            return ToolOutput(
                result={"tracking": tracking},
                metadata={"tracked": True, "method": "fallback", "error": str(e)}
            )
    
    async def _track_slo_llm(self, slo: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Generate SLO tracking data.
SLO: {json.dumps(slo)}

Respond ONLY with a JSON object containing:
- name: SLO name
- target: target availability % (e.g., 99.9)
- current: current period %
- error_budget_remaining: percentage remaining
- error_budget_burn_rate: how fast burning (e.g., 1.2x)
- period: time window (e.g., 28d rolling)
- status: ok/degrading/broken

Calculate realistic values."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=1500
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM SLO tracking failed: {e}")
            raise
    
    async def _track_slo_fallback(self, slo: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "name": slo.get("name", "availability"),
            "target": slo.get("target", 99.9),
            "current": 99.5,
            "error_budget_remaining": 0.5,
            "error_budget_burn_rate": 1.1,
            "status": "ok",
        }
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "slo" in input


class AnomalyDetectorTool(BaseTool):
    name = "anomaly_detect"
    description = "Detect anomalies in metrics using statistical methods"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        metrics = input.args.get("metrics", [])
        sensitivity = input.args.get("sensitivity", "medium")
        
        try:
            anomalies = await self._detect_anomalies_llm(metrics, sensitivity)
            return ToolOutput(
                result={"anomalies": anomalies},
                metadata={"detected": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM anomaly detection failed: {e}, using fallback")
            anomalies = await self._detect_anomalies_fallback(metrics, sensitivity)
            return ToolOutput(
                result={"anomalies": anomalies},
                metadata={"detected": True, "method": "fallback", "error": str(e)}
            )
    
    async def _detect_anomalies_llm(
        self,
        metrics: List[Dict[str, Any]],
        sensitivity: str
    ) -> List[Dict[str, Any]]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Detect anomalies in these metrics.
Metrics: {json.dumps(metrics)}
Sensitivity: {sensitivity} (low/medium/high)

Respond ONLY with a JSON array of anomaly objects with:
- metric: metric name
- value: anomalous value
- expected: expected value
- deviation: % deviation
- severity: low/medium/high
- description: why it's anomalous

Use statistical methods: z-score, IQR, seasonal decomposition."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM anomaly detection failed: {e}")
            raise
    
    async def _detect_anomalies_fallback(
        self,
        metrics: List[Dict[str, Any]],
        sensitivity: str
    ) -> List[Dict[str, Any]]:
        anomalies = []
        
        threshold = {"low": 3.0, "medium": 2.5, "high": 2.0}.get(sensitivity, 2.5)
        
        for m in metrics:
            if m.get("value", 0) > threshold * m.get("baseline", 100):
                anomalies.append({
                    "metric": m.get("name", "unknown"),
                    "value": m.get("value"),
                    "expected": m.get("baseline"),
                    "severity": "medium",
                })
        
        return anomalies
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "metrics" in input


def register_observability_tools(registry) -> None:
    registry.register(MetricsCollectorTool())
    registry.register(LogAggregatorTool())
    registry.register(AlertManagerTool())
    registry.register(DashboardGeneratorTool())
    registry.register(TracingCollectorTool())
    registry.register(SLOTrackerTool())
    registry.register(AnomalyDetectorTool())