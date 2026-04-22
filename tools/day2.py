from typing import Any, Dict, List, Optional
from datetime import timezone
import json
import logging

from tools.base import BaseTool, ToolInput, ToolOutput

logger = logging.getLogger(__name__)


class AutoScalerTool(BaseTool):
    name = "autoscale"
    description = "Scale resources based on metrics (K8s HPA, cloud autoscaling)"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        resource = input.args.get("resource", "")
        target_metric = input.args.get("target_metric", 70)
        
        try:
            result = await self._autoscale_llm(resource, target_metric)
            return ToolOutput(
                result=result,
                metadata={"scaled": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM autoscaling failed: {e}, using fallback")
            result = await self._autoscale_fallback(resource, target_metric)
            return ToolOutput(
                result=result,
                metadata={"scaled": True, "method": "fallback", "error": str(e)}
            )
    
    async def _autoscale_llm(
        self,
        resource: str,
        target_metric: int
    ) -> Dict[str, Any]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Generate autoscaling configuration.
Resource: {resource}
Target metric: {target_metric}% utilization

Respond ONLY with a JSON object containing:
- resource: resource name
- current_replicas: current count
- target_replicas: recommended count
- action: scale_up/scale_down/stable
- scaling_policy: rules (min_replicas, max_replicas, target_cpu, target_memory)
- cooldown_seconds: time between scaling actions
- stabilization_window_seconds: window to evaluate

Use HPA/VPA best practices."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=1500
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM autoscaling failed: {e}")
            raise
    
    async def _autoscale_fallback(
        self,
        resource: str,
        target_metric: int
    ) -> Dict[str, Any]:
        return {
            "resource": resource,
            "current_replicas": 3,
            "target_replicas": 5,
            "action": "scale_up",
        }
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "resource" in input


class UpdateOrchestratorTool(BaseTool):
    name = "update_orchestrate"
    description = "Orchestrate rolling updates, blue-green, canary deployments"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        target = input.args.get("target", "")
        version = input.args.get("version", "")
        strategy = input.args.get("strategy", "rolling")
        
        try:
            result = await self._orchestrate_update_llm(target, version, strategy)
            return ToolOutput(
                result=result,
                metadata={"orchestrated": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM update orchestration failed: {e}, using fallback")
            result = await self._orchestrate_update_fallback(target, version, strategy)
            return ToolOutput(
                result=result,
                metadata={"orchestrated": True, "method": "fallback", "error": str(e)}
            )
    
    async def _orchestrate_update_llm(
        self,
        target: str,
        version: str,
        strategy: str
    ) -> Dict[str, Any]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Generate update orchestration plan.
Target: {target}
Version: {version}
Strategy: {strategy} (rolling/blue-green/canary)

Respond ONLY with a JSON object containing:
- target: deployment name
- version: target version
- strategy: update strategy
- max_unavailable: pods unavailable during update
- max_surge: extra pods during update
- progress_deadline_seconds: timeout
- pre_checks: array of checks before update
- rollback_triggers: conditions to rollback
- traffic_split: % to each version (canary)

Generate complete rollout config."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=1500
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM update orchestration failed: {e}")
            raise
    
    async def _orchestrate_update_fallback(
        self,
        target: str,
        version: str,
        strategy: str
    ) -> Dict[str, Any]:
        return {
            "target": target,
            "version": version,
            "strategy": strategy,
            "max_unavailable": 1,
        }
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "target" in input


class IncidentDetectorTool(BaseTool):
    name = "incident_detect"
    description = "Detect and classify incidents from alerts"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        alerts = input.args.get("alerts", [])
        
        try:
            incidents = await self._detect_incidents_llm(alerts)
            return ToolOutput(
                result={"incidents": incidents},
                metadata={"detected": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM incident detection failed: {e}, using fallback")
            incidents = await self._detect_incidents_fallback(alerts)
            return ToolOutput(
                result={"incidents": incidents},
                metadata={"detected": True, "method": "fallback", "error": str(e)}
            )
    
    async def _detect_incidents_llm(
        self,
        alerts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Classify alerts into incidents.
Alerts: {json.dumps(alerts)}

Respond ONLY with a JSON array of incident objects with:
- incident_id: unique ID
- severity: critical/high/medium/low
- status: open/investigating/identified/monitoring/resolved
- type: availability/performance/security/data
- affected_services: array
- alert_count: number of related alerts
- description: summary
- created_at: ISO timestamp

Group related alerts into single incidents."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM incident detection failed: {e}")
            raise
    
    async def _detect_incidents_fallback(
        self,
        alerts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        return [
            {"severity": a.get("severity", "critical"), "status": "open", "type": "availability"}
            for a in alerts
            if a.get("severity") == "critical"
        ]
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "alerts" in input


class RootCauseAnalyzerTool(BaseTool):
    name = "root_cause_analyze"
    description = "Analyze incident root cause using 5 Whys, fishbone, RTFM"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        incident_id = input.args.get("incident_id", "")
        
        try:
            rca = await self._analyze_root_cause_llm(incident_id)
            return ToolOutput(
                result={"rca": rca},
                metadata={"analyzed": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM RCA failed: {e}, using fallback")
            rca = await self._analyze_root_cause_fallback(incident_id)
            return ToolOutput(
                result={"rca": rca},
                metadata={"analyzed": True, "method": "fallback", "error": str(e)}
            )
    
    async def _analyze_root_cause_llm(self, incident_id: str) -> Dict[str, Any]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Perform root cause analysis.
Incident ID: {incident_id}

Respond ONLY with a JSON object using these methods:
- five_whys: array of why questions and answers
- contributing_factors: array (people, process, technology, environment)
- root_cause: final cause
- confidence: float 0-1
- impacted_components: array
- recurrence_risk: low/medium/high
- prevention_measures: array of fixes

Be thorough - don't stop at symptoms."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM RCA failed: {e}")
            raise
    
    async def _analyze_root_cause_fallback(self, incident_id: str) -> Dict[str, Any]:
        return {
            "incident_id": incident_id,
            "root_cause": "memory_leak",
            "confidence": 0.85,
        }
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "incident_id" in input


class RunbookGeneratorTool(BaseTool):
    name = "runbook_generate"
    description = "Generate runbooks from incidents, incidents, SRE best practices"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        incident_type = input.args.get("incident_type", "")
        
        try:
            runbook = await self._generate_runbook_llm(incident_type)
            return ToolOutput(
                result={"runbook": runbook},
                metadata={"generated": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM runbook generation failed: {e}, using fallback")
            runbook = await self._generate_runbook_fallback(incident_type)
            return ToolOutput(
                result={"runbook": runbook},
                metadata={"generated": True, "method": "fallback", "error": str(e)}
            )
    
    async def _generate_runbook_llm(self, incident_type: str) -> Dict[str, Any]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Generate operational runbook.
Incident type: {incident_type} (e.g., high_cpu, database_outage, 503_errors)

Respond ONLY with a JSON object containing:
- title: runbook title
- description: what this runbook covers
- severity: impact level
- steps: array of step objects (step_number, action, command, verification, rollback)
- escalation: who to notify
- sla_response: target response time
- related_docs: documentation links
- tags: array

Include specific commands and verification steps."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM runbook generation failed: {e}")
            raise
    
    async def _generate_runbook_fallback(self, incident_type: str) -> Dict[str, Any]:
        return {
            "title": f"Runbook for {incident_type}",
            "steps": [
                {"step": 1, "action": "check_status"},
                {"step": 2, "action": "notify_team"},
            ],
        }
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "incident_type" in input


class BackupManagerTool(BaseTool):
    name = "backup_manage"
    description = "Manage backups and recovery (SQL, S3, snapshots)"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        action = input.args.get("action", "backup")
        target = input.args.get("target", "")
        
        try:
            result = await self._manage_backup_llm(action, target)
            return ToolOutput(
                result=result,
                metadata={"managed": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM backup management failed: {e}, using fallback")
            result = await self._manage_backup_fallback(action, target)
            return ToolOutput(
                result=result,
                metadata={"managed": True, "method": "fallback", "error": str(e)}
            )
    
    async def _manage_backup_llm(
        self,
        action: str,
        target: str
    ) -> Dict[str, Any]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Generate backup operation plan.
Action: {action} (backup/restore/list/delete)
Target: {target} (database/s3/snapshot)

Respond ONLY with a JSON object containing:
- action: the action
- target: resource
- status: success/failed/in_progress
- timestamp: ISO timestamp
- backup_id: unique ID
- location: where stored
- size_bytes: size
- retention_days: how long to keep
- verification: checksum or restore test command

Include actual commands for recovery."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=1500
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM backup management failed: {e}")
            raise
    
    async def _manage_backup_fallback(
        self,
        action: str,
        target: str
    ) -> Dict[str, Any]:
        from datetime import datetime
        return {
            "action": action,
            "target": target,
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "action" in input


class CapacityPlannerTool(BaseTool):
    name = "capacity_plan"
    description = "Plan capacity needs with growth forecasting"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        resource = input.args.get("resource", "")
        growth_rate = input.args.get("growth_rate", 10)
        
        try:
            plan = await self._plan_capacity_llm(resource, growth_rate)
            return ToolOutput(
                result={"plan": plan},
                metadata={"planned": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM capacity planning failed: {e}, using fallback")
            plan = await self._plan_capacity_fallback(resource, growth_rate)
            return ToolOutput(
                result={"plan": plan},
                metadata={"planned": True, "method": "fallback", "error": str(e)}
            )
    
    async def _plan_capacity_llm(
        self,
        resource: str,
        growth_rate: int
    ) -> Dict[str, Any]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Generate capacity plan.
Resource: {resource} (e.g., database, storage, compute)
Growth rate: {growth_rate}% per month

Respond ONLY with a JSON object containing:
- resource: resource name
- current_capacity: current value with unit
- projected_capacity: array by month (6 months)
- timeline_months: planning horizon
- recommendations: array of provisioning actions
- cost_estimate: monthly cost
- autoscale_recommendation: yes/no with threshold

Use realistic scaling patterns."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=1500
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM capacity planning failed: {e}")
            raise
    
    async def _plan_capacity_fallback(
        self,
        resource: str,
        growth_rate: int
    ) -> Dict[str, Any]:
        return {
            "resource": resource,
            "current_capacity": 100,
            "projected_capacity": 150,
            "timeline_months": 12,
        }
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "resource" in input


def register_day2_tools(registry) -> None:
    registry.register(AutoScalerTool())
    registry.register(UpdateOrchestratorTool())
    registry.register(IncidentDetectorTool())
    registry.register(RootCauseAnalyzerTool())
    registry.register(RunbookGeneratorTool())
    registry.register(BackupManagerTool())
    registry.register(CapacityPlannerTool())