from typing import Any, Dict, List, Optional
from core.adapters.base import AdapterInput, AdapterOutput, PlatformAdapter, AdapterRegistry, get_adapter_registry
from core.patterns.schema import Pattern, get_pattern_library
from core.constraints.engine import get_constraint_engine
from models.ir import IRFeature, PlatformContext


class VMwareTanzuAdapter(PlatformAdapter):
    @property
    def platform_id(self) -> str:
        return "tanzu"
    
    @property
    def supported_services(self) -> List[str]:
        return [
            "spring-boot",
            "spring-cloud-function",
            "app-service",
            "build-service",
            "service-bindings",
            "knative",
            "eventing",
            "ingress",
            "cert-manager",
            "observability-service",
            "spring-cloud-dataflow",
            "rabbitmq",
            "redis",
            "postgres",
        ]
    
    @property
    def patterns(self) -> List[Pattern]:
        library = get_pattern_library()
        
        tanzu_patterns = [
            Pattern(
                id="tanzu_spring_boot",
                name="Spring Boot Application",
                domain="architecture",
                triggers=["spring", "boot", "java"],
                conditions=[],
                components=["spring-boot-app"],
                benefits=["Enterprise Java", "Spring ecosystem", "Auto-config"],
                tradeoffs=["Memory footprint", "Startup time"],
                priority=9,
                confidence=0.9,
            ),
            Pattern(
                id="tanzu_scf",
                name="Spring Cloud Functions",
                domain="architecture",
                triggers=["scf", "spring-cloud", "function"],
                conditions=[],
                components=["spring-cloud-function"],
                benefits=["Serverless", "Event-driven", "Cloud-native"],
                tradeoffs=["Debugging complexity"],
                priority=8,
                confidence=0.8,
            ),
            Pattern(
                id="tanzu_knative",
                name="Knative Serving",
                domain="architecture",
                triggers=["knative", "serverless", "k-service"],
                conditions=[],
                components=["knative-service"],
                benefits=["Auto-scaling", "Scale-to-zero", "URL routing"],
                tradeoffs=["Kubernetes knowledge required"],
                priority=9,
                confidence=0.85,
            ),
            Pattern(
                id="tanzu_knative_eventing",
                name="Knative Eventing",
                domain="architecture",
                triggers=["knative-eventing", "eventing"],
                conditions=[],
                components=["event-source", "broker", "trigger"],
                benefits=["Event decoupling", "Multi-source"],
                tradeoffs=["Event schema management"],
                priority=8,
                confidence=0.8,
            ),
            Pattern(
                id="tanzu_service_binding",
                name="Tanzu Service Bindings",
                domain="architecture",
                triggers=["service-binding", "spring-cloud"],
                conditions=[],
                components=["service-binding"],
                benefits=["12-factor", "No credentials in code"],
                tradeoffs=["Service operator coordination"],
                priority=9,
                confidence=0.9,
            ),
        ]
        
        for p in tanzu_patterns:
            library.register(p)
        
        return tanzu_patterns
    
    @property
    def constraints(self) -> Any:
        return get_constraint_engine()._constraint_sets.get("tanzu")
    
    def transform_ir_to_platform(self, input: AdapterInput) -> AdapterOutput:
        features = input.ir_features
        pattern_results = input.pattern_matches
        violations = input.constraint_violations
        
        config_templates = self.generate_config(features)
        code_snippets = self.generate_code(features)
        
        recommendations = self._build_recommendations(
            pattern_results,
            features,
            violations
        )
        
        can_deploy = not any(
            v.severity == "error" for v in violations
        )
        
        confidence = sum(p.match_score for p in pattern_results) / max(1, len(pattern_results))
        
        return AdapterOutput(
            recommendations=recommendations,
            config_templates=config_templates,
            code_snippets=code_snippets,
            explanation=self._explain(recommendations, violations),
            confidence=confidence,
            can_deploy=can_deploy,
        )
    
    def generate_config(self, features: IRFeature) -> Dict[str, str]:
        configs = {}
        
        if features.has_serverless:
            configs["knative-service.yaml"] = self._generate_knative_service(features)
        else:
            configs["deployment.yaml"] = self._generate_deployment(features)
        
        configs["config.yaml"] = self._generate_configmap(features)
        
        if features.has_event_driven:
            configs["eventing-broker.yaml"] = self._generate_eventing_broker(features)
        
        return configs
    
    def generate_code(self, features: IRFeature) -> Dict[str, str]:
        code = {}
        
        if features.has_serverless:
            code["function.java"] = self._generate_function_code()
        else:
            code["Application.java"] = self._generate_spring_app_code()
            
        if features.has_database:
            code["pom.xml"] = self._generate_pom_xml()
        
        return code
    
    def _generate_knative_service(self, features: IRFeature) -> str:
        return '''apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: my-tanzu-app
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "0"
        autoscaling.knative.dev/maxScale: "10"
    spec:
      containers:
        - image: my-registry/my-tanzu-app:v1
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
          ports:
            - containerPort: 8080
'''
    
    def _generate_deployment(self, features: IRFeature) -> str:
        return '''apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-tanzu-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-tanzu-app
  template:
    metadata:
      labels:
        app: my-tanzu-app
    spec:
      containers:
        - name: app
          image: my-registry/my-tanzu-app:v1
          ports:
            - containerPort: 8080
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
'''
    
    def _generate_configmap(self, features: IRFeature) -> str:
        return '''apiVersion: v1
kind: ConfigMap
metadata:
  name: my-tanzu-app-config
data:
  application.properties: |
    server.port=8080
    spring.profiles.active=cloud
'''
    
    def _generate_eventing_broker(self, features: IRFeature) -> str:
        return '''apiVersion: eventing.knative.dev/v1
kind: Broker
metadata:
  name: my-app-broker
---
apiVersion: eventing.knative.dev/v1
kind: Trigger
metadata:
  name: my-app-trigger
spec:
  broker: my-app-broker
  subscriber:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      name: my-tanzu-app
'''
    
    def _generate_function_code(self) -> str:
        return '''package com.example;

import java.util.function.Function;

public class MyFunction implements Function<String, String> {
    @Override
    public String apply(String input) {
        return "Processed: " + input;
    }
}
'''
    
    def _generate_spring_app_code(self) -> str:
        return '''package com.example;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
@RestController
public class Application {
    
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
    
    @GetMapping("/")
    public String hello() {
        return "Hello from Tanzu!";
    }
}
'''
    
    def _generate_pom_xml(self) -> str:
        return '''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.example</groupId>
    <artifactId>my-tanzu-app</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>
    
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.0</version>
    </parent>
    
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-actuator</artifactId>
        </dependency>
    </dependencies>
    
    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
'''
    
    def _build_recommendations(
        self,
        pattern_results: List[Any],
        features: IRFeature,
        violations: List[Any]
    ) -> List[Dict[str, Any]]:
        recommendations = []
        
        for pattern_result in pattern_results[:3]:
            pattern = getattr(pattern_result, "pattern", None)
            if pattern:
                recommendations.append({
                    "name": pattern.name,
                    "reason": f"Matched {len(pattern_result.matched_conditions)} conditions",
                    "score": pattern_result.match_score,
                })
        
        for violation in violations:
            recommendations.append({
                "name": "Fix Required",
                "reason": violation.message,
                "severity": violation.severity,
                "fix": violation.fix_hint,
            })
        
        return recommendations
    
    def _explain(
        self,
        recommendations: List[Dict[str, Any]],
        violations: List[Any]
    ) -> str:
        parts = []
        
        if recommendations:
            best = recommendations[0]
            parts.append(f"Recommended: {best.get('name', 'Unknown')}")
        
        if violations:
            errors = [v for v in violations if v.severity == "error"]
            if errors:
                parts.append(f"Blocking issues: {len(errors)}")
        
        return " | ".join(parts) if parts else "Analysis complete"


def register_tanzu_adapter(registry=None):
    if registry:
        registry.register(VMwareTanzuAdapter())