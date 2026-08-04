from typing import Any, Dict, List
from core.adapters.base import AdapterInput, AdapterOutput, PlatformAdapter
from core.patterns.schema import Pattern, get_pattern_library
from core.constraints.engine import get_constraint_engine, Constraint, ConstraintSet
from models.ir import IRFeature, PlatformContext


class AWSAdapter(PlatformAdapter):
    def __init__(self):
        super().__init__()
        self._config_loader = None
    
    def _get_config_loader(self):
        if self._config_loader is None:
            from core.adapters.config_loader import get_config_loader
            self._config_loader = get_config_loader()
        return self._config_loader
    
    @property
    def platform_id(self) -> str:
        return "aws"
    
    @property
    def supported_services(self) -> List[str]:
        """Load services from YAML config if available, else use defaults."""
        loader = self._get_config_loader()
        services = loader.load_services("aws")
        if services:
            # Flatten categorized services into flat list
            result = []
            for category_services in services.values():
                result.extend(category_services)
            return sorted(set(result))
        # Fallback to defaults
        return [
            "lambda",
            "ec2",
            "ecs",
            "eks",
            "s3",
            "dynamodb",
            "rds",
            "iam",
            "api-gateway",
            "cloudfront",
            "sns",
            "sqs",
            "eventbridge",
        ]
    
    @property
    def patterns(self) -> List[Pattern]:
        return [
            Pattern(
                id="aws_lambda",
                name="AWS Lambda Function",
                domain="serverless",
                triggers=["lambda", "serverless", "function"],
                conditions=[],
                components=["lambda"],
                benefits=["Pay per request", "Auto-scale", "No server management"],
                tradeoffs=["Cold starts", "Vendor lock-in"],
                priority=9,
                confidence=0.9,
            ),
            Pattern(
                id="aws_ecs_fargate",
                name="ECS Fargate Container",
                domain="container",
                triggers=["container", "docker", "ecs"],
                conditions=[],
                components=["ecs", "fargate"],
                benefits=["Managed containers", "Pay per use"],
                tradeoffs=["Complexity"],
                priority=8,
                confidence=0.85,
            ),
            Pattern(
                id="aws_lambda_api",
                name="Lambda API Gateway",
                domain="api",
                triggers=["api", "rest", "endpoint"],
                conditions=[],
                components=["api-gateway", "lambda"],
                benefits=["Quick APIs", "Low cost"],
                tradeoffs=["Timeouts"],
                priority=8,
                confidence=0.85,
            ),
            Pattern(
                id="aws_eventbridge",
                name="EventBridge Event Bus",
                domain="event-driven",
                triggers=["event", "eventbus", "pub-sub"],
                conditions=[],
                components=["eventbridge"],
                benefits=["Decoupled", "Reactive"],
                tradeoffs=["Learning curve"],
                priority=7,
                confidence=0.8,
            ),
            Pattern(
                id="aws_dynamodb",
                name="DynamoDB NoSQL",
                domain="database",
                triggers=["nosql", "dynamo", "key-value"],
                conditions=[],
                components=["dynamodb"],
                benefits=["Managed", "Fast", "Scalable"],
                tradeoffs=["Cost at scale"],
                priority=8,
                confidence=0.85,
            ),
        ]
    
    @property
    def constraints(self) -> List[Constraint]:
        return [
            Constraint(
                id="aws_lambda_timeout",
                name="Lambda timeout 15min",
                domain="serverless",
                type="limit",
                feature="timeout",
                operator="lte",
                threshold=900,
                message="Lambda timeout cannot exceed 900 seconds",
                fix_hint="Use Step Functions for longer workflows",
                severity="error",
                platforms=["aws"],
            ),
            Constraint(
                id="aws_lambda_memory",
                name="Lambda memory max 10GB",
                domain="serverless",
                type="limit",
                feature="memory",
                operator="lte",
                threshold=10240,
                message="Lambda memory cannot exceed 10240 MB",
                fix_hint="Use ECS for high-memory workloads",
                severity="error",
                platforms=["aws"],
            ),
        ]
    
    def transform_ir_to_platform(self, input: AdapterInput) -> AdapterOutput:
        features = input.ir_features
        pattern_results = input.pattern_matches
        violations = list(input.constraint_violations)
        
        configs = self.generate_config(features)
        code = self.generate_code(features)
        terraform = self.generate_terraform(features)
        
        # ── Deep platform constraint validation ──────────────────────────
        engine = get_constraint_engine()
        
        # Register AWS-specific constraints (idempotent)
        try:
            engine.register_aws_constraints()
        except Exception:
            pass
        
        # Evaluate feature set against AWS service limits
        feature_dict = features.model_dump()
        platform_violations = engine.evaluate(feature_dict, "aws")
        violations.extend(platform_violations)
        
        # Evaluate cross-service compatibility rules
        cross_service_violations = engine.validate_cross_service_compatibility(
            feature_dict, platform="aws"
        )
        violations.extend(cross_service_violations)
        # ─────────────────────────────────────────────────────────────────
        
        recommendations = self._build_recommendations(pattern_results, features, violations)
        
        can_deploy = not any(v.severity == "error" for v in violations)
        
        confidence = (
            sum(p.match_score for p in pattern_results) / max(1, len(pattern_results))
            if pattern_results else 0.7
        )
        
        # Attach all violations to metadata for downstream consumers
        violation_dicts = []
        for v in violations:
            if hasattr(v, "model_dump"):
                violation_dicts.append(v.model_dump())
            elif hasattr(v, "__dict__"):
                violation_dicts.append({
                    "message": getattr(v, "message", str(v)),
                    "severity": getattr(v, "severity", "error"),
                    "fix_hint": getattr(v, "fix_hint", ""),
                })
        
        return AdapterOutput(
            recommendations=recommendations,
            config_templates=configs,
            code_snippets=code,
            terraform=terraform,
            platform=self.platform_id,
            confidence=confidence,
            can_deploy=can_deploy,
            metadata={"constraint_violations": violation_dicts},
        )
    
    def _build_recommendations(
        self,
        patterns: List[Any],
        features: IRFeature,
        violations: List[Any],
    ) -> List[Dict[str, Any]]:
        recs = []
        
        if patterns:
            for p in patterns:
                recs.append({
                    "name": p.pattern_id,
                    "reason": f"Matched pattern {p.pattern_id} with score {p.match_score:.2f}",
                    "priority": p.priority,
                })
        
        if features.has_serverless:
            recs.append({
                "name": "aws_lambda",
                "reason": "Features indicate serverless requirement",
                "priority": 9,
            })
        
        if features.has_container:
            recs.append({
                "name": "aws_ecs_fargate",
                "reason": "Features indicate container requirement",
                "priority": 8,
            })
        
        if violations:
            for v in violations:
                if v.severity == "warning":
                    recs.append({
                        "name": "constraint_warning",
                        "reason": v.message,
                        "priority": 5,
                    })
        
        return recs
    
    def generate_config(self, features: IRFeature) -> Dict[str, str]:
        configs = {}
        
        if features.has_serverless:
            configs["serverless.yml"] = '''service: my-service
provider:
  name: aws
  runtime: python3.12

functions:
  hello:
    handler: handler.hello
    events:
      - http:
          path: hello
          method: get'''
        
        if features.has_container:
            configs["ecs-task-definition.json"] = '''{
  "family": "my-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512"
}'''
        
        return configs
    
    def generate_code(self, features: IRFeature) -> Dict[str, str]:
        code = {}
        
        if features.has_serverless:
            code["handler.py"] = '''def handler(event, context):
    return {
        "statusCode": 200,
        "body": "Hello from Lambda"
    }'''
        
        return code
    
    # ── Bidirectional Import ──────────────────────────────────────────
    
    def import_from_terraform(self, state_file: dict) -> Dict[str, Any]:
        """Parse Terraform state JSON into generic Intermediate Representation.
        
        Args:
            state_file: A Terraform state dict (from `terraform show -json`)
            
        Returns:
            Dict with nodes (resources) and edges (relationships/dependencies)
        """
        ir_nodes = []
        ir_edges = []
        
        resources = state_file.get("resources", [])
        
        for resource in resources:
            resource_type = resource.get("type", "")
            resource_name = resource.get("name", "")
            instances = resource.get("instances", [])
            
            if not instances:
                continue
            
            instance = instances[0]
            attributes = instance.get("attributes", {})
            
            # Map Terraform resource types to IR node types
            node_mapping = {
                "aws_lambda_function": {"type": "Function", "platform_type": "lambda"},
                "aws_dynamodb_table": {"type": "Database", "platform_type": "dynamodb"},
                "aws_s3_bucket": {"type": "Storage", "platform_type": "s3"},
                "aws_api_gateway_rest_api": {"type": "APIGateway", "platform_type": "api-gateway"},
                "aws_ecs_service": {"type": "Container", "platform_type": "ecs"},
                "aws_ecs_task_definition": {"type": "ContainerTask", "platform_type": "ecs"},
                "aws_cloudfront_distribution": {"type": "CDN", "platform_type": "cloudfront"},
                "aws_iam_role": {"type": "IAMRole", "platform_type": "iam"},
                "aws_sns_topic": {"type": "Messaging", "platform_type": "sns"},
                "aws_sqs_queue": {"type": "Queue", "platform_type": "sqs"},
                "aws_cloudwatch_event_rule": {"type": "EventBus", "platform_type": "eventbridge"},
                "aws_cloudwatch_log_group": {"type": "Logging", "platform_type": "cloudwatch"},
                "aws_elasticache_cluster": {"type": "Cache", "platform_type": "elasticache"},
                "aws_rds_cluster": {"type": "Database", "platform_type": "rds"},
            }
            
            mapping = node_mapping.get(resource_type, {"type": "Resource", "platform_type": resource_type})
            
            # Extract common properties
            arn = attributes.get("arn", "")
            region = arn.split(":")[3] if ":" in arn else "us-east-1"
            
            properties = self._extract_terraform_properties(resource_type, attributes)
            
            ir_node = {
                "id": resource_name,
                "type": mapping["type"],
                "platform_type": mapping["platform_type"],
                "properties": properties,
                "region": region,
                "source": "terraform",
            }
            ir_nodes.append(ir_node)
        
        # Infer edges from Terraform dependencies and attributes
        for resource in resources:
            resource_name = resource.get("name", "")
            instances = resource.get("instances", [])
            if not instances:
                continue
            
            instance = instances[0]
            attributes = instance.get("attributes", {})
            
            # Dependencies from Terraform 'depends_on'
            for dep in resource.get("depends_on", []):
                ir_edges.append({
                    "source": dep,
                    "target": resource_name,
                    "type": "DEPENDS_ON",
                    "source_type": "terraform",
                })
            
            # Implicit relationships from attributes (e.g., role_arn → IAM role)
            for attr_name, attr_value in attributes.items():
                if attr_name.endswith("_arn") and isinstance(attr_value, str) and ":lambda:" not in attr_value:
                    # Find matching IAM role
                    for node in ir_nodes:
                        if node["type"] == "IAMRole" and node["id"] in attr_value:
                            ir_edges.append({
                                "source": node["id"],
                                "target": resource_name,
                                "type": "USES",
                                "source_type": "inferred",
                            })
        
        return {
            "nodes": ir_nodes,
            "edges": ir_edges,
            "node_count": len(ir_nodes),
            "edge_count": len(ir_edges),
            "source": "terraform_import",
        }
    
    def _extract_terraform_properties(self, resource_type: str, attributes: dict) -> dict:
        """Extract relevant properties from Terraform resource attributes."""
        props = {}
        
        if resource_type == "aws_lambda_function":
            props["runtime"] = attributes.get("runtime", "")
            props["memory_size"] = attributes.get("memory_size", 128)
            props["timeout"] = attributes.get("timeout", 3)
            props["handler"] = attributes.get("handler", "")
            props["architectures"] = attributes.get("architectures", ["x86_64"])
        
        elif resource_type == "aws_dynamodb_table":
            props["billing_mode"] = attributes.get("billing_mode", "PROVISIONED")
            props["hash_key"] = attributes.get("hash_key", "")
            props["range_key"] = attributes.get("range_key", "")
            read_cap = attributes.get("read_capacity", 5)
            write_cap = attributes.get("write_capacity", 5)
            props["read_capacity"] = read_cap
            props["write_capacity"] = write_cap
        
        elif resource_type == "aws_s3_bucket":
            props["bucket"] = attributes.get("bucket", "")
            props["acl"] = attributes.get("acl", "private")
            versioning = attributes.get("versioning", [{}])
            props["versioning_enabled"] = versioning[0].get("enabled", False) if versioning else False
        
        elif resource_type == "aws_ecs_service":
            props["launch_type"] = attributes.get("launch_type", "FARGATE")
            props["desired_count"] = attributes.get("desired_count", 1)
            props["cpu"] = attributes.get("cpu", "256")
            props["memory"] = attributes.get("memory", "512")
        
        elif resource_type == "aws_api_gateway_rest_api":
            props["name"] = attributes.get("name", "")
            props["description"] = attributes.get("description", "")
            endpoint_types = attributes.get("endpoint_configuration", [{}])
            props["endpoint_type"] = endpoint_types[0].get("types", []) if endpoint_types else []
        
        return props
    
    # ── Terraform HCL Generation ─────────────────────────────────────
    
    def generate_terraform(self, features: IRFeature) -> str:
        """Generate production-quality Terraform HCL from IR features.
        
        Uses official Terraform AWS modules with proper versioning and tagging.
        """
        modules = []
        
        # Terraform backend and provider block
        modules.append('''terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      ManagedBy = "gag"
      Generated = "true"
    }
  }
}''')
        
        # Lambda function module
        if features.has_serverless:
            modules.append('''module "lambda_function" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 7.0"

  function_name = var.function_name
  description   = "Generated by Engineering Intelligence System"
  runtime       = var.lambda_runtime
  handler       = var.lambda_handler
  memory_size   = var.lambda_memory
  timeout       = var.lambda_timeout

  source_path = var.lambda_source_path

  environment_variables = var.lambda_env_vars

  tags = var.tags
}''')
        
        # DynamoDB table
        if features.has_database:
            modules.append('''module "dynamodb_table" {
  source  = "terraform-aws-modules/dynamodb-table/aws"
  version = "~> 4.0"

  name     = var.table_name
  hash_key = var.hash_key

  billing_mode = var.billing_mode
  
  attributes = var.dynamodb_attributes

  tags = var.tags
}''')
        
        # S3 bucket — triggered by has_database (storage often implied) or has_serverless
        if features.has_database or features.has_serverless:
            modules.append('''module "s3_bucket" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "~> 4.0"

  bucket = var.bucket_name
  acl    = var.bucket_acl

  versioning = {
    enabled = var.enable_versioning
  }

  tags = var.tags
}''')
        
        if modules:
            modules.append(self._terraform_variables())
        
        return "\n".join(modules)
    
    def _terraform_variables(self) -> str:
        """Generate Terraform variables block for all module variables."""
        return '''variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "function_name" {
  description = "Lambda function name"
  type        = string
}

variable "lambda_runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.12"
}

variable "lambda_handler" {
  description = "Lambda handler"
  type        = string
  default     = "index.handler"
}

variable "lambda_memory" {
  description = "Lambda memory in MB"
  type        = number
  default     = 128
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 3
}

variable "lambda_source_path" {
  description = "Path to Lambda source code"
  type        = string
}

variable "lambda_env_vars" {
  description = "Lambda environment variables"
  type        = map(string)
  default     = {}
}

variable "table_name" {
  description = "DynamoDB table name"
  type        = string
  default     = ""
}

variable "hash_key" {
  description = "DynamoDB hash key"
  type        = string
  default     = "id"
}

variable "billing_mode" {
  description = "DynamoDB billing mode"
  type        = string
  default     = "PAY_PER_REQUEST"
}

variable "dynamodb_attributes" {
  description = "DynamoDB attributes"
  type        = list(object({
    name = string
    type = string
  }))
  default     = []
}

variable "bucket_name" {
  description = "S3 bucket name"
  type        = string
  default     = ""
}

variable "bucket_acl" {
  description = "S3 bucket ACL"
  type        = string
  default     = "private"
}

variable "enable_versioning" {
  description = "Enable S3 versioning"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}'''

class AzureAdapter(PlatformAdapter):
    def __init__(self):
        super().__init__()
        self._config_loader = None
    
    def _get_config_loader(self):
        if self._config_loader is None:
            from core.adapters.config_loader import get_config_loader
            self._config_loader = get_config_loader()
        return self._config_loader
    
    @property
    def platform_id(self) -> str:
        return "azure"
    
    @property
    def supported_services(self) -> List[str]:
        """Load services from YAML config if available, else use defaults."""
        loader = self._get_config_loader()
        services = loader.load_services("azure")
        if services:
            result = []
            for category_services in services.values():
                result.extend(category_services)
            return sorted(set(result))
        # Fallback to defaults
        return [
            "functions",
            "app-service",
            "aks",
            "cosmos-db",
            "storage",
            "key-vault",
            "api-management",
            "event-hub",
            "service-bus",
            "logic-apps",
            "ad",
            "entra-id",
        ]
    
    @property
    def patterns(self) -> List[Pattern]:
        return [
            Pattern(
                id="azure_functions",
                name="Azure Functions",
                domain="serverless",
                triggers=["function", "serverless", "azure"],
                conditions=[],
                components=["functions"],
                benefits=["Pay per execution", "Auto-scale"],
                tradeoffs=["Vendor lock-in"],
                priority=9,
                confidence=0.9,
            ),
            Pattern(
                id="azure_aks",
                name="Azure Kubernetes Service",
                domain="container",
                triggers=["kubernetes", "k8s", "aks"],
                conditions=[],
                components=["aks"],
                benefits=["Managed K8s", "Enterprise ready"],
                tradeoffs=["Complexity"],
                priority=8,
                confidence=0.85,
            ),
            Pattern(
                id="azure_cosmosdb",
                name="Cosmos DB",
                domain="database",
                triggers=["nosql", "cosmos", "mongodb"],
                conditions=[],
                components=["cosmos-db"],
                benefits=["Global distribution", "SLA"],
                tradeoffs=["Cost at scale"],
                priority=8,
                confidence=0.8,
            ),
            Pattern(
                id="azure_eventhub",
                name="Event Hubs",
                domain="event-driven",
                triggers=["event", "streaming", "eventhub"],
                conditions=[],
                components=["event-hub"],
                benefits=["Throughput", "Real-time"],
                tradeoffs=["Learning curve"],
                priority=7,
                confidence=0.8,
            ),
        ]
    
    @property
    def constraints(self) -> List[Constraint]:
        return [
            Constraint(
                id="azure_functions_timeout",
                name="Functions timeout 10min",
                domain="serverless",
                type="limit",
                feature="timeout",
                operator="lte",
                threshold=600,
                message="Functions timeout cannot exceed 600 seconds",
                fix_hint="Use Durable Functions for longer workflows",
                severity="error",
                platforms=["azure"],
            ),
            Constraint(
                id="azure_functions_scale",
                name="Functions scale limit",
                domain="serverless",
                type="limit",
                feature="instances",
                operator="lte",
                threshold=200,
                message="Functions scale limit is 200 instances",
                fix_hint="Contact support for higher limits",
                severity="warning",
                platforms=["azure"],
            ),
        ]
    
    def transform_ir_to_platform(self, input: AdapterInput) -> AdapterOutput:
        features = input.ir_features
        pattern_results = input.pattern_matches
        violations = list(input.constraint_violations)
        
        configs = self.generate_config(features)
        code = self.generate_code(features)
        terraform = self.generate_terraform(features)
        
        # ── Deep platform constraint validation ──────────────────────────
        engine = get_constraint_engine()
        
        # Evaluate feature set against Azure service limits
        feature_dict = features.model_dump()
        platform_violations = engine.evaluate(feature_dict, "azure")
        violations.extend(platform_violations)
        
        # Evaluate cross-service compatibility rules
        cross_service_violations = engine.validate_cross_service_compatibility(
            feature_dict, platform="azure"
        )
        violations.extend(cross_service_violations)
        # ─────────────────────────────────────────────────────────────────
        
        recommendations = self._build_recommendations(pattern_results, features, violations)
        
        can_deploy = not any(v.severity == "error" for v in violations)
        
        confidence = (
            sum(p.match_score for p in pattern_results) / max(1, len(pattern_results))
            if pattern_results else 0.7
        )
        
        # Attach all violations to metadata for downstream consumers
        violation_dicts = []
        for v in violations:
            if hasattr(v, "model_dump"):
                violation_dicts.append(v.model_dump())
            elif hasattr(v, "__dict__"):
                violation_dicts.append({
                    "message": getattr(v, "message", str(v)),
                    "severity": getattr(v, "severity", "error"),
                    "fix_hint": getattr(v, "fix_hint", ""),
                })
        
        return AdapterOutput(
            recommendations=recommendations,
            config_templates=configs,
            code_snippets=code,
            terraform=terraform,
            platform=self.platform_id,
            confidence=confidence,
            can_deploy=can_deploy,
            metadata={"constraint_violations": violation_dicts},
        )
    
    def _build_recommendations(
        self,
        patterns: List[Any],
        features: IRFeature,
        violations: List[Any],
    ) -> List[Dict[str, Any]]:
        recs = []
        
        if patterns:
            for p in patterns:
                recs.append({
                    "name": p.pattern_id,
                    "reason": f"Matched pattern {p.pattern_id} with score {p.match_score:.2f}",
                    "priority": p.priority,
                })
        
        if features.has_serverless:
            recs.append({
                "name": "azure_functions",
                "reason": "Features indicate serverless requirement",
                "priority": 9,
            })
        
        if features.has_container:
            recs.append({
                "name": "azure_aks",
                "reason": "Features indicate container requirement",
                "priority": 8,
            })
        
        if violations:
            for v in violations:
                if hasattr(v, "severity") and v.severity == "warning":
                    msg = getattr(v, "message", str(v))
                    recs.append({
                        "name": "constraint_warning",
                        "reason": msg,
                        "priority": 5,
                    })
        
        return recs
    
    def generate_config(self, features: IRFeature) -> Dict[str, str]:
        configs = {}
        
        if features.has_serverless:
            configs["host.json"] = '''{
  "version": 2,
  "extensions": {
    "http": {
      "routePrefix": ""
    }
  }
}'''
        
        return configs
    
    def generate_code(self, features: IRFeature) -> Dict[str, str]:
        code = {}
        
        if features.has_serverless:
            code["index.js"] = '''module.exports = async function (context, req) {
    context.res = {
        body: "Hello from Azure Functions"
    };
};'''
        
        return code
    
    # ── Bidirectional Import ──────────────────────────────────────────
    
    def import_from_terraform(self, state_file: dict) -> Dict[str, Any]:
        """Parse Terraform state JSON into generic Intermediate Representation.
        
        Args:
            state_file: A Terraform state dict (from `terraform show -json`)
            
        Returns:
            Dict with nodes (resources) and edges (relationships/dependencies)
        """
        ir_nodes = []
        ir_edges = []
        
        resources = state_file.get("resources", [])
        
        for resource in resources:
            resource_type = resource.get("type", "")
            resource_name = resource.get("name", "")
            instances = resource.get("instances", [])
            
            if not instances:
                continue
            
            instance = instances[0]
            attributes = instance.get("attributes", {})
            
            # Map Azure Terraform resource types to IR node types
            node_mapping = {
                "azurerm_function_app": {"type": "Function", "platform_type": "functions"},
                "azurerm_cosmosdb_account": {"type": "Database", "platform_type": "cosmos_db"},
                "azurerm_kubernetes_cluster": {"type": "Container", "platform_type": "aks"},
                "azurerm_storage_account": {"type": "Storage", "platform_type": "storage"},
                "azurerm_event_hub_namespace": {"type": "Messaging", "platform_type": "event_hubs"},
                "azurerm_key_vault": {"type": "Security", "platform_type": "key_vault"},
                "azurerm_log_analytics_workspace": {"type": "Logging", "platform_type": "log_analytics"},
                "azurerm_api_management": {"type": "APIGateway", "platform_type": "api_management"},
                "azurerm_service_bus_namespace": {"type": "Messaging", "platform_type": "service_bus"},
                "azurerm_container_registry": {"type": "Registry", "platform_type": "container_registry"},
                "azurerm_application_insights": {"type": "Monitoring", "platform_type": "application_insights"},
            }
            
            mapping = node_mapping.get(resource_type, {"type": "Resource", "platform_type": resource_type})
            
            properties = self._extract_terraform_properties(resource_type, attributes)
            
            ir_node = {
                "id": resource_name,
                "type": mapping["type"],
                "platform_type": mapping["platform_type"],
                "properties": properties,
                "region": attributes.get("location", ""),
                "source": "terraform",
            }
            ir_nodes.append(ir_node)
        
        # Infer edges from Terraform dependencies and attributes
        for resource in resources:
            resource_name = resource.get("name", "")
            instances = resource.get("instances", [])
            if not instances:
                continue
            
            instance = instances[0]
            attributes = instance.get("attributes", {})
            
            # Dependencies from Terraform 'depends_on'
            for dep in resource.get("depends_on", []):
                ir_edges.append({
                    "source": dep,
                    "target": resource_name,
                    "type": "DEPENDS_ON",
                    "source_type": "terraform",
                })
            
            # Implicit relationships from attributes
            for attr_name, attr_value in attributes.items():
                if attr_name.endswith("_id") and isinstance(attr_value, str):
                    for node in ir_nodes:
                        if node["id"] in attr_value and node["id"] != resource_name:
                            ir_edges.append({
                                "source": node["id"],
                                "target": resource_name,
                                "type": "USES",
                                "source_type": "inferred",
                            })
                            break
        
        return {
            "nodes": ir_nodes,
            "edges": ir_edges,
            "node_count": len(ir_nodes),
            "edge_count": len(ir_edges),
            "source": "terraform_import",
        }
    
    def _extract_terraform_properties(self, resource_type: str, attributes: dict) -> dict:
        """Extract relevant properties from Azure Terraform resource attributes."""
        props = {}
        
        if resource_type == "azurerm_function_app":
            props["runtime"] = attributes.get("site_config", [{}])[0].get("linux_fx_version", "") if attributes.get("site_config") else ""
            props["kind"] = attributes.get("kind", "")
            always_on = attributes.get("site_config", [{}])[0].get("always_on", False) if attributes.get("site_config") else False
            props["always_on"] = always_on
            props["app_service_plan_id"] = attributes.get("app_service_plan_id", "")
        
        elif resource_type == "azurerm_cosmosdb_account":
            props["offer_type"] = attributes.get("offer_type", "Standard")
            props["kind"] = attributes.get("kind", "GlobalDocumentDB")
            consistency = attributes.get("consistency_policy", [{}])
            props["consistency_level"] = consistency[0].get("consistency_level", "Session") if consistency else "Session"
        
        elif resource_type == "azurerm_kubernetes_cluster":
            props["kubernetes_version"] = attributes.get("kubernetes_version", "")
            props["dns_prefix"] = attributes.get("dns_prefix", "")
            default_pool = attributes.get("default_node_pool", [{}])
            props["node_count"] = default_pool[0].get("node_count", 1) if default_pool else 1
            props["vm_size"] = default_pool[0].get("vm_size", "Standard_DS2_v2") if default_pool else "Standard_DS2_v2"
        
        elif resource_type == "azurerm_storage_account":
            props["account_tier"] = attributes.get("account_tier", "Standard")
            props["account_replication_type"] = attributes.get("account_replication_type", "LRS")
            props["account_kind"] = attributes.get("account_kind", "StorageV2")
        
        return props
    
    # ── Terraform HCL Generation ─────────────────────────────────────
    
    def generate_terraform(self, features: IRFeature) -> str:
        """Generate production-quality Terraform HCL from IR features.
        
        Uses azurerm provider with proper versioning and tagging.
        """
        modules = []
        
        # Terraform backend and provider block
        modules.append('''terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
  
  default_tags = {
    ManagedBy = "gag"
    Generated = "true"
  }
}''')
        
        # Resource group (required for Azure)
        modules.append('''resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
}''')
        
        # Azure Functions
        if features.has_serverless:
            modules.append('''resource "azurerm_storage_account" "functions" {
  name                     = var.function_storage_name
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_service_plan" "functions" {
  name                = var.service_plan_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = var.service_plan_sku
}

resource "azurerm_linux_function_app" "main" {
  name                        = var.function_app_name
  resource_group_name         = azurerm_resource_group.main.name
  location                    = azurerm_resource_group.main.location
  storage_account_name        = azurerm_storage_account.functions.name
  storage_account_access_key  = azurerm_storage_account.functions.primary_access_key
  service_plan_id             = azurerm_service_plan.functions.id

  site_config {
    application_stack {
      python_version = var.function_python_version
    }
  }

  app_settings = var.function_app_settings
}''')
        
        # Cosmos DB
        if features.has_database:
            modules.append('''resource "azurerm_cosmosdb_account" "main" {
  name                = var.cosmosdb_account_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  consistency_policy {
    consistency_level = var.cosmosdb_consistency_level
  }

  geo_location {
    location          = azurerm_resource_group.main.location
    failover_priority = 0
  }
}''')
        
        # Event Hubs namespace
        if features.has_event_driven:
            modules.append('''resource "azurerm_eventhub_namespace" "main" {
  name                = var.eventhub_namespace_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.eventhub_sku
  capacity            = var.eventhub_capacity
}''')
        
        if modules:
            modules.append(self._terraform_variables())
        
        return "\n".join(modules)
    
    def _terraform_variables(self) -> str:
        """Generate Terraform variables block for Azure module variables."""
        return '''variable "resource_group_name" {
  description = "Azure Resource Group name"
  type        = string
  default     = "gag-rg"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "function_storage_name" {
  description = "Storage account name for Azure Functions"
  type        = string
}

variable "service_plan_name" {
  description = "App Service Plan name"
  type        = string
  default     = "gag-service-plan"
}

variable "service_plan_sku" {
  description = "Service plan SKU"
  type        = string
  default     = "Y1"
}

variable "function_app_name" {
  description = "Azure Function App name"
  type        = string
}

variable "function_python_version" {
  description = "Python version for Azure Functions"
  type        = string
  default     = "3.11"
}

variable "function_app_settings" {
  description = "Azure Function App settings"
  type        = map(string)
  default     = {}
}

variable "cosmosdb_account_name" {
  description = "Cosmos DB account name"
  type        = string
}

variable "cosmosdb_consistency_level" {
  description = "Cosmos DB consistency level"
  type        = string
  default     = "Session"
}

variable "eventhub_namespace_name" {
  description = "Event Hubs namespace name"
  type        = string
}

variable "eventhub_sku" {
  description = "Event Hubs SKU"
  type        = string
  default     = "Standard"
}

variable "eventhub_capacity" {
  description = "Event Hubs throughput units"
  type        = number
  default     = 1
}'''


class GCPAdapter(PlatformAdapter):
    def __init__(self):
        super().__init__()
        self._config_loader = None
    
    def _get_config_loader(self):
        if self._config_loader is None:
            from core.adapters.config_loader import get_config_loader
            self._config_loader = get_config_loader()
        return self._config_loader
    
    @property
    def platform_id(self) -> str:
        return "gcp"
    
    @property
    def supported_services(self) -> List[str]:
        """Load services from YAML config if available, else use defaults."""
        loader = self._get_config_loader()
        services = loader.load_services("gcp")
        if services:
            result = []
            for category_services in services.values():
                result.extend(category_services)
            return sorted(set(result))
        # Fallback to defaults
        return [
            "cloud-functions",
            "cloud-run",
            "gke",
            "firestore",
            "cloud-storage",
            "cloud-sql",
            "pubsub",
            "api-gateway",
            "secret-manager",
            "cloud-build",
        ]
    
    @property
    def patterns(self) -> List[Pattern]:
        return [
            Pattern(
                id="gcp_cloud_functions",
                name="Cloud Functions",
                domain="serverless",
                triggers=["function", "serverless", "gcp"],
                conditions=[],
                components=["cloud-functions"],
                benefits=["Pay per request", "Auto-scale"],
                tradeoffs=["Vendor lock-in"],
                priority=9,
                confidence=0.9,
            ),
            Pattern(
                id="gcp_cloud_run",
                name="Cloud Run",
                domain="serverless",
                triggers=["container", "cloud-run", "serverless"],
                conditions=[],
                components=["cloud-run"],
                benefits=["Container-based", "HTTPS endpoint"],
                tradeoffs=["Stateless only"],
                priority=9,
                confidence=0.9,
            ),
            Pattern(
                id="gcp_gke",
                name="GKE Autopilot",
                domain="container",
                triggers=["kubernetes", "k8s", "gke"],
                conditions=[],
                components=["gke"],
                benefits=["Managed K8s", "Autopilot mode"],
                tradeoffs=["Cost"],
                priority=8,
                confidence=0.85,
            ),
            Pattern(
                id="gcp_firestore",
                name="Firestore",
                domain="database",
                triggers=["nosql", "firestore", "document"],
                conditions=[],
                components=["firestore"],
                benefits=["Serverless", "Real-time sync"],
                tradeoffs=["Limited queries"],
                priority=8,
                confidence=0.8,
            ),
            Pattern(
                id="gcp_pubsub",
                name="Pub/Sub",
                domain="event-driven",
                triggers=["event", "pubsub", "messaging"],
                conditions=[],
                components=["pubsub"],
                benefits=["Managed", "Scalable"],
                tradeoffs=["At-least-once delivery"],
                priority=7,
                confidence=0.8,
            ),
        ]
    
    @property
    def constraints(self) -> List[Constraint]:
        return [
            Constraint(
                id="gcp_functions_timeout",
                name="Functions timeout 9min",
                domain="serverless",
                type="limit",
                feature="timeout",
                operator="lte",
                threshold=540,
                message="Cloud Functions timeout cannot exceed 540 seconds",
                fix_hint="Use Cloud Run or GKE for longer workloads",
                severity="error",
                platforms=["gcp"],
            ),
            Constraint(
                id="gcp_functions_memory",
                name="Functions memory max 8GB",
                domain="serverless",
                type="limit",
                feature="memory",
                operator="lte",
                threshold=8192,
                message="Cloud Functions memory cannot exceed 8192 MB",
                fix_hint="Use Cloud Run for higher memory",
                severity="error",
                platforms=["gcp"],
            ),
        ]
    
    def transform_ir_to_platform(self, input: AdapterInput) -> AdapterOutput:
        features = input.ir_features
        pattern_results = input.pattern_matches
        violations = list(input.constraint_violations)
        
        configs = self.generate_config(features)
        code = self.generate_code(features)
        terraform = self.generate_terraform(features)
        
        # ── Deep platform constraint validation ──────────────────────────
        engine = get_constraint_engine()
        
        # Evaluate feature set against GCP service limits
        feature_dict = features.model_dump()
        platform_violations = engine.evaluate(feature_dict, "gcp")
        violations.extend(platform_violations)
        
        # Evaluate cross-service compatibility rules
        cross_service_violations = engine.validate_cross_service_compatibility(
            feature_dict, platform="gcp"
        )
        violations.extend(cross_service_violations)
        # ─────────────────────────────────────────────────────────────────
        
        recommendations = self._build_recommendations(pattern_results, features, violations)
        
        can_deploy = not any(
            getattr(v, "severity", "error") == "error" for v in violations
        )
        
        confidence = (
            sum(p.match_score for p in pattern_results) / max(1, len(pattern_results))
            if pattern_results else 0.7
        )
        
        # Attach all violations to metadata for downstream consumers
        violation_dicts = []
        for v in violations:
            if hasattr(v, "model_dump"):
                violation_dicts.append(v.model_dump())
            elif hasattr(v, "__dict__"):
                violation_dicts.append({
                    "message": getattr(v, "message", str(v)),
                    "severity": getattr(v, "severity", "error"),
                    "fix_hint": getattr(v, "fix_hint", ""),
                })
        
        return AdapterOutput(
            recommendations=recommendations,
            config_templates=configs,
            code_snippets=code,
            terraform=terraform,
            platform=self.platform_id,
            confidence=confidence,
            can_deploy=can_deploy,
            metadata={"constraint_violations": violation_dicts},
        )
    
    def _build_recommendations(
        self,
        patterns: List[Any],
        features: IRFeature,
        violations: List[Any],
    ) -> List[Dict[str, Any]]:
        recs = []
        
        if patterns:
            for p in patterns:
                recs.append({
                    "name": p.pattern_id,
                    "reason": f"Matched pattern {p.pattern_id} with score {p.match_score:.2f}",
                    "priority": p.priority,
                })
        
        if features.has_serverless:
            recs.append({
                "name": "gcp_cloud_functions",
                "reason": "Features indicate serverless requirement",
                "priority": 9,
            })
        
        if features.has_container:
            recs.append({
                "name": "gcp_cloud_run",
                "reason": "Features indicate container requirement",
                "priority": 8,
            })
        
        if violations:
            for v in violations:
                if hasattr(v, "severity") and v.severity == "warning":
                    msg = getattr(v, "message", str(v))
                    recs.append({
                        "name": "constraint_warning",
                        "reason": msg,
                        "priority": 5,
                    })
        
        return recs
    
    def generate_config(self, features: IRFeature) -> Dict[str, str]:
        configs = {}
        
        if features.has_serverless:
            configs["main.py"] = '''def main(request):
    return "Hello from Cloud Functions"'''
        
        return configs
    
    def generate_code(self, features: IRFeature) -> Dict[str, str]:
        code = {}
        if features.has_serverless:
            code["main.py"] = '''def hello_world(request):
    return "Hello from Cloud Functions"'''
        return code
    
    # ── Bidirectional Import ──────────────────────────────────────────
    
    def import_from_terraform(self, state_file: dict) -> Dict[str, Any]:
        """Parse Terraform state JSON into generic Intermediate Representation.
        
        Args:
            state_file: A Terraform state dict (from `terraform show -json`)
            
        Returns:
            Dict with nodes (resources) and edges (relationships/dependencies)
        """
        ir_nodes = []
        ir_edges = []
        
        resources = state_file.get("resources", [])
        
        for resource in resources:
            resource_type = resource.get("type", "")
            resource_name = resource.get("name", "")
            instances = resource.get("instances", [])
            
            if not instances:
                continue
            
            instance = instances[0]
            attributes = instance.get("attributes", {})
            
            # Map GCP Terraform resource types to IR node types
            node_mapping = {
                "google_cloudfunctions_function": {"type": "Function", "platform_type": "cloud_functions"},
                "google_cloud_run_service": {"type": "Container", "platform_type": "cloud_run"},
                "google_container_cluster": {"type": "Container", "platform_type": "gke"},
                "google_storage_bucket": {"type": "Storage", "platform_type": "cloud_storage"},
                "google_pubsub_topic": {"type": "Messaging", "platform_type": "pubsub"},
                "google_firestore_database": {"type": "Database", "platform_type": "firestore"},
                "google_kms_crypto_key": {"type": "Security", "platform_type": "cloud_kms"},
                "google_service_account": {"type": "IAM", "platform_type": "iam"},
                "google_cloud_sql_database_instance": {"type": "Database", "platform_type": "cloud_sql"},
                "google_bigquery_dataset": {"type": "Analytics", "platform_type": "bigquery"},
                "google_secret_manager_secret": {"type": "Security", "platform_type": "secret_manager"},
                "google_cloud_scheduler_job": {"type": "Scheduler", "platform_type": "cloud_scheduler"},
            }
            
            mapping = node_mapping.get(resource_type, {"type": "Resource", "platform_type": resource_type})
            
            properties = self._extract_terraform_properties(resource_type, attributes)
            
            ir_node = {
                "id": resource_name,
                "type": mapping["type"],
                "platform_type": mapping["platform_type"],
                "properties": properties,
                "region": attributes.get("region", attributes.get("location", "")),
                "source": "terraform",
            }
            ir_nodes.append(ir_node)
        
        # Infer edges from Terraform dependencies and attributes
        for resource in resources:
            resource_name = resource.get("name", "")
            instances = resource.get("instances", [])
            if not instances:
                continue
            
            instance = instances[0]
            attributes = instance.get("attributes", {})
            
            # Dependencies from Terraform 'depends_on'
            for dep in resource.get("depends_on", []):
                ir_edges.append({
                    "source": dep,
                    "target": resource_name,
                    "type": "DEPENDS_ON",
                    "source_type": "terraform",
                })
            
            # Implicit relationships from attributes (e.g., service account references)
            for attr_name, attr_value in attributes.items():
                if attr_name.endswith("_email") and isinstance(attr_value, str):
                    for node in ir_nodes:
                        if node.get("platform_type") == "iam" and node["id"] in attr_value:
                            ir_edges.append({
                                "source": node["id"],
                                "target": resource_name,
                                "type": "USES",
                                "source_type": "inferred",
                            })
                            break
        
        return {
            "nodes": ir_nodes,
            "edges": ir_edges,
            "node_count": len(ir_nodes),
            "edge_count": len(ir_edges),
            "source": "terraform_import",
        }
    
    def _extract_terraform_properties(self, resource_type: str, attributes: dict) -> dict:
        """Extract relevant properties from GCP Terraform resource attributes."""
        props = {}
        
        if resource_type == "google_cloudfunctions_function":
            props["runtime"] = attributes.get("runtime", "")
            props["entry_point"] = attributes.get("entry_point", "")
            props["available_memory_mb"] = attributes.get("available_memory_mb", 256)
            props["timeout"] = attributes.get("timeout", 60)
            props["max_instances"] = attributes.get("max_instances", 0)
        
        elif resource_type == "google_cloud_run_service":
            props["ingress"] = attributes.get("template", [{}])[0].get("metadata", {}).get("annotations", {}).get("run.googleapis.com/ingress", "all") if attributes.get("template") else "all"
            template = attributes.get("template", [{}])
            spec = template[0].get("spec", {}) if template else {}
            containers = spec.get("containers", [{}])
            resources = containers[0].get("resources", {}) if containers else {}
            props["memory"] = resources.get("limits", {}).get("memory", "")
            props["cpu"] = resources.get("limits", {}).get("cpu", "")
        
        elif resource_type == "google_container_cluster":
            props["initial_node_count"] = attributes.get("initial_node_count", 1)
            props["location"] = attributes.get("location", "")
            props["min_master_version"] = attributes.get("min_master_version", "")
            remove_default_pool = attributes.get("remove_default_node_pool", False)
            props["remove_default_node_pool"] = remove_default_pool
        
        elif resource_type == "google_storage_bucket":
            props["name"] = attributes.get("name", "")
            props["location"] = attributes.get("location", "US")
            props["storage_class"] = attributes.get("storage_class", "STANDARD")
            versioning = attributes.get("versioning", [{}])
            props["versioning_enabled"] = versioning[0].get("enabled", False) if versioning else False
        
        return props
    
    # ── Terraform HCL Generation ─────────────────────────────────────
    
    def generate_terraform(self, features: IRFeature) -> str:
        """Generate production-quality Terraform HCL from IR features.
        
        Uses google provider with proper versioning and tagging.
        """
        modules = []
        
        # Terraform backend and provider block
        modules.append('''terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  
  default_labels = {
    managed_by = "gag"
    generated  = "true"
  }
}''')
        
        # Cloud Functions
        if features.has_serverless:
            modules.append('''resource "google_storage_bucket" "function_source" {
  name     = var.function_bucket_name
  location = var.region
}

resource "google_cloudfunctions_function" "main" {
  name        = var.function_name
  description = "Generated by Engineering Intelligence System"
  runtime     = var.function_runtime
  
  available_memory_mb   = var.function_memory
  source_archive_bucket = google_storage_bucket.function_source.name
  source_archive_object = var.function_source_object
  trigger_http          = true
  entry_point           = var.function_entry_point
  
  environment_variables = var.function_env_vars
}

resource "google_cloudfunctions_function_iam_member" "invoker" {
  project        = google_cloudfunctions_function.main.project
  region         = google_cloudfunctions_function.main.region
  cloud_function = google_cloudfunctions_function.main.name
  
  role   = "roles/cloudfunctions.invoker"
  member = "allUsers"
}''')
        
        # Cloud Run
        if features.has_container:
            modules.append('''resource "google_cloud_run_v2_service" "main" {
  name     = var.cloud_run_service_name
  location = var.region
  
  template {
    containers {
      image = var.container_image
      
      resources {
        limits = {
          cpu    = var.container_cpu
          memory = var.container_memory
        }
      }
    }
  }
}

resource "google_cloud_run_service_iam_member" "invoker" {
  project  = google_cloud_run_v2_service.main.project
  location = google_cloud_run_v2_service.main.location
  service  = google_cloud_run_v2_service.main.name
  
  role   = "roles/run.invoker"
  member = "allUsers"
}''')
        
        # Firestore
        if features.has_database:
            modules.append('''resource "google_firestore_database" "main" {
  name        = var.firestore_database_name
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"
  
  concurrency_mode            = "OPTIMISTIC"
  app_engine_integration_mode = "DISABLED"
}''')
        
        # Pub/Sub
        if features.has_event_driven:
            modules.append('''resource "google_pubsub_topic" "main" {
  name = var.pubsub_topic_name
  
  labels = {
    managed_by = "gag"
  }
}

resource "google_pubsub_subscription" "main" {
  name  = "${google_pubsub_topic.main.name}-subscription"
  topic = google_pubsub_topic.main.name
  
  ack_deadline_seconds = var.pubsub_ack_deadline
  
  labels = {
    managed_by = "gag"
  }
}''')
        
        if modules:
            modules.append(self._terraform_variables())
        
        return "\n".join(modules)
    
    def _terraform_variables(self) -> str:
        """Generate Terraform variables block for GCP module variables."""
        return '''variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "function_bucket_name" {
  description = "GCS bucket name for Cloud Functions source"
  type        = string
}

variable "function_name" {
  description = "Cloud Function name"
  type        = string
}

variable "function_runtime" {
  description = "Cloud Function runtime"
  type        = string
  default     = "python312"
}

variable "function_memory" {
  description = "Cloud Function memory in MB"
  type        = number
  default     = 256
}

variable "function_source_object" {
  description = "Source archive object in GCS"
  type        = string
}

variable "function_entry_point" {
  description = "Cloud Function entry point"
  type        = string
  default     = "hello_world"
}

variable "function_env_vars" {
  description = "Cloud Function environment variables"
  type        = map(string)
  default     = {}
}

variable "cloud_run_service_name" {
  description = "Cloud Run service name"
  type        = string
}

variable "container_image" {
  description = "Container image URL"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "container_cpu" {
  description = "Container CPU limit"
  type        = string
  default     = "1"
}

variable "container_memory" {
  description = "Container memory limit"
  type        = string
  default     = "512Mi"
}

variable "firestore_database_name" {
  description = "Firestore database name"
  type        = string
  default     = "(default)"
}

variable "firestore_location" {
  description = "Firestore location"
  type        = string
  default     = "nam5"
}

variable "pubsub_topic_name" {
  description = "Pub/Sub topic name"
  type        = string
}

variable "pubsub_ack_deadline" {
  description = "Pub/Sub subscription ack deadline in seconds"
  type        = number
  default     = 600
}'''


def register_cloud_adapters():
    from core.adapters import get_adapter_registry
    registry = get_adapter_registry()
    registry.register(AWSAdapter())
    registry.register(AzureAdapter())
    registry.register(GCPAdapter())