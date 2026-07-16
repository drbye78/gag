from pydantic import BaseModel, Field
from typing import List, Dict, Any, Callable, Optional
from enum import Enum


class RuleType(str, Enum):
    MANDATORY = "mandatory"
    RECOMMENDED = "recommended"
    PROHIBITED = "prohibited"


class RuleCondition(BaseModel):
    field: str = Field(...)
    operator: str = Field(...)
    value: Any = Field(...)


class RuleAction(BaseModel):
    type: str = Field(...)
    message: str = Field(...)
    fix_suggestion: Optional[str] = Field(None)


class ConstraintRule(BaseModel):
    id: str = Field(...)
    name: str = Field(...)
    description: str = Field("")
    type: RuleType = Field(...)
    conditions: List[RuleCondition] = Field(default_factory=list)
    action: RuleAction = Field(...)
    applies_to: List[str] = Field(default_factory=list)
    severity: str = Field("error")


class RuleResult(BaseModel):
    rule: ConstraintRule
    triggered: bool
    message: str
    fix: Optional[str] = None
    severity: str


class RuleEngine:
    def __init__(self):
        self.rules: Dict[str, ConstraintRule] = {}
    
    def add_rule(self, rule: ConstraintRule) -> None:
        self.rules[rule.id] = rule
    
    def evaluate(
        self,
        context: Dict[str, Any],
        scope: List[str]
    ) -> List[RuleResult]:
        results = []
        
        for rule_id, rule in self.rules.items():
            if scope and not any(s in rule.applies_to for s in scope):
                continue
            
            triggered = self._check_conditions(rule.conditions, context)
            
            if triggered:
                results.append(RuleResult(
                    rule=rule,
                    triggered=True,
                    message=rule.action.message,
                    fix=rule.action.fix_suggestion,
                    severity=rule.severity,
                ))
        
        return results
    
    def _check_conditions(
        self,
        conditions: List[RuleCondition],
        context: Dict[str, Any]
    ) -> bool:
        return all(self._evaluate_condition(c, context) for c in conditions)
    
    def _evaluate_condition(self, cond: RuleCondition, context: Dict[str, Any]) -> bool:
        value = self._get_nested(context, cond.field)
        
        if cond.operator == "eq":
            return value == cond.value
        elif cond.operator == "in":
            return value in cond.value
        elif cond.operator == "contains":
            return cond.value in str(value)
        elif cond.operator == "gt":
            return value is not None and value > cond.value
        elif cond.operator == "lt":
            return value is not None and value < cond.value
        
        return False
    
    def _get_nested(self, d: Dict, path: str) -> Any:
        keys = path.split(".")
        val = d
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return None
        return val


def get_rule_engine() -> RuleEngine:
    engine = RuleEngine()
    _load_default_rules(engine)
    return engine


def _load_default_rules(engine: RuleEngine) -> None:
    engine.add_rule(ConstraintRule(
        id="sap_xsuaa_required",
        name="XSUAA Required for SAP BTP",
        type=RuleType.MANDATORY,
        conditions=[
            RuleCondition(field="platform", operator="eq", value="sap"),
            RuleCondition(field="has_auth", operator="eq", value=False),
        ],
        action=RuleAction(
            type="error",
            message="SAP BTP requires authentication (XSUAA)",
            fix_suggestion="Add XSUAA service: cf create-service xsuaa default",
        ),
        applies_to=["sap"],
        severity="error",
    ))
    
    engine.add_rule(ConstraintRule(
        id="pp_dataverse_required",
        name="Dataverse Required",
        type=RuleType.MANDATORY,
        conditions=[
            RuleCondition(field="platform", operator="eq", value="powerplatform"),
            RuleCondition(field="has_database", operator="eq", value=False),
        ],
        action=RuleAction(
            type="error",
            message="Power Platform requires Dataverse",
            fix_suggestion="Use Dataverse for data storage",
        ),
        applies_to=["powerplatform"],
        severity="error",
    ))