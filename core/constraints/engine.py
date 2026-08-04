import logging
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


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
    constraint: Optional[Constraint] = None
    constraint_id: Optional[str] = None
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
        self._aws_registered: bool = False
    
    def register_constraint_set(self, constraint_set: ConstraintSet) -> None:
        self._constraint_sets[constraint_set.id] = constraint_set
        
        for constraint in constraint_set.constraints:
            for platform in constraint.platforms:
                if platform not in self._platform_index:
                    self._platform_index[platform] = []
                if constraint.id not in self._platform_index[platform]:
                    self._platform_index[platform].append(constraint.id)
    
    def evaluate(self, features: dict, platform: str) -> list[ConstraintViolation]:
        violations = []
        
        constraint_ids = self._platform_index.get(platform, [])
        
        # Deduplicate: evaluate each constraint set only once
        visited_sets: set[str] = set()
        for constraint_id in constraint_ids:
            constraint_set = self._get_constraint_set_for_id(constraint_id)
            if not constraint_set or constraint_set.id in visited_sets:
                continue
            visited_sets.add(constraint_set.id)
            
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
        elif op == "lte":
            violated = bool(actual) and actual <= expected
        elif op == "gte":
            violated = bool(actual) and actual >= expected
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
    
    # ── AWS platform constraint registration ──────────────────────────────
    
    def register_aws_constraints(self) -> None:
        """Register AWS platform constraints from YAML config.

        Loads the constraints.yaml for AWS from config/adapters/aws/ and
        registers service-specific limit constraints plus cross-service
        compatibility rules.  Idempotent — subsequent calls are no-ops.
        """
        if self._aws_registered:
            return

        config = self._load_aws_constraints_yaml()
        if not config:
            return

        constraints_config = config.get("constraints", {})

        for service_name, service_constraints in constraints_config.items():
            if service_name == "cross_service":
                continue

            constraint_objs: list[Constraint] = []

            # Lambda limits
            if service_name == "lambda":
                constraint_objs.extend([
                    Constraint(
                        id="aws_lambda_timeout_limit",
                        name="Lambda max timeout",
                        domain="aws",
                        type="limit",
                        feature="lambda_timeout",
                        operator="gt",
                        threshold=service_constraints.get("max_timeout_seconds", 900),
                        message=f"AWS Lambda timeout exceeds maximum of {service_constraints.get('max_timeout_seconds', 900)}s",
                        fix_hint="Reduce timeout to ≤900s or use AWS Step Functions for long-running workflows",
                        severity="error",
                        platforms=["aws"],
                    ),
                    Constraint(
                        id="aws_lambda_memory_limit",
                        name="Lambda max memory",
                        domain="aws",
                        type="limit",
                        feature="lambda_memory",
                        operator="gt",
                        threshold=service_constraints.get("max_memory_mb", 10240),
                        message=f"AWS Lambda memory exceeds maximum of {service_constraints.get('max_memory_mb', 10240)} MB",
                        fix_hint="Reduce memory allocation to ≤10240 MB or use ECS/EKS for high-memory workloads",
                        severity="error",
                        platforms=["aws"],
                    ),
                    Constraint(
                        id="aws_lambda_ephemeral_storage",
                        name="Lambda max ephemeral storage",
                        domain="aws",
                        type="limit",
                        feature="lambda_ephemeral_storage",
                        operator="gt",
                        threshold=service_constraints.get("max_ephemeral_storage_mb", 10240),
                        message=f"AWS Lambda ephemeral storage exceeds maximum of {service_constraints.get('max_ephemeral_storage_mb', 10240)} MB",
                        fix_hint="Reduce ephemeral storage or use EFS for additional storage",
                        severity="error",
                        platforms=["aws"],
                    ),
                    Constraint(
                        id="aws_lambda_concurrent_exec",
                        name="Lambda max concurrent executions",
                        domain="aws",
                        type="limit",
                        feature="lambda_concurrent_executions",
                        operator="gt",
                        threshold=service_constraints.get("max_concurrent_executions", 1000),
                        message=f"AWS Lambda concurrent executions exceed default limit of {service_constraints.get('max_concurrent_executions', 1000)}",
                        fix_hint="Request quota increase or use throttling/queuing",
                        severity="warning",
                        platforms=["aws"],
                    ),
                ])

            # DynamoDB limits
            elif service_name == "dynamodb":
                constraint_objs.extend([
                    Constraint(
                        id="aws_dynamodb_item_size",
                        name="DynamoDB max item size",
                        domain="aws",
                        type="limit",
                        feature="dynamodb_item_size",
                        operator="gt",
                        threshold=service_constraints.get("max_item_size_bytes", 409600),
                        message=f"DynamoDB item size exceeds maximum of {service_constraints.get('max_item_size_bytes', 409600)} bytes (400 KB)",
                        fix_hint="Split large items or use S3 for oversized payloads with key reference",
                        severity="error",
                        platforms=["aws"],
                    ),
                ])

            # ECS Fargate limits
            elif service_name == "ecs_fargate":
                constraint_objs.extend([
                    Constraint(
                        id="aws_fargate_cpu_limit",
                        name="Fargate max vCPU",
                        domain="aws",
                        type="limit",
                        feature="fargate_cpu",
                        operator="gt",
                        threshold=service_constraints.get("max_cpu_units", 16384),
                        message=f"ECS Fargate CPU exceeds maximum of {service_constraints.get('max_cpu_units', 16384)} units (16 vCPU)",
                        fix_hint="Reduce CPU or use EC2 launch type for larger instances",
                        severity="error",
                        platforms=["aws"],
                    ),
                    Constraint(
                        id="aws_fargate_memory_limit",
                        name="Fargate max memory",
                        domain="aws",
                        type="limit",
                        feature="fargate_memory",
                        operator="gt",
                        threshold=service_constraints.get("max_memory_mb", 122880),
                        message=f"ECS Fargate memory exceeds maximum of {service_constraints.get('max_memory_mb', 122880)} MB (120 GB)",
                        fix_hint="Reduce memory or use EC2 launch type for larger instances",
                        severity="error",
                        platforms=["aws"],
                    ),
                ])

            # API Gateway limits
            elif service_name == "api_gateway":
                constraint_objs.extend([
                    Constraint(
                        id="aws_apigw_timeout",
                        name="API Gateway max integration timeout",
                        domain="aws",
                        type="limit",
                        feature="api_gateway_timeout_ms",
                        operator="gt",
                        threshold=service_constraints.get("max_timeout_ms", 29000),
                        message=f"API Gateway integration timeout exceeds maximum of {service_constraints.get('max_timeout_ms', 29000)} ms (29 seconds)",
                        fix_hint="Use asynchronous invocation pattern or WebSocket APIs for long-running requests",
                        severity="error",
                        platforms=["aws"],
                    ),
                ])

            # S3 limits
            elif service_name == "s3":
                constraint_objs.extend([
                    Constraint(
                        id="aws_s3_object_size",
                        name="S3 max object size",
                        domain="aws",
                        type="limit",
                        feature="s3_object_size",
                        operator="gt",
                        threshold=service_constraints.get("max_object_size_bytes", 5497558138880),
                        message=f"S3 object size exceeds maximum of {service_constraints.get('max_object_size_bytes', 5497558138880)} bytes (5 TB)",
                        fix_hint="Use multipart upload for large objects",
                        severity="error",
                        platforms=["aws"],
                    ),
                ])

            # Step Functions limits
            elif service_name == "step_functions":
                constraint_objs.extend([
                    Constraint(
                        id="aws_sfn_express_timeout",
                        name="Step Functions Express max execution",
                        domain="aws",
                        type="limit",
                        feature="step_functions_timeout_seconds",
                        operator="gt",
                        threshold=service_constraints.get("express_max_execution_seconds", 300),
                        message=f"AWS Step Functions Express execution exceeds maximum of {service_constraints.get('express_max_execution_seconds', 300)} seconds (5 minutes)",
                        fix_hint="Use Standard workflow type for long-running executions",
                        severity="error",
                        platforms=["aws"],
                    ),
                ])

            if constraint_objs:
                self.register_constraint_set(ConstraintSet(
                    id=f"aws_{service_name}_limits",
                    name=f"AWS {service_name.upper()} limits",
                    description=f"Service limits for AWS {service_name}",
                    constraints=constraint_objs,
                ))

        self._aws_registered = True

    def _load_aws_constraints_yaml(self) -> dict:
        """Load AWS constraints from YAML config file.

        Uses the AdapterConfigLoader if available, falling back to direct
        yaml read for environments that don't import the adapter layer.
        """
        try:
            from core.adapters.config_loader import get_config_loader
            loader = get_config_loader()
            return loader.load_constraints("aws")
        except ImportError:
            pass

        # Fallback: direct YAML read
        config_path = Path("config/adapters/aws/constraints.yaml")
        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f)
                return data or {}
        return {}

    def _load_platform_constraints_yaml(self, platform: str) -> dict:
        """Load platform constraints from YAML config file.

        Uses the AdapterConfigLoader if available, falling back to direct
        yaml read for environments that don't import the adapter layer.
        """
        try:
            from core.adapters.config_loader import get_config_loader
            loader = get_config_loader()
            return loader.load_constraints(platform)
        except ImportError:
            pass

        # Fallback: direct YAML read
        config_path = Path(f"config/adapters/{platform}/constraints.yaml")
        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f)
                return data or {}
        return {}

    # ── Cross-service compatibility validation ────────────────────────────
    
    def validate_cross_service_compatibility(
        self, features: dict, platform: str = "aws"
    ) -> list[ConstraintViolation]:
        """Check cross-service compatibility rules for the given platform.

        Evaluates rules from the YAML config's cross_service section:
        - incompatible_combinations: services that cannot coexist without conditions
        - recommended_combinations: informational pairings (not enforced as violations)

        Args:
            features: Dict of feature flags and values (e.g. IRFeature.model_dump())
            platform: Platform identifier ('aws', 'azure', 'gcp')

        Returns:
            List of ConstraintViolation objects for incompatible combinations found.
        """
        violations = []
        config = self._load_platform_constraints_yaml(platform)
        if not config:
            return violations

        cross_service = config.get("constraints", {}).get("cross_service", {})
        incompatible = cross_service.get("incompatible_combinations", [])

        for combo in incompatible:
            services = combo.get("services", [])
            condition = combo.get("condition", "")
            message = combo.get("message", "")

            if not services or not message:
                continue

            if not self._services_present(features, services):
                continue

            if self._condition_met(features, condition, services):
                violations.append(ConstraintViolation(
                    constraint_id=f"cross_service_{services[0]}_{services[1]}",
                    actual_value=condition,
                    expected_value=None,
                    severity="error",
                    message=message,
                    fix_hint="Review service compatibility: ensure required conditions are met",
                ))

        return violations

    def _services_present(self, features: dict, services: list[str]) -> bool:
        """Check if the listed services are present in the feature set."""
        service_flags = {
            "lambda": "has_serverless",
            "efs": "uses_external_services",
            "rds_proxy": "uses_external_services",
            "apigateway": "has_api",
            "functions": "has_serverless",
            "aks": "has_container",
            "cosmos_db": "has_database",
            "cloud_functions": "has_serverless",
            "cloud_run": "has_container",
            "gke": "has_container",
            "firestore": "has_database",
            "pubsub": "has_event_driven",
        }
        for svc in services:
            flag = service_flags.get(svc, f"has_{svc}")
            if not features.get(flag) and svc not in str(features.get("uses_external_services", [])).lower():
                # Check via uses_external_services list
                external_services = features.get("uses_external_services", [])
                if isinstance(external_services, list) and svc in external_services:
                    continue
                # Also check boolean flag
                if not features.get(flag):
                    return False
        return True

    def _condition_met(self, features: dict, condition: str, services: list[str]) -> bool:
        """Evaluate whether a named condition is met in the features dict."""
        conditions = {
            "no_vpc_config": lambda f: not f.get("uses_external_services") 
                                       or "vpc" not in str(f.get("uses_external_services", [])).lower(),
            "timeout_gt_29000": lambda f: f.get("lambda_timeout", 0) > 29 
                                          or f.get("api_gateway_timeout_ms", 0) > 29000,
            "direct_integration": lambda f: True,  # Always met when both services are present
        }
        checker = conditions.get(condition)
        if checker:
            return checker(features)
        return False


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
    
    # Register platform constraints from YAML configs (AWS limits, cross-service rules, etc.)
    try:
        engine.register_aws_constraints()
    except Exception as e:
        logger.debug("Failed to register AWS constraints: %s", e)