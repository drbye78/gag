from typing import Any, Dict, List
from core.adapters.base import AdapterInput, AdapterOutput, PlatformAdapter
from core.patterns.schema import Pattern, get_pattern_library
from core.constraints.engine import get_constraint_engine, Constraint, ConstraintSet
from models.ir import IRFeature, PlatformContext


class AWSAdapter(PlatformAdapter):
    @property
    def platform_id(self) -> str:
        return "aws"
    
    @property
    def supported_services(self) -> List[str]:
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
        configs = self.generate_config(features)
        code = self.generate_code(features)
        
        return AdapterOutput(
            recommendations=[{"name": "AWS Architecture", "reason": "Based on extracted features"}],
            config_templates=configs,
            code_snippets=code,
            platform=self.platform_id,
            confidence=0.8,
        )
    
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


class AzureAdapter(PlatformAdapter):
    @property
    def platform_id(self) -> str:
        return "azure"
    
    @property
    def supported_services(self) -> List[str]:
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
        configs = self.generate_config(features)
        code = self.generate_code(features)
        
        return AdapterOutput(
            recommendations=[{"name": "Azure Architecture", "reason": "Based on extracted features"}],
            config_templates=configs,
            code_snippets=code,
            platform=self.platform_id,
            confidence=0.8,
        )
    
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


class GCPAdapter(PlatformAdapter):
    @property
    def platform_id(self) -> str:
        return "gcp"
    
    @property
    def supported_services(self) -> List[str]:
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
        configs = self.generate_config(features)
        code = self.generate_code(features)
        
        return AdapterOutput(
            recommendations=[{"name": "GCP Architecture", "reason": "Based on extracted features"}],
            config_templates=configs,
            code_snippets=code,
            platform=self.platform_id,
            confidence=0.8,
        )
    
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


def register_cloud_adapters():
    from core.adapters import get_adapter_registry
    registry = get_adapter_registry()
    registry.register(AWSAdapter())
    registry.register(AzureAdapter())
    registry.register(GCPAdapter())