from typing import Any, Dict, List

from core.adapters.base import AdapterInput, AdapterOutput, PlatformAdapter
from core.adapters.mixins import RecommendationMixin
from core.adapters.models import ServiceEdition, ServiceSpec, summarize_portfolios
from core.constraints.engine import Constraint
from core.patterns.schema import Pattern
from models.ir import IRFeature


class AWSAdapter(RecommendationMixin, PlatformAdapter):
    def __init__(self) -> None:
        super().__init__()

    @property
    def platform_id(self) -> str:
        return "aws"

    @property
    def supported_services(self) -> List[str]:
        return [
            "lambda", "ec2", "ecs", "eks", "s3", "dynamodb",
            "rds", "iam", "api-gateway", "cloudfront", "sns", "sqs", "eventbridge",
        ]

    @property
    def service_catalog(self) -> List[ServiceSpec]:
        return [
            ServiceSpec(name="lambda", portfolio="compute", edition=ServiceEdition.ENTERPRISE, sla="99.95%", tags=["serverless", "function", "faas"], cost_model={"monthly_min": 0, "monthly_max": 100}, description="AWS Lambda serverless functions"),
            ServiceSpec(name="ec2", portfolio="compute", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["vm", "compute", "instance"], cost_model={"monthly_min": 30, "monthly_max": 10000}, description="Amazon EC2 virtual machines"),
            ServiceSpec(name="ecs", portfolio="compute", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["container", "docker", "ecs"], cost_model={"monthly_min": 50, "monthly_max": 5000}, description="Amazon ECS container service"),
            ServiceSpec(name="eks", portfolio="compute", edition=ServiceEdition.ENTERPRISE, sla="99.95%", tags=["kubernetes", "k8s", "container"], cost_model={"monthly_min": 73, "monthly_max": 5000}, description="Amazon EKS managed Kubernetes"),
            ServiceSpec(name="s3", portfolio="storage", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["storage", "object", "bucket"], cost_model={"monthly_min": 0, "monthly_max": 500}, description="Amazon S3 object storage"),
            ServiceSpec(name="dynamodb", portfolio="database", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["nosql", "key-value", "database"], cost_model={"monthly_min": 0, "monthly_max": 5000}, description="Amazon DynamoDB NoSQL"),
            ServiceSpec(name="rds", portfolio="database", edition=ServiceEdition.ENTERPRISE, sla="99.95%", tags=["sql", "database", "relational"], cost_model={"monthly_min": 15, "monthly_max": 5000}, description="Amazon RDS relational database"),
            ServiceSpec(name="iam", portfolio="security", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["auth", "access", "roles"], cost_model={"monthly_min": 0, "monthly_max": 0}, description="AWS Identity and Access Management"),
            ServiceSpec(name="api-gateway", portfolio="networking", edition=ServiceEdition.ENTERPRISE, sla="99.95%", tags=["api", "gateway", "rest"], cost_model={"monthly_min": 0, "monthly_max": 1000}, description="Amazon API Gateway"),
            ServiceSpec(name="cloudfront", portfolio="networking", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["cdn", "edge", "delivery"], cost_model={"monthly_min": 0, "monthly_max": 500}, description="Amazon CloudFront CDN"),
            ServiceSpec(name="sns", portfolio="messaging", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["pub-sub", "notification", "topic"], cost_model={"monthly_min": 0, "monthly_max": 100}, description="Amazon SNS notification service"),
            ServiceSpec(name="sqs", portfolio="messaging", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["queue", "messaging", "decoupling"], cost_model={"monthly_min": 0, "monthly_max": 100}, description="Amazon SQS queue service"),
            ServiceSpec(name="eventbridge", portfolio="integration", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["event-bus", "eda", "scheduler"], cost_model={"monthly_min": 0, "monthly_max": 200}, description="Amazon EventBridge event bus"),
        ]

    @property
    def patterns(self) -> List[Pattern]:
        return [
            Pattern(id="aws_lambda", name="AWS Lambda Function", domain="serverless", triggers=["lambda", "serverless", "function"], conditions=[], components=["lambda"], benefits=["Pay per request", "Auto-scale", "No server management"], tradeoffs=["Cold starts", "Vendor lock-in"], priority=9, confidence=0.9),
            Pattern(id="aws_ecs_fargate", name="ECS Fargate Container", domain="container", triggers=["container", "docker", "ecs"], conditions=[], components=["ecs", "fargate"], benefits=["Managed containers", "Pay per use"], tradeoffs=["Complexity"], priority=8, confidence=0.85),
            Pattern(id="aws_lambda_api", name="Lambda API Gateway", domain="api", triggers=["api", "rest", "endpoint"], conditions=[], components=["api-gateway", "lambda"], benefits=["Quick APIs", "Low cost"], tradeoffs=["Timeouts"], priority=8, confidence=0.85),
            Pattern(id="aws_eventbridge", name="EventBridge Event Bus", domain="event-driven", triggers=["event", "eventbus", "pub-sub"], conditions=[], components=["eventbridge"], benefits=["Decoupled", "Reactive"], tradeoffs=["Learning curve"], priority=7, confidence=0.8),
            Pattern(id="aws_dynamodb", name="DynamoDB NoSQL", domain="database", triggers=["nosql", "dynamo", "key-value"], conditions=[], components=["dynamodb"], benefits=["Managed", "Fast", "Scalable"], tradeoffs=["Cost at scale"], priority=8, confidence=0.85),
        ]

    @property
    def constraints(self) -> List[Constraint]:
        return [
            Constraint(id="aws_lambda_timeout", name="Lambda timeout 15min", domain="serverless", type="limit", feature="timeout", operator="lte", threshold=900, message="Lambda timeout cannot exceed 900 seconds", fix_hint="Use Step Functions for longer workflows", severity="error", platforms=["aws"]),
            Constraint(id="aws_lambda_memory", name="Lambda memory max 10GB", domain="serverless", type="limit", feature="memory", operator="lte", threshold=10240, message="Lambda memory cannot exceed 10240 MB", fix_hint="Use ECS for high-memory workloads", severity="error", platforms=["aws"]),
        ]

    def transform_ir_to_platform(self, input: AdapterInput) -> AdapterOutput:
        features = input.ir_features
        pattern_results = input.pattern_matches
        violations = input.constraint_violations

        configs = self.generate_config(features)
        code = self.generate_code(features)
        recommendations = self._build_recommendations(pattern_results, features, violations)

        can_deploy = not any(v.severity == "error" for v in violations)
        confidence = (
            sum(getattr(p, "match_score", getattr(p, "score", 0.0)) for p in pattern_results)
            / max(1, len(pattern_results))
            if pattern_results
            else 0.7
        )

        selected = [r.get("name", "") for r in recommendations if r.get("name")]
        catalog_map = {s.name: s for s in self.service_catalog}
        service_specs = [catalog_map[name] for name in selected if name in catalog_map]
        compliance_matrix = self.compute_compliance(features, selected)
        cost_estimate = self.estimate_cost(features, selected)
        required_dependencies = self.resolve_dependencies(selected)

        return AdapterOutput(
            recommendations=recommendations,
            config_templates=configs,
            code_snippets=code,
            explanation=self._explain(recommendations, violations),
            confidence=confidence,
            can_deploy=can_deploy,
            platform=self.platform_id,
            service_specs=service_specs,
            compliance_matrix=compliance_matrix,
            cost_estimate=cost_estimate,
            required_dependencies=required_dependencies,
            portfolio_summary=summarize_portfolios(service_specs),
        )

    def _build_recommendations(
        self, patterns: List[Any], features: IRFeature, violations: List[Any],
    ) -> List[Dict[str, Any]]:
        recs = super()._build_recommendations(patterns, features, violations)

        if features.has_serverless:
            recs.append({"name": "aws_lambda", "reason": "Features indicate serverless requirement", "priority": 9})
        if features.has_container:
            recs.append({"name": "aws_ecs_fargate", "reason": "Features indicate container requirement", "priority": 8})

        seen = set()
        deduped = []
        for r in recs:
            key = (r.get("name"), r.get("reason", ""))
            if key not in seen:
                seen.add(key)
                deduped.append(r)
        return deduped

    def generate_config(self, features: IRFeature) -> Dict[str, str]:
        configs = {}
        if features.has_serverless:
            configs["serverless.yml"] = """service: my-service
provider:
  name: aws
  runtime: python3.12
functions:
  hello:
    handler: handler.hello
    events:
      - http:
          path: hello
          method: get"""
        if features.has_container:
            configs["ecs-task-definition.json"] = """{ "family": "my-task", "networkMode": "awsvpc", "requiresCompatibilities": ["FARGATE"], "cpu": "256", "memory": "512" }"""
        return configs

    def generate_code(self, features: IRFeature) -> Dict[str, str]:
        code = {}
        if features.has_serverless:
            code["handler.py"] = """def handler(event, context):
    return {"statusCode": 200, "body": "Hello from Lambda"}"""
        return code


class AzureAdapter(RecommendationMixin, PlatformAdapter):
    def __init__(self) -> None:
        super().__init__()

    @property
    def platform_id(self) -> str:
        return "azure"

    @property
    def supported_services(self) -> List[str]:
        return ["functions", "app-service", "aks", "cosmos-db", "storage", "key-vault", "api-management", "event-hub", "service-bus", "logic-apps", "ad", "entra-id"]

    @property
    def service_catalog(self) -> List[ServiceSpec]:
        return [
            ServiceSpec(name="functions", portfolio="compute", edition=ServiceEdition.ENTERPRISE, sla="99.95%", tags=["serverless", "function", "faas"], cost_model={"monthly_min": 0, "monthly_max": 100}, description="Azure Functions serverless"),
            ServiceSpec(name="app-service", portfolio="compute", edition=ServiceEdition.ENTERPRISE, sla="99.95%", tags=["web", "app", "paas"], cost_model={"monthly_min": 13, "monthly_max": 1000}, description="Azure App Service"),
            ServiceSpec(name="aks", portfolio="compute", edition=ServiceEdition.ENTERPRISE, sla="99.95%", tags=["kubernetes", "k8s", "container"], cost_model={"monthly_min": 73, "monthly_max": 5000}, description="Azure Kubernetes Service"),
            ServiceSpec(name="cosmos-db", portfolio="database", edition=ServiceEdition.ENTERPRISE, sla="99.999%", tags=["nosql", "database", "global"], cost_model={"monthly_min": 25, "monthly_max": 10000}, description="Azure Cosmos DB"),
            ServiceSpec(name="storage", portfolio="storage", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["blob", "file", "queue", "table"], cost_model={"monthly_min": 0, "monthly_max": 500}, description="Azure Storage"),
            ServiceSpec(name="key-vault", portfolio="security", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["secrets", "encryption", "certificates"], cost_model={"monthly_min": 0, "monthly_max": 50}, description="Azure Key Vault"),
            ServiceSpec(name="api-management", portfolio="networking", edition=ServiceEdition.ENTERPRISE, sla="99.95%", tags=["api", "gateway", "management"], cost_model={"monthly_min": 150, "monthly_max": 5000}, description="Azure API Management"),
            ServiceSpec(name="event-hub", portfolio="messaging", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["event", "streaming", "kafka"], cost_model={"monthly_min": 10, "monthly_max": 1000}, description="Azure Event Hubs"),
            ServiceSpec(name="service-bus", portfolio="messaging", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["queue", "topic", "messaging"], cost_model={"monthly_min": 10, "monthly_max": 500}, description="Azure Service Bus"),
            ServiceSpec(name="logic-apps", portfolio="integration", edition=ServiceEdition.ENTERPRISE, sla="99.9%", tags=["workflow", "integration", "low-code"], cost_model={"monthly_min": 0, "monthly_max": 500}, description="Azure Logic Apps"),
            ServiceSpec(name="ad", portfolio="security", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["identity", "directory", "sso"], cost_model={"monthly_min": 0, "monthly_max": 100}, description="Azure Active Directory"),
            ServiceSpec(name="entra-id", portfolio="security", edition=ServiceEdition.ENTERPRISE, sla="99.99%", certifications=["SOC2", "ISO 27001"], tags=["identity", "iam", "microsoft-entra"], cost_model={"monthly_min": 0, "monthly_max": 100}, description="Microsoft Entra ID"),
        ]

    @property
    def patterns(self) -> List[Pattern]:
        return [
            Pattern(id="azure_functions", name="Azure Functions", domain="serverless", triggers=["function", "serverless", "azure"], conditions=[], components=["functions"], benefits=["Pay per execution", "Auto-scale"], tradeoffs=["Vendor lock-in"], priority=9, confidence=0.9),
            Pattern(id="azure_aks", name="Azure Kubernetes Service", domain="container", triggers=["kubernetes", "k8s", "aks"], conditions=[], components=["aks"], benefits=["Managed K8s", "Enterprise ready"], tradeoffs=["Complexity"], priority=8, confidence=0.85),
            Pattern(id="azure_cosmosdb", name="Cosmos DB", domain="database", triggers=["nosql", "cosmos", "mongodb"], conditions=[], components=["cosmos-db"], benefits=["Global distribution", "SLA"], tradeoffs=["Cost at scale"], priority=8, confidence=0.8),
            Pattern(id="azure_eventhub", name="Event Hubs", domain="event-driven", triggers=["event", "streaming", "eventhub"], conditions=[], components=["event-hub"], benefits=["Throughput", "Real-time"], tradeoffs=["Learning curve"], priority=7, confidence=0.8),
        ]

    @property
    def constraints(self) -> List[Constraint]:
        return [
            Constraint(id="azure_functions_timeout", name="Functions timeout 10min", domain="serverless", type="limit", feature="timeout", operator="lte", threshold=600, message="Functions timeout cannot exceed 600 seconds", fix_hint="Use Durable Functions for longer workflows", severity="error", platforms=["azure"]),
            Constraint(id="azure_functions_scale", name="Functions scale limit", domain="serverless", type="limit", feature="instances", operator="lte", threshold=200, message="Functions scale limit is 200 instances", fix_hint="Contact support for higher limits", severity="warning", platforms=["azure"]),
        ]

    def transform_ir_to_platform(self, input: AdapterInput) -> AdapterOutput:
        features = input.ir_features
        pattern_results = input.pattern_matches
        violations = input.constraint_violations

        configs = self.generate_config(features)
        code = self.generate_code(features)
        recommendations = self._build_recommendations(pattern_results, features, violations)

        can_deploy = not any(v.severity == "error" for v in violations)
        confidence = (
            sum(getattr(p, "match_score", getattr(p, "score", 0.0)) for p in pattern_results)
            / max(1, len(pattern_results))
            if pattern_results
            else 0.7
        )

        selected = [r.get("name", "") for r in recommendations if r.get("name")]
        catalog_map = {s.name: s for s in self.service_catalog}
        service_specs = [catalog_map[name] for name in selected if name in catalog_map]
        compliance_matrix = self.compute_compliance(features, selected)
        cost_estimate = self.estimate_cost(features, selected)
        required_dependencies = self.resolve_dependencies(selected)

        return AdapterOutput(
            recommendations=recommendations,
            config_templates=configs,
            code_snippets=code,
            explanation=self._explain(recommendations, violations),
            confidence=confidence,
            can_deploy=can_deploy,
            platform=self.platform_id,
            service_specs=service_specs,
            compliance_matrix=compliance_matrix,
            cost_estimate=cost_estimate,
            required_dependencies=required_dependencies,
            portfolio_summary=summarize_portfolios(service_specs),
        )

    def _build_recommendations(
        self, patterns: List[Any], features: IRFeature, violations: List[Any],
    ) -> List[Dict[str, Any]]:
        recs = super()._build_recommendations(patterns, features, violations)
        if features.has_serverless:
            recs.append({"name": "azure_functions", "reason": "Features indicate serverless requirement", "priority": 9})
        if features.has_container:
            recs.append({"name": "azure_aks", "reason": "Features indicate container requirement", "priority": 8})
        seen = set()
        deduped = []
        for r in recs:
            key = (r.get("name"), r.get("reason", ""))
            if key not in seen:
                seen.add(key)
                deduped.append(r)
        return deduped

    def generate_config(self, features: IRFeature) -> Dict[str, str]:
        configs = {}
        if features.has_serverless:
            configs["host.json"] = '{ "version": 2, "extensions": { "http": { "routePrefix": "" } } }'
        return configs

    def generate_code(self, features: IRFeature) -> Dict[str, str]:
        code = {}
        if features.has_serverless:
            code["index.js"] = """module.exports = async function (context, req) {
    context.res = { body: "Hello from Azure Functions" };
};"""
        return code


class GCPAdapter(RecommendationMixin, PlatformAdapter):
    def __init__(self) -> None:
        super().__init__()

    @property
    def platform_id(self) -> str:
        return "gcp"

    @property
    def supported_services(self) -> List[str]:
        return ["cloud-functions", "cloud-run", "gke", "firestore", "cloud-storage", "cloud-sql", "pubsub", "api-gateway", "secret-manager", "cloud-build"]

    @property
    def service_catalog(self) -> List[ServiceSpec]:
        return [
            ServiceSpec(name="cloud-functions", portfolio="compute", edition=ServiceEdition.ENTERPRISE, sla="99.95%", tags=["serverless", "function", "faas"], cost_model={"monthly_min": 0, "monthly_max": 100}, description="Google Cloud Functions"),
            ServiceSpec(name="cloud-run", portfolio="compute", edition=ServiceEdition.ENTERPRISE, sla="99.95%", tags=["container", "serverless", "knative"], cost_model={"monthly_min": 0, "monthly_max": 500}, description="Google Cloud Run"),
            ServiceSpec(name="gke", portfolio="compute", edition=ServiceEdition.ENTERPRISE, sla="99.95%", tags=["kubernetes", "k8s", "container"], cost_model={"monthly_min": 73, "monthly_max": 5000}, description="Google Kubernetes Engine"),
            ServiceSpec(name="firestore", portfolio="database", edition=ServiceEdition.ENTERPRISE, sla="99.999%", tags=["nosql", "document", "serverless"], cost_model={"monthly_min": 0, "monthly_max": 300}, description="Google Firestore"),
            ServiceSpec(name="cloud-storage", portfolio="storage", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["storage", "object", "bucket"], cost_model={"monthly_min": 0, "monthly_max": 500}, description="Google Cloud Storage"),
            ServiceSpec(name="cloud-sql", portfolio="database", edition=ServiceEdition.ENTERPRISE, sla="99.95%", tags=["sql", "database", "relational"], cost_model={"monthly_min": 10, "monthly_max": 5000}, description="Google Cloud SQL"),
            ServiceSpec(name="pubsub", portfolio="messaging", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["pub-sub", "event", "messaging"], cost_model={"monthly_min": 0, "monthly_max": 200}, description="Google Pub/Sub"),
            ServiceSpec(name="api-gateway", portfolio="networking", edition=ServiceEdition.ENTERPRISE, sla="99.95%", tags=["api", "gateway", "rest"], cost_model={"monthly_min": 0, "monthly_max": 500}, description="Google API Gateway"),
            ServiceSpec(name="secret-manager", portfolio="security", edition=ServiceEdition.ENTERPRISE, sla="99.99%", tags=["secrets", "encryption", "credentials"], cost_model={"monthly_min": 0, "monthly_max": 50}, description="Google Secret Manager"),
            ServiceSpec(name="cloud-build", portfolio="ci-cd", edition=ServiceEdition.ENTERPRISE, sla="99.9%", tags=["build", "ci-cd", "pipeline"], cost_model={"monthly_min": 0, "monthly_max": 200}, description="Google Cloud Build"),
        ]

    @property
    def patterns(self) -> List[Pattern]:
        return [
            Pattern(id="gcp_cloud_functions", name="Cloud Functions", domain="serverless", triggers=["function", "serverless", "gcp"], conditions=[], components=["cloud-functions"], benefits=["Pay per request", "Auto-scale"], tradeoffs=["Vendor lock-in"], priority=9, confidence=0.9),
            Pattern(id="gcp_cloud_run", name="Cloud Run", domain="serverless", triggers=["container", "cloud-run", "serverless"], conditions=[], components=["cloud-run"], benefits=["Container-based", "HTTPS endpoint"], tradeoffs=["Stateless only"], priority=9, confidence=0.9),
            Pattern(id="gcp_gke", name="GKE Autopilot", domain="container", triggers=["kubernetes", "k8s", "gke"], conditions=[], components=["gke"], benefits=["Managed K8s", "Autopilot mode"], tradeoffs=["Cost"], priority=8, confidence=0.85),
            Pattern(id="gcp_firestore", name="Firestore", domain="database", triggers=["nosql", "firestore", "document"], conditions=[], components=["firestore"], benefits=["Serverless", "Real-time sync"], tradeoffs=["Limited queries"], priority=8, confidence=0.8),
            Pattern(id="gcp_pubsub", name="Pub/Sub", domain="event-driven", triggers=["event", "pubsub", "messaging"], conditions=[], components=["pubsub"], benefits=["Managed", "Scalable"], tradeoffs=["At-least-once delivery"], priority=7, confidence=0.8),
        ]

    @property
    def constraints(self) -> List[Constraint]:
        return [
            Constraint(id="gcp_functions_timeout", name="Functions timeout 9min", domain="serverless", type="limit", feature="timeout", operator="lte", threshold=540, message="Cloud Functions timeout cannot exceed 540 seconds", fix_hint="Use Cloud Run or GKE for longer workloads", severity="error", platforms=["gcp"]),
            Constraint(id="gcp_functions_memory", name="Functions memory max 8GB", domain="serverless", type="limit", feature="memory", operator="lte", threshold=8192, message="Cloud Functions memory cannot exceed 8192 MB", fix_hint="Use Cloud Run for higher memory", severity="error", platforms=["gcp"]),
        ]

    def transform_ir_to_platform(self, input: AdapterInput) -> AdapterOutput:
        features = input.ir_features
        pattern_results = input.pattern_matches
        violations = input.constraint_violations

        configs = self.generate_config(features)
        code = self.generate_code(features)
        recommendations = self._build_recommendations(pattern_results, features, violations)

        can_deploy = not any(v.severity == "error" for v in violations)
        confidence = (
            sum(getattr(p, "match_score", getattr(p, "score", 0.0)) for p in pattern_results)
            / max(1, len(pattern_results))
            if pattern_results
            else 0.7
        )

        selected = [r.get("name", "") for r in recommendations if r.get("name")]
        catalog_map = {s.name: s for s in self.service_catalog}
        service_specs = [catalog_map[name] for name in selected if name in catalog_map]
        compliance_matrix = self.compute_compliance(features, selected)
        cost_estimate = self.estimate_cost(features, selected)
        required_dependencies = self.resolve_dependencies(selected)

        return AdapterOutput(
            recommendations=recommendations,
            config_templates=configs,
            code_snippets=code,
            explanation=self._explain(recommendations, violations),
            confidence=confidence,
            can_deploy=can_deploy,
            platform=self.platform_id,
            service_specs=service_specs,
            compliance_matrix=compliance_matrix,
            cost_estimate=cost_estimate,
            required_dependencies=required_dependencies,
            portfolio_summary=summarize_portfolios(service_specs),
        )

    def _build_recommendations(
        self, patterns: List[Any], features: IRFeature, violations: List[Any],
    ) -> List[Dict[str, Any]]:
        recs = super()._build_recommendations(patterns, features, violations)
        if features.has_serverless:
            recs.append({"name": "gcp_cloud_functions", "reason": "Features indicate serverless requirement", "priority": 9})
        if features.has_container:
            recs.append({"name": "gcp_gke", "reason": "Features indicate container requirement", "priority": 8})
        seen = set()
        deduped = []
        for r in recs:
            key = (r.get("name"), r.get("reason", ""))
            if key not in seen:
                seen.add(key)
                deduped.append(r)
        return deduped

    def generate_config(self, features: IRFeature) -> Dict[str, str]:
        configs = {}
        if features.has_serverless:
            configs["main.py"] = "def main(request):\n    return 'Hello from Cloud Functions'"
        return configs

    def generate_code(self, features: IRFeature) -> Dict[str, str]:
        code = {}
        if features.has_serverless:
            code["main.py"] = "def hello_world(request):\n    return 'Hello from Cloud Functions'"
        return code
