"""
Planner Agent - Intent Detection and Execution Planning.

Detects user intent (design/explain/troubleshoot/optimize) and creates
execution plans with retrieval steps and tool invocations.
"""

from typing import Any, Dict, List, Optional

from agents.prompts import Intent, Step, create_planner_response


class ExecutionStep:
    def __init__(
        self,
        step_type: str,
        action: str,
        source: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ):
        self.step_type = step_type
        self.action = action
        self.source = source
        self.params = params or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_type": self.step_type,
            "action": self.action,
            "source": self.source,
            "params": self.params,
        }


class ExecutionPlan:
    def __init__(
        self,
        query: str,
        intent: str = "explain",
        steps: Optional[List[ExecutionStep]] = None,
        tools: Optional[List[str]] = None,
    ):
        self.query = query
        self.intent = intent
        self.steps = steps or []
        self.tools = tools or []
        self.current_step = 0

    def add_step(self, step: ExecutionStep):
        self.steps.append(step)

    def add_tool(self, tool: str):
        if tool not in self.tools:
            self.tools.append(tool)

    def next_step(self) -> Optional[ExecutionStep]:
        if self.current_step < len(self.steps):
            step = self.steps[self.current_step]
            self.current_step += 1
            return step
        return None

    def is_complete(self) -> bool:
        return self.current_step >= len(self.steps)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "intent": self.intent,
            "steps": [s.to_dict() for s in self.steps],
            "tools": self.tools,
            "current_step": self.current_step,
            "is_complete": self.is_complete(),
        }


class PlannerAgent:
    def __init__(self):
        self._default_sources = ["docs", "code", "graph", "tickets", "telemetry", "diagram", "ui_sketch"]
        # High-level intent mapping from QueryClassifier fine-grained intents
        self._classifier_intent_map = {
            "causal": Intent.TROUBLESHOOT,
            "relationship": Intent.EXPLAIN,
            "code_relationship": Intent.EXPLAIN,
            "complex": Intent.DESIGN,
            "fact": Intent.EXPLAIN,
            "list": Intent.EXPLAIN,
            "code": Intent.EXPLAIN,
            "documentation": Intent.EXPLAIN,
        }
        # Direct keyword overrides for explicit high-level intents
        self._explicit_intent_keywords = {
            Intent.DESIGN: ["design", "create", "build", "architect", "propose"],
            Intent.TROUBLESHOOT: ["debug", "troubleshoot", "diagnose", "root cause"],
            Intent.OPTIMIZE: ["improve", "optimize", "performance", "faster", "better", "scale"],
        }

    def _detect_intent(self, query: str) -> str:
        """Detect intent by delegating to QueryClassifier, then mapping to
        high-level planner intents. Explicit keyword matches take priority.
        """
        query_lower = query.lower()

        # 1. Check explicit high-level keywords first
        for intent, keywords in self._explicit_intent_keywords.items():
            if any(kw in query_lower for kw in keywords):
                return intent

        # Check UI implementation keywords → DESIGN intent
        ui_keywords = ["ui", "sketch", "wireframe", "implement ui", "screen layout", "mockup"]
        if any(kw in query_lower for kw in ui_keywords):
            return Intent.DESIGN

        # 2. Delegate to QueryClassifier for fine-grained classification
        try:
            from retrieval.classifier import get_query_classifier

            classifier = get_query_classifier()
            classification = classifier.classify(query)
            primary_intent = classification.get("primary_intent", "fact")
            return self._classifier_intent_map.get(primary_intent, Intent.EXPLAIN)
        except Exception:
            # Fallback to simple keyword matching if classifier unavailable
            return self._fallback_intent(query)

    def _fallback_intent(self, query: str) -> str:
        """Fallback intent detection when QueryClassifier is unavailable."""
        query_lower = query.lower()
        for intent, keywords in self._explicit_intent_keywords.items():
            if any(kw in query_lower for kw in keywords):
                return intent
        return Intent.EXPLAIN

    def _identify_sources(self, query: str) -> List[str]:
        query_lower = query.lower()
        sources = []

        if any(
            kw in query_lower for kw in ["doc", "document", "readme", "guide", "how to"]
        ):
            sources.append("docs")
        if any(
            kw in query_lower
            for kw in ["code", "function", "class", "implement", "api"]
        ):
            sources.append("code")
        if any(
            kw in query_lower
            for kw in ["architecture", "component", "service", "deploy"]
        ):
            sources.append("graph")
        if any(kw in query_lower for kw in ["issue", "bug", "ticket", "problem"]):
            sources.append("tickets")
        if any(kw in query_lower for kw in ["metric", "log", "performance", "monitor"]):
            sources.append("telemetry")

        # UI implementation keywords
        if any(kw in query_lower for kw in ["ui", "sketch", "wireframe", "screen", "layout", "mockup"]):
            sources.append("ui_sketch")

        if not sources:
            sources = self._default_sources

        return sources

    def _identify_tools(self, query: str) -> List[str]:
        query_lower = query.lower()
        tools = []

        if any(kw in query_lower for kw in ["evaluate", "assess", "review"]):
            tools.append("architecture_evaluate")
        if any(kw in query_lower for kw in ["security", "vulnerability", "secure"]):
            tools.append("security_validate")
        if any(kw in query_lower for kw in ["cost", "estimate", "price"]):
            tools.append("cost_estimate")

        return tools

    async def plan(
        self, query: str, ir_context: Optional[Dict[str, Any]] = None
    ) -> ExecutionPlan:
        intent = self._detect_intent(query)
        sources = self._identify_sources(query)
        tools = self._identify_tools(query)

        plan = ExecutionPlan(query=query, intent=intent)

        if intent == Intent.DESIGN:
            plan.add_step(
                ExecutionStep(step_type="analyze", action="analyze_ir", source="ir")
            )
            plan.add_step(
                ExecutionStep(step_type="retrieve", action="search", source="docs")
            )
            plan.add_step(
                ExecutionStep(step_type="retrieve", action="search", source="code")
            )
            plan.add_step(
                ExecutionStep(step_type="reason", action="generate_architecture")
            )

        elif intent == Intent.TROUBLESHOOT:
            plan.add_step(
                ExecutionStep(step_type="retrieve", action="search", source="tickets")
            )
            plan.add_step(
                ExecutionStep(step_type="retrieve", action="search", source="telemetry")
            )
            plan.add_step(ExecutionStep(step_type="analyze", action="analyze_logs"))
            plan.add_step(ExecutionStep(step_type="reason", action="diagnose"))

        else:
            plan.add_step(
                ExecutionStep(step_type="retrieve", action="search", source="all")
            )

        for source in sources:
            plan.add_step(
                ExecutionStep(
                    step_type="retrieve",
                    action="search",
                    source=source,
                    params={"limit": 10},
                )
            )

        if tools:
            plan.add_step(
                ExecutionStep(
                    step_type="tool", action="execute_tools", params={"tools": tools}
                )
            )

        plan.add_step(ExecutionStep(step_type="reason", action="generate_answer"))

        for tool in tools:
            plan.add_tool(tool)

        return plan

    def get_retrieval_queries(self, query: str) -> Dict[str, List[str]]:
        """Generate retrieval queries based on query per protocol."""
        sources = self._identify_sources(query)
        intent = self._detect_intent(query)

        queries = {
            "docs_queries": [],
            "code_queries": [],
            "ticket_queries": [],
            "telemetry_queries": [],
        }

        if "docs" in sources:
            queries["docs_queries"].append(query)
            queries["docs_queries"].append(f"SAP BTP {query}")

        if "code" in sources:
            queries["code_queries"].append(query)
            queries["code_queries"].append(f"{query} implementation")

        if "tickets" in sources:
            queries["ticket_queries"].append(query)
            queries["ticket_queries"].append(f"{query} known issues")

        if "telemetry" in sources:
            queries["telemetry_queries"].append(query)
            queries["telemetry_queries"].append(f"{query} logs metrics")

        return queries


def get_planner_agent() -> PlannerAgent:
    return PlannerAgent()
