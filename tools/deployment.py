from typing import Any, Dict, List, Optional
import json
import logging

from tools.base import BaseTool, ToolInput, ToolOutput

logger = logging.getLogger(__name__)


class CICDPipelineGeneratorTool(BaseTool):
    """Generate CI/CD pipeline configuration for multiple platforms."""
    name = "cicd_pipeline_generate"
    description = "Generate CI/CD pipeline configuration (GitHub Actions, GitLab, Jenkins)"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        platform = input.args.get("platform", "github")
        language = input.args.get("language", "python")
        project_name = input.args.get("project_name", "my-project")
        include_tests = input.args.get("include_tests", True)
        include_deploy = input.args.get("include_deploy", False)
        
        try:
            pipeline = await self._generate_pipeline_llm(
                platform, language, project_name, include_tests, include_deploy
            )
            return ToolOutput(
                result={"platform": platform, "pipeline": pipeline},
                metadata={"generated": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM pipeline generation failed: {e}, using fallback")
            pipeline = await self._generate_pipeline_fallback(
                platform, language, project_name, include_tests, include_deploy
            )
            return ToolOutput(
                result={"platform": platform, "pipeline": pipeline},
                metadata={"generated": True, "method": "fallback", "error": str(e)}
            )
    
    async def _generate_pipeline_llm(
        self,
        platform: str,
        language: str,
        project_name: str,
        include_tests: bool,
        include_deploy: bool
    ) -> Dict[str, Any]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Generate a production-ready CI/CD pipeline configuration for {platform}.
Language: {language}
Project: {project_name}
Include tests: {include_tests}
Include deploy: {include_deploy}

Respond ONLY with a JSON object containing the full pipeline configuration.
For GitHub Actions: include full workflow YAML as a string in the 'yaml' field.
Include these jobs: lint, test, build, (deploy if include_deploy).
Use modern best practices: caching, matrix builds, artifact publishing."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=3000
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM pipeline generation failed: {e}")
            raise
    
    async def _generate_pipeline_fallback(
        self,
        platform: str,
        language: str,
        project_name: str,
        include_tests: bool,
        include_deploy: bool
    ) -> Dict[str, Any]:
        jobs = {
            "lint": {
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                ]
            },
            "build": {
                "runs-on": "ubuntu-latest",
                "needs": ["lint"] if include_tests else None,
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Setup Python", "uses": "actions/setup-python@v5", "with": {"python-version": "3.12"}},
                    {"name": "Install deps", "run": "pip install -e ."},
                    {"name": "Build", "run": f"python -m build"},
                ]
            }
        }
        
        if include_tests:
            jobs["test"] = {
                "runs-on": "ubuntu-latest",
                "needs": ["build"],
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Run tests", "run": "pytest tests/ -v"},
                ]
            }
        
        if include_deploy:
            jobs["deploy"] = {
                "runs-on": "ubuntu-latest",
                "needs": ["test"],
                "environment": "production",
            }
        
        return {
            "name": "CI",
            "on": ["push", "pull_request"],
            "jobs": jobs,
        }
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "platform" in input


class DeploymentGeneratorTool(BaseTool):
    name = "deployment_generate"
    description = "Generate Kubernetes deployment manifests with containers, configmaps, secrets"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        name = input.args.get("name", "app")
        replicas = input.args.get("replicas", 3)
        image = input.args.get("image", f"{name}:latest")
        port = input.args.get("port", 8000)
        env = input.args.get("env", {})
        service_type = input.args.get("service_type", "ClusterIP")
        
        try:
            manifest = await self._generate_deployment_llm(
                name, replicas, image, port, env, service_type
            )
            return ToolOutput(
                result={"manifest": manifest},
                metadata={"generated": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM deployment generation failed: {e}, using fallback")
            manifest = await self._generate_deployment_fallback(
                name, replicas, image, port, env, service_type
            )
            return ToolOutput(
                result={"manifest": manifest},
                metadata={"generated": True, "method": "fallback", "error": str(e)}
            )
    
    async def _generate_deployment_llm(
        self,
        name: str,
        replicas: int,
        image: str,
        port: int,
        env: Dict[str, str],
        service_type: str
    ) -> Dict[str, Any]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Generate a production-ready Kubernetes deployment manifest.
App name: {name}
Replicas: {replicas}
Image: {image}
Container port: {port}
Environment variables: {json.dumps(env)}
Service type: {service_type}

Respond ONLY with a JSON object containing:
- deployment: apps/v1 Deployment spec
- service: v1 Service spec  
- configmap: v1 ConfigMap (if env vars)
- ingress: networking.k8s.io/v1 Ingress (optional)

Use best practices: security context, resource limits, liveness/readiness probes."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2500
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM deployment generation failed: {e}")
            raise
    
    async def _generate_deployment_fallback(
        self,
        name: str,
        replicas: int,
        image: str,
        port: int,
        env: Dict[str, str],
        service_type: str
    ) -> Dict[str, Any]:
        resources = {
            "limits": {"cpu": "500m", "memory": "512Mi"},
            "requests": {"cpu": "100m", "memory": "128Mi"},
        }
        
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": name},
            "spec": {
                "replicas": replicas,
                "selector": {"matchLabels": {"app": name}},
                "template": {
                    "metadata": {"labels": {"app": name}},
                    "spec": {
                        "containers": [{
                            "name": name,
                            "image": image,
                            "ports": [{"containerPort": port, "name": "http"}],
                            "env": [{"name": k, "value": v} for k, v in env.items()],
                            "resources": resources,
                            "livenessProbe": {
                                "httpGet": {"path": "/health", "port": port},
                                "initialDelaySeconds": 30,
                                "periodSeconds": 10,
                            },
                            "readinessProbe": {
                                "httpGet": {"path": "/ready", "port": port},
                                "initialDelaySeconds": 5,
                                "periodSeconds": 5,
                            },
                        }]
                    }
                }
            }
        }
        
        service = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": name},
            "spec": {
                "selector": {"app": name},
                "ports": [{"port": port, "targetPort": port, "name": "http"}],
                "type": service_type,
            }
        }
        
        result = {"deployment": deployment, "service": service}
        
        if env:
            result["configmap"] = {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {"name": f"{name}-config"},
                "data": env,
            }
        
        return result
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "name" in input


class HelmChartGeneratorTool(BaseTool):
    name = "helm_chart_generate"
    description = "Generate Helm chart with templates, values, Chart.yaml"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        name = input.args.get("name", "chart")
        description = input.args.get("description", f"Helm chart for {name}")
        version = input.args.get("version", "0.1.0")
        app_version = input.args.get("app_version", "latest")
        
        try:
            chart = await self._generate_helm_chart_llm(
                name, description, version, app_version
            )
            return ToolOutput(
                result={"chart": chart},
                metadata={"generated": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM helm chart generation failed: {e}, using fallback")
            chart = await self._generate_helm_chart_fallback(
                name, description, version, app_version
            )
            return ToolOutput(
                result={"chart": chart},
                metadata={"generated": True, "method": "fallback", "error": str(e)}
            )
    
    async def _generate_helm_chart_llm(
        self,
        name: str,
        description: str,
        version: str,
        app_version: str
    ) -> Dict[str, Any]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Generate a Helm chart structure for {name}.
Description: {description}
Chart version: {version}
App version: {app_version}

Respond ONLY with a JSON object containing:
- Chart.yaml: apiVersion, name, version, appVersion, description
- values.yaml: common values (replicaCount, image, service, resources)
- templates/: deployment.yaml, service.yaml, ingress.yaml, _helpers.tpl

Use production best practices."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2500
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM helm chart generation failed: {e}")
            raise
    
    async def _generate_helm_chart_fallback(
        self,
        name: str,
        description: str,
        version: str,
        app_version: str
    ) -> Dict[str, Any]:
        chart_yaml = {
            "apiVersion": "v2",
            "name": name,
            "version": version,
            "appVersion": app_version,
            "description": description,
        }
        
        values = {
            "replicaCount": 3,
            "image": {
                "repository": name,
                "pullPolicy": "IfNotPresent",
            },
            "service": {
                "type": "ClusterIP",
                "port": 80,
            },
            "resources": {
                "limits": {"cpu": "500m", "memory": "512Mi"},
                "requests": {"cpu": "100m", "memory": "128Mi"},
            },
        }
        
        return {
            "Chart.yaml": chart_yaml,
            "values.yaml": values,
        }
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "name" in input


class TerraformGeneratorTool(BaseTool):
    name = "terraform_generate"
    description = "Generate Terraform IaC for cloud resources"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        provider = input.args.get("provider", "aws")
        resources = input.args.get("resources", ["ecs", "rds", "s3"])
        
        try:
            terraform = await self._generate_terraform_llm(provider, resources)
            return ToolOutput(
                result={"terraform": terraform},
                metadata={"generated": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM terraform generation failed: {e}, using fallback")
            terraform = await self._generate_terraform_fallback(provider, resources)
            return ToolOutput(
                result={"terraform": terraform},
                metadata={"generated": True, "method": "fallback", "error": str(e)}
            )
    
    async def _generate_terraform_llm(
        self,
        provider: str,
        resources: List[str]
    ) -> Dict[str, Any]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Generate Terraform IaC for {provider}.
Resources: {', '.join(resources)}

Respond ONLY with a JSON object containing:
- main.tf: provider config, resource blocks
- variables.tf: variable definitions
- outputs.tf: output definitions
- versions.tf: backend and provider versions

Use production best practices: modules, remote state, outputs."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2500
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM terraform generation failed: {e}")
            raise
    
    async def _generate_terraform_fallback(
        self,
        provider: str,
        resources: List[str]
    ) -> Dict[str, Any]:
        return {
            "provider": provider,
            f"{provider.lower()}_provider": {
                "provider": f'"{provider.lower()}"',
                "region": "us-east-1",
            },
        }
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "provider" in input


class DockerComposeGeneratorTool(BaseTool):
    name = "docker_compose_generate"
    description = "Generate docker-compose files with multi-service support"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        services = input.args.get("services", ["api"])
        includes = input.args.get("includes", ["db", "redis"])
        
        try:
            compose = await self._generate_compose_llm(services, includes)
            return ToolOutput(
                result={"compose": compose},
                metadata={"generated": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM compose generation failed: {e}, using fallback")
            compose = await self._generate_compose_fallback(services, includes)
            return ToolOutput(
                result={"compose": compose},
                metadata={"generated": True, "method": "fallback", "error": str(e)}
            )
    
    async def _generate_compose_llm(
        self,
        services: List[str],
        includes: List[str]
    ) -> Dict[str, Any]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Generate a docker-compose.yaml.
Services: {', '.join(services)}
Includes: {', '.join(includes)}

Respond ONLY with a valid docker-compose JSON object.
Include: version, services, (networks, volumes if needed).
Use healthchecks, restart policies, proper port mappings."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM compose generation failed: {e}")
            raise
    
    async def _generate_compose_fallback(
        self,
        services: List[str],
        includes: List[str]
    ) -> Dict[str, Any]:
        compose = {
            "version": "3.8",
            "services": {},
        }
        
        for s in services:
            compose["services"][s] = {
                "image": f"{s}:latest",
                "restart": "unless-stopped",
            }
        
        if "db" in includes:
            compose["services"]["db"] = {
                "image": "postgres:15",
                "environment": {"POSTGRES_PASSWORD": "secret"},
                "volumes": ["db-data:/var/lib/postgresql/data"],
                "healthcheck": {
                    "test": ["CMD-SHELL", "pg_isready"],
                    "interval": "10s",
                    "timeout": "5s",
                },
            }
        
        if "redis" in includes:
            compose["services"]["redis"] = {
                "image": "redis:7-alpine",
                "healthcheck": {
                    "test": ["CMD", "redis-cli", "ping"],
                    "interval": "10s",
                },
            }
        
        compose["volumes"] = {"db-data": None}
        
        return compose
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "services" in input


class DeploymentValidatorTool(BaseTool):
    name = "deployment_validate"
    description = "Validate Kubernetes manifests, Terraform, Docker Compose"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        config = input.args.get("config", {})
        config_type = input.args.get("type", "kubernetes")
        
        try:
            validation = await self._validate_deployment_llm(config, config_type)
            return ToolOutput(
                result=validation,
                metadata={"validated": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM validation failed: {e}, using fallback")
            validation = await self._validate_deployment_fallback(config, config_type)
            return ToolOutput(
                result=validation,
                metadata={"validated": True, "method": "fallback", "error": str(e)}
            )
    
    async def _validate_deployment_llm(
        self,
        config: Dict[str, Any],
        config_type: str
    ) -> Dict[str, Any]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Validate this {config_type} configuration.
Config: {json.dumps(config)}

Respond ONLY with a JSON object containing:
- valid: boolean
- issues: array of issue objects with severity (error/warning), message, field
- suggestions: array of fix suggestions

Be strict: catch missing required fields, invalid values, security issues."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.2,
                max_tokens=1500
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            raise
    
    async def _validate_deployment_fallback(
        self,
        config: Dict[str, Any],
        config_type: str
    ) -> Dict[str, Any]:
        issues = []
        
        if config_type == "kubernetes":
            if not config.get("apiVersion"):
                issues.append({
                    "severity": "error",
                    "message": "Missing apiVersion",
                    "field": "apiVersion"
                })
            if not config.get("kind"):
                issues.append({
                    "severity": "error", 
                    "message": "Missing kind",
                    "field": "kind"
                })
        
        elif config_type == "terraform":
            if not config.get("provider"):
                issues.append({
                    "severity": "warning",
                    "message": "No provider specified",
                    "field": "provider"
                })
        
        elif config_type == "docker":
            if not config.get("services"):
                issues.append({
                    "severity": "error",
                    "message": "No services defined",
                    "field": "services"
                })
        
        return {
            "valid": len([i for i in issues if i.get("severity") == "error"]) == 0,
            "issues": issues,
        }
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "config" in input or "type" in input


def register_deployment_tools(registry) -> None:
    registry.register(CICDPipelineGeneratorTool())
    registry.register(DeploymentGeneratorTool())
    registry.register(HelmChartGeneratorTool())
    registry.register(TerraformGeneratorTool())
    registry.register(DockerComposeGeneratorTool())
    registry.register(DeploymentValidatorTool())