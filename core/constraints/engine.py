from pydantic import BaseModel, Field
from typing import Any, Optional


class Constraint(BaseModel):
    id: str
    name: str
    domain: str
    
    type: str
    feature: str
    operator: str
    threshold: Any
    
    message: str
    fix_hint: str
    severity: str = "error"
    
    platforms: list[str] = []
    min_confidence: float = 0.0


class ConstraintViolation(BaseModel):
    constraint: Constraint
    actual_value: Any
    expected_value: Any
    severity: str
    message: str
    fix_hint: str


class ConstraintSet(BaseModel):
    id: str
    name: str
    description: str
    constraints: list[Constraint]


class ConstraintEngine:
    def __init__(self):
        self._constraint_sets: dict[str, ConstraintSet] = {}
        self._platform_index: dict[str, list[str]] = {}
    
    def register_constraint_set(self, constraint_set: ConstraintSet) -> None:
        self._constraint_sets[constraint_set.id] = constraint_set
        
        for constraint in constraint_set.constraints:
            for platform in constraint.platforms:
                if platform not in self._platform_index:
                    self._platform_index[platform] = []
                self._platform_index[platform].append(constraint.id)
    
    def evaluate(self, features: dict, platform: str) -> list[ConstraintViolation]:
        violations = []
        
        constraint_ids = self._platform_index.get(platform, [])
        
        for constraint_id in constraint_ids:
            constraint_set = self._get_constraint_set_for_id(constraint_id)
            if not constraint_set:
                continue
            
            for constraint in constraint_set.constraints:
                violation = self._evaluate_constraint(constraint, features)
                if violation:
                    violations.append(violation)
        
        return violations
    
    def _get_constraint_set_for_id(self, constraint_id: str) -> Optional[ConstraintSet]:
        for cs in self._constraint_sets.values():
            if any(c.id == constraint_id for c in cs.constraints):
                return cs
        return None
    
    def _evaluate_constraint(self, constraint: Constraint, features: dict) -> Optional[ConstraintViolation]:
        actual = features.get(constraint.feature)
        if actual is None:
            return None
        
        op = constraint.operator
        expected = constraint.threshold
        violated = False
        
        if op == "eq":
            violated = actual != expected
        elif op == "ne":
            violated = actual == expected
        elif op == "gt":
            violated = bool(actual) and actual > expected
        elif op == "lt":
            violated = bool(actual) and actual < expected
        elif op == "required":
            violated = not actual
        
        if violated:
            return ConstraintViolation(
                constraint=constraint,
                actual_value=actual,
                expected_value=expected,
                severity=constraint.severity,
                message=constraint.message,
                fix_hint=constraint.fix_hint,
            )
        
        return None
    
    def apply_fix(self, features: dict, violation: ConstraintViolation) -> dict:
        constraint = violation.constraint
        feature = constraint.feature
        
        if constraint.domain == "security" and constraint.feature == "has_auth":
            features["has_auth"] = True
        
        return features


_constraint_engine: Optional[ConstraintEngine] = None


def get_constraint_engine() -> ConstraintEngine:
    global _constraint_engine
    if _constraint_engine is None:
        _constraint_engine = ConstraintEngine()
        _load_default_constraints(_constraint_engine)
    return _constraint_engine


def _load_default_constraints(engine: ConstraintEngine) -> None:
    sap_constraints = ConstraintSet(
        id="sap_btp",
        name="SAP BTP Constraints",
        description="Platform-specific constraints for SAP Business Technology Platform",
        constraints=[
            Constraint(
                id="sap_xsuaa_required",
                name="XSUAA Required",
                domain="security",
                type="hard",
                feature="has_auth",
                operator="eq",
                threshold=True,
                message="SAP BTP applications require authentication (XSUAA)",
                fix_hint="Add XSUAA service: cf create-service xsuaa default -p xsuaa.json",
                severity="error",
                platforms=["sap"],
            ),
            Constraint(
                id="sap_multi_tenant_ias",
                name="Multi-tenant requires IAS",
                domain="compliance",
                type="soft",
                feature="multi_tenant",
                operator="eq",
                threshold=True,
                message="Multi-tenant SAP apps should use Identity Authentication service",
                fix_hint="Use IAS for multi-tenant: cf create-service identity default",
                severity="warning",
                platforms=["sap"],
            ),
            Constraint(
                id="sap_encryption",
                name="Data Encryption Required",
                domain="security",
                type="hard",
                feature="encryption_required",
                operator="eq",
                threshold=True,
                message="Sensitive data requires encryption at rest",
                fix_hint="Enable encryption in HDI container or use SAP HANA Cloud encryption",
                severity="error",
                platforms=["sap"],
            ),
        ],
    )
    
    salesforce_constraints = ConstraintSet(
        id="salesforce",
        name="Salesforce Constraints",
        description="Platform-specific constraints for Salesforce",
        constraints=[
            Constraint(
                id="sf_auth_required",
                name="OAuth Required",
                domain="security",
                type="hard",
                feature="has_auth",
                operator="eq",
                threshold=True,
                message="Salesforce integrations require OAuth 2.0",
                fix_hint="Implement OAuth 2.0 flow with connected app",
                severity="error",
                platforms=["salesforce"],
            ),
        ],
    )
    
    powerplatform_constraints = ConstraintSet(
        id="powerplatform",
        name="Power Platform Constraints",
        description="Platform-specific constraints for Microsoft Power Platform",
        constraints=[
            Constraint(
                id="pp_dataverse_required",
                name="Dataverse Required",
                domain="data",
                type="hard",
                feature="has_database",
                operator="eq",
                threshold=True,
                message="Power Platform solutions require Dataverse",
                fix_hint="Use Dataverse for data storage in Power Apps",
                severity="error",
                platforms=["powerplatform"],
            ),
        ],
    )
    
    engine.register_constraint_set(sap_constraints)
    engine.register_constraint_set(salesforce_constraints)
    engine.register_constraint_set(powerplatform_constraints)
    
    tanzu_constraints = ConstraintSet(
        id="tanzu",
        name="VMware Tanzu Constraints",
        description="Platform-specific constraints for VMware Tanzu",
        constraints=[
            Constraint(
                id="tanzu_service_account",
                name="Service Account Required",
                domain="security",
                type="hard",
                feature="has_auth",
                operator="eq",
                threshold=True,
                message="Tanzu applications should use service accounts",
                fix_hint="Configure service account: kubectl create serviceaccount my-sa",
                severity="warning",
                platforms=["tanzu"],
            ),
            Constraint(
                id="tanzu_resource_limits",
                name="Resource Limits Required",
                domain="performance",
                type="soft",
                feature="scalability_required",
                operator="eq",
                threshold=True,
                message="Production Tanzu workloads should have resource limits",
                fix_hint="Add resources.limits to container spec",
                severity="warning",
                platforms=["tanzu"],
            ),
        ],
    )
    
    engine.register_constraint_set(tanzu_constraints)