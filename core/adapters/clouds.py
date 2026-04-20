from typing import Any, Dict, List
from core.adapters.base import AdapterInput, AdapterOutput, PlatformAdapter
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
    def patterns(self) -> List[Any]:
        return []
    
    @property
    def constraints(self) -> Any:
        return None
    
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
    def patterns(self) -> List[Any]:
        return []
    
    @property
    def constraints(self) -> Any:
        return None
    
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
    def patterns(self) -> List[Any]:
        return []
    
    @property
    def constraints(self) -> Any:
        return None
    
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
        return {}


def register_cloud_adapters():
    from core.adapters import get_adapter_registry
    registry = get_adapter_registry()
    registry.register(AWSAdapter())
    registry.register(AzureAdapter())
    registry.register(GCPAdapter())