from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel


class PDLCPhase(str, Enum):
    IDEATION = "ideation"
    BUSINESS_REQUIREMENTS = "business_requirements"
    ARCHITECTURE_DESIGN = "architecture_design"
    CODING = "coding"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    PRODUCTION_OBSERVABILITY = "production_observability"
    FEEDBACK_LOOP = "feedback_loop"
    DAY2_OPERATIONS = "day2_operations"


class MCPErrorCode:
    TOOL_NOT_FOUND = -32001
    INVALID_PARAMS = -32002
    EXECUTION_FAILED = -32003
    RATELIMITED = -32004
    RESOURCE_NOT_FOUND = -32005
    PROMPT_NOT_FOUND = -32006


class ToolInput(BaseModel):
    args: Dict[str, Any]


class ToolOutput(BaseModel):
    result: Any
    error: Optional[str] = None
    metadata: Dict[str, Any]


class BaseTool(ABC):
    name: str
    description: str
    phase: PDLCPhase = PDLCPhase.CODING

    @abstractmethod
    async def execute(self, input: ToolInput) -> ToolOutput:
        pass

    @abstractmethod
    def validate_input(self, input: Dict[str, Any]) -> bool:
        pass


class ArchitectureEvaluator(BaseTool):
    name = "architecture_evaluate"
    description = (
        "Evaluate architecture design for quality, consistency, and best practices"
    )

    PATTERNS_SCORES = {
        "microservices": {"correctness": 0.85, "consistency": 0.9, "best_practices": 0.88},
        "serverless": {"correctness": 0.9, "consistency": 0.85, "best_practices": 0.92},
        "monolith": {"correctness": 0.95, "consistency": 0.95, "best_practices": 0.7},
        "event-driven": {"correctness": 0.82, "consistency": 0.88, "best_practices": 0.85},
        "cqrs": {"correctness": 0.88, "consistency": 0.82, "best_practices": 0.9},
        "default": {"correctness": 0.8, "consistency": 0.8, "best_practices": 0.8},
    }

    async def execute(self, input: ToolInput) -> ToolOutput:
        architecture_id = input.args.get("architecture_id", "")
        criteria = input.args.get(
            "criteria", ["correctness", "consistency", "best_practices"]
        )

        arch_lower = architecture_id.lower()
        scores = {}
        for c in criteria:
            matched = False
            for pattern, pattern_scores in self.PATTERNS_SCORES.items():
                if pattern in arch_lower:
                    scores[c] = pattern_scores.get(c, 0.8)
                    matched = True
                    break
            if not matched:
                scores[c] = self.PATTERNS_SCORES["default"].get(c, 0.8)

        issues = []
        recommendations = []

        if scores.get("best_practices", 0) < 0.85:
            issues.append("Architecture may not follow current best practices")
            recommendations.append("Consider adopting modern architectural patterns")

        if scores.get("consistency", 0) < 0.85:
            issues.append("Architecture consistency could be improved")
            recommendations.append("Standardize component interactions and data flow")

        avg_score = sum(scores.values()) / len(scores) if scores else 0.8
        if avg_score < 0.75:
            issues.append("Overall architecture score below threshold")
            recommendations.append("Review architecture against industry standards")

        result = {
            "architecture_id": architecture_id,
            "scores": scores,
            "issues": issues,
            "recommendations": recommendations,
        }

        return ToolOutput(result=result, metadata={"evaluated": True})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "architecture_id" in input


class SecurityValidator(BaseTool):
    name = "security_validate"
    description = "Validate security aspects of code or architecture"

    VULNERABILITY_PATTERNS = [
        (r"password\s*=\s*['\"][^'\"]{0,8}['\"]", "Hardcoded password detected"),
        (r"api[_-]?key\s*=\s*['\"][A-Za-z0-9]{20,}['\"]", "Potential hardcoded API key"),
        (r"eval\s*\(", "Use of eval() is a security risk"),
        (r"exec\s*\(", "Use of exec() is a security risk"),
        (r"__import__\s*\(", "Dynamic imports can be a security risk"),
        (r"os\.system\s*\(", "Shell commands via os.system are risky"),
        (r"subprocess\.run\s*\([^,]+shell\s*=\s*True", "Shell injection vulnerability"),
        (r"SELECT\s+\*\s+FROM", "SELECT * may expose sensitive data"),
        (r"GRANT\s+ALL", "Overly permissive database grant"),
        (r"\.\.\/", "Potential path traversal"),
    ]

    async def execute(self, input: ToolInput) -> ToolOutput:
        target = input.args.get("target", "")
        target_type = input.args.get("target_type", "code")
        content = input.args.get("content", "")

        vulnerabilities = []

        if content:
            import re
            for pattern, description in self.VULNERABILITY_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    vulnerabilities.append({
                        "type": "pattern_match",
                        "description": description,
                        "severity": "medium" if "sql" in description.lower() else "low",
                    })

        if target_type == "code":
            if len(content) > 10000:
                vulnerabilities.append({
                    "type": "size_check",
                    "description": "Large code file may need additional review",
                    "severity": "info",
                })

        passed = len([v for v in vulnerabilities if v.get("severity") != "info"]) == 0

        result = {
            "target": target,
            "target_type": target_type,
            "vulnerabilities": vulnerabilities,
            "passed": passed,
        }

        return ToolOutput(result=result, metadata={"validated": True})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "target" in input and "target_type" in input


class CostEstimator(BaseTool):
    name = "cost_estimate"
    description = "Estimate infrastructure and operational costs"

    TRAFFIC_MULTIPLIERS = {
        "low": 0.5,
        "medium": 1.0,
        "high": 2.5,
        "enterprise": 5.0,
    }

    BASE_COSTS = {
        "compute": {"low": 50, "medium": 150, "high": 400, "enterprise": 800},
        "storage": {"low": 25, "medium": 75, "high": 200, "enterprise": 500},
        "network": {"low": 15, "medium": 50, "high": 150, "enterprise": 350},
        "other": {"low": 10, "medium": 30, "high": 80, "enterprise": 150},
    }

    def _estimate_by_architecture(self, architecture_id: str) -> Dict[str, float]:
        arch_lower = architecture_id.lower()
        if "serverless" in arch_lower or "lambda" in arch_lower:
            return {"compute": 30, "storage": 60, "network": 40, "other": 20}
        elif "kubernetes" in arch_lower or "eks" in arch_lower or "gke" in arch_lower:
            return {"compute": 300, "storage": 100, "network": 80, "other": 50}
        elif "vm" in arch_lower or "virtual" in arch_lower:
            return {"compute": 100, "storage": 80, "network": 50, "other": 30}
        elif "saas" in arch_lower or "managed" in arch_lower:
            return {"compute": 150, "storage": 100, "network": 60, "other": 40}
        return {"compute": 100, "storage": 75, "network": 50, "other": 25}

    async def execute(self, input: ToolInput) -> ToolOutput:
        architecture_id = input.args.get("architecture_id", "")
        traffic_estimate = input.args.get("traffic_estimate", "medium").lower()

        multiplier = self.TRAFFIC_MULTIPLIERS.get(traffic_estimate, 1.0)
        base_by_arch = self._estimate_by_architecture(architecture_id)

        breakdown = {
            category: int(base * multiplier)
            for category, base in base_by_arch.items()
        }

        total = sum(breakdown.values())

        result = {
            "architecture_id": architecture_id,
            "traffic_estimate": traffic_estimate,
            "estimated_monthly_cost": total,
            "currency": "USD",
            "breakdown": breakdown,
        }

        return ToolOutput(result=result, metadata={"estimated": True})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "architecture_id" in input


class SearchTool(BaseTool):
    name = "search"
    description = "Search across all document and code sources"

    async def execute(self, input: ToolInput) -> ToolOutput:
        query = input.args.get("query", "")
        limit = input.args.get("limit", 10)

        try:
            from retrieval.hybrid import get_hybrid_retriever

            retriever = get_hybrid_retriever()
            result = await retriever.search(query, limit=limit)
            return ToolOutput(result=result, metadata={"searched": True})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "query" in input


class HybridSearchTool(BaseTool):
    name = "hybrid_search"
    description = "Advanced hybrid search with reasoning and reranking"

    async def execute(self, input: ToolInput) -> ToolOutput:
        query = input.args.get("query", "")
        limit = input.args.get("limit", 10)
        use_reasoning = input.args.get("use_reasoning", True)

        try:
            from retrieval.hybrid import get_enhanced_hybrid_retriever

            retriever = get_enhanced_hybrid_retriever()
            result = await retriever.search_with_enhanced_reasoning(
                query, limit=limit, use_entity_reasoning=use_reasoning
            )
            return ToolOutput(result=result, metadata={"searched": True})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "query" in input


class RerankTool(BaseTool):
    name = "rerank"
    description = "Rerank search results using ML models"

    async def execute(self, input: ToolInput) -> ToolOutput:
        query = input.args.get("query", "")
        results = input.args.get("results", [])

        try:
            from retrieval.rerank import get_rerank_pipeline

            pipeline = get_rerank_pipeline()
            reranked = await pipeline.rerank(query, results)
            return ToolOutput(
                result={"reranked": [r.dict() for r in reranked]},
                metadata={"reranked": True},
            )
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "query" in input and "results" in input


class ChainReasoningTool(BaseTool):
    name = "chain_reasoning"
    description = "Execute chain-of-thoughts reasoning on facts"

    async def execute(self, input: ToolInput) -> ToolOutput:
        query = input.args.get("query", "")
        facts = input.args.get("facts", [])

        try:
            from retrieval.reasoning import get_reasoning_engine, ReasoningMode

            engine = get_reasoning_engine(ReasoningMode.CHAIN_OF_THOUGHTS)
            result = await engine.reason(query, facts)
            return ToolOutput(result=result, metadata={"reasoned": True})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "query" in input and "facts" in input


class EntityReasoningTool(BaseTool):
    name = "entity_reasoning"
    description = "Entity-aware reasoning with graph traversal"

    async def execute(self, input: ToolInput) -> ToolOutput:
        query = input.args.get("query", "")
        facts = input.args.get("facts", [])
        entity_graph = input.args.get("entity_graph", None)

        try:
            from retrieval.reasoning.entity_aware import (
                get_entity_aware_reasoning_engine,
            )

            engine = get_entity_aware_reasoning_engine()
            result = await engine.reason(query, facts, entity_graph)
            return ToolOutput(result=result, metadata={"reasoned": True})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "query" in input


class IterativeReasoningTool(BaseTool):
    name = "iterative_reasoning"
    description = "Iterative retrieval with query refinement"

    async def execute(self, input: ToolInput) -> ToolOutput:
        query = input.args.get("query", "")
        max_iterations = input.args.get("max_iterations", 3)

        try:
            from retrieval.hybrid import get_hybrid_retriever
            from retrieval.reasoning.iterative import get_iterative_reasoning_engine

            retriever = get_hybrid_retriever()

            async def retriever_fn(q):
                result = await retriever.search(q, limit=10)
                return result.get("results", [])

            engine = get_iterative_reasoning_engine(max_iterations=max_iterations)
            result = await engine.retrieve(query, retriever_fn)
            return ToolOutput(result=result, metadata={"reasoned": True})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "query" in input


class GraphQueryTool(BaseTool):
    name = "query_graph"
    description = "Query knowledge graph for relationships"

    async def execute(self, input: ToolInput) -> ToolOutput:
        query = input.args.get("query", "")
        limit = input.args.get("limit", 10)

        try:
            from retrieval.graph import get_graph_retriever

            retriever = get_graph_retriever()
            result = await retriever.search(query, limit=limit)
            return ToolOutput(result=result, metadata={"queried": True})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "query" in input


class EntitySearchTool(BaseTool):
    name = "entity_search"
    description = "Search by entity name with graph traversal and cache"

    async def execute(self, input: ToolInput) -> ToolOutput:
        entity_name = input.args.get("entity_name", "")
        depth = input.args.get("depth", 2)
        limit = input.args.get("limit", 10)

        try:
            from retrieval.hybrid import get_enhanced_hybrid_retriever

            retriever = get_enhanced_hybrid_retriever()
            result = await retriever.search_with_enhanced_reasoning(
                f"entity {entity_name}",
                limit=limit,
                use_entity_reasoning=True,
            )
            return ToolOutput(result=result, metadata={"searched": True})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "entity_name" in input


class IngestSourceTool(BaseTool):
    name = "ingest_source"
    description = "Ingest content from a source"

    async def execute(self, input: ToolInput) -> ToolOutput:
        source_type = input.args.get("source_type", "documents")
        content = input.args.get("content", "")
        metadata = input.args.get("metadata", {})

        try:
            from ingestion.orchestrator import IngestionCoordinator, IngestionSource

            coordinator = IngestionCoordinator()
            result = await coordinator.ingest_all(
                sources=[IngestionSource(source_type)],
                mode=None,
            )
            return ToolOutput(result=result, metadata={"ingested": True})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "source_type" in input


class GetJobStatusTool(BaseTool):
    name = "get_job_status"
    description = "Get status of ingestion job"

    async def execute(self, input: ToolInput) -> ToolOutput:
        job_id = input.args.get("job_id", "")

        try:
            from ingestion.pipeline import get_ingestion_pipeline

            pipeline = get_ingestion_pipeline()
            job = pipeline.get_job(job_id)
            if job:
                result = {
                    "job_id": job.job_id,
                    "status": job.status.value,
                    "progress": job.progress,
                    "error": job.error,
                }
                return ToolOutput(result=result, metadata={"checked": True})
            return ToolOutput(result=None, error="Job not found", metadata={})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "job_id" in input


class KubernetesSearchTool(BaseTool):
    name = "kubernetes_search"
    description = "Search Kubernetes manifests"

    async def execute(self, input: ToolInput) -> ToolOutput:
        try:
            from retrieval.tooling import get_kubernetes_retriever
            retriever = get_kubernetes_retriever()
            result = await retriever.search(
                query=input.args.get("query", ""),
                limit=input.args.get("limit", 10),
                kind=input.args.get("kind"),
                namespace=input.args.get("namespace"),
            )
            return ToolOutput(result=result, metadata={"source": "kubernetes"})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "query" in input


class HelmSearchTool(BaseTool):
    name = "helm_search"
    description = "Search Helm charts"

    async def execute(self, input: ToolInput) -> ToolOutput:
        try:
            from retrieval.tooling import get_helm_retriever
            retriever = get_helm_retriever()
            result = await retriever.search(
                query=input.args.get("query", ""),
                limit=input.args.get("limit", 10),
                chart_name=input.args.get("chart_name"),
            )
            return ToolOutput(result=result, metadata={"source": "helm"})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "query" in input


class DockerfileSearchTool(BaseTool):
    name = "dockerfile_search"
    description = "Search Dockerfiles"

    async def execute(self, input: ToolInput) -> ToolOutput:
        try:
            from retrieval.tooling import get_dockerfile_retriever
            retriever = get_dockerfile_retriever()
            result = await retriever.search(
                query=input.args.get("query", ""),
                limit=input.args.get("limit", 10),
                instruction=input.args.get("instruction"),
            )
            return ToolOutput(result=result, metadata={"source": "dockerfile"})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "query" in input


class GraphQLSearchTool(BaseTool):
    name = "graphql_search"
    description = "Search GraphQL schemas"

    async def execute(self, input: ToolInput) -> ToolOutput:
        try:
            from retrieval.tooling import get_graphql_retriever
            retriever = get_graphql_retriever()
            result = await retriever.search(
                query=input.args.get("query", ""),
                limit=input.args.get("limit", 10),
                kind=input.args.get("kind"),
            )
            return ToolOutput(result=result, metadata={"source": "graphql"})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "query" in input


class IstioSearchTool(BaseTool):
    name = "istio_search"
    description = "Search Istio resources"

    async def execute(self, input: ToolInput) -> ToolOutput:
        try:
            from retrieval.tooling import get_istio_retriever
            retriever = get_istio_retriever()
            result = await retriever.search(
                query=input.args.get("query", ""),
                limit=input.args.get("limit", 10),
                kind=input.args.get("kind"),
                namespace=input.args.get("namespace"),
            )
            return ToolOutput(result=result, metadata={"source": "istio"})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "query" in input


class FindCallersTool(BaseTool):
    name = "find_callers"
    description = "Find functions that call a function"

    async def execute(self, input: ToolInput) -> ToolOutput:
        try:
            from retrieval.code_graph import get_code_graph_retriever
            retriever = get_code_graph_retriever()
            result = await retriever.find_callers(
                function_name=input.args.get("function_name", ""),
                limit=input.args.get("limit", 20),
            )
            return ToolOutput(result=result, metadata={"method": "find_callers"})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "function_name" in input


class FindCalleesTool(BaseTool):
    name = "find_callees"
    description = "Find functions called by a function"

    async def execute(self, input: ToolInput) -> ToolOutput:
        try:
            from retrieval.code_graph import get_code_graph_retriever
            retriever = get_code_graph_retriever()
            result = await retriever.find_callees(
                function_name=input.args.get("function_name", ""),
                limit=input.args.get("limit", 20),
            )
            return ToolOutput(result=result, metadata={"method": "find_callees"})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "function_name" in input


class FindDeadCodeTool(BaseTool):
    name = "find_dead_code"
    description = "Find unused code"

    async def execute(self, input: ToolInput) -> ToolOutput:
        try:
            from retrieval.code_graph import get_code_graph_retriever
            retriever = get_code_graph_retriever()
            result = await retriever.search(
                query="unused",
                method="dead_code",
                limit=input.args.get("limit", 20),
            )
            return ToolOutput(result=result, metadata={"method": "dead_code"})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return True


class GetComplexityTool(BaseTool):
    name = "get_complexity"
    description = "Get function complexity"

    async def execute(self, input: ToolInput) -> ToolOutput:
        try:
            from retrieval.code_graph import get_code_graph_retriever
            retriever = get_code_graph_retriever()
            function_name = input.args.get("function_name", "")
            result = await retriever.search(
                query=f"complexity {function_name}",
                method="complexity",
                limit=1,
            )
            return ToolOutput(result=result, metadata={"method": "complexity"})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "function_name" in input


class ClassHierarchyTool(BaseTool):
    name = "class_hierarchy"
    description = "Get class hierarchy"

    async def execute(self, input: ToolInput) -> ToolOutput:
        try:
            from retrieval.code_graph import get_code_graph_retriever
            retriever = get_code_graph_retriever()
            class_name = input.args.get("class_name", "")
            result = await retriever.search(
                query=f"class {class_name}",
                method="class_hierarchy",
                limit=input.args.get("limit", 10),
            )
            return ToolOutput(result=result, metadata={"method": "class_hierarchy"})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "class_name" in input


class GetModuleDepsTool(BaseTool):
    name = "get_module_deps"
    description = "Get module dependencies"

    async def execute(self, input: ToolInput) -> ToolOutput:
        try:
            from retrieval.code_graph import get_code_graph_retriever
            retriever = get_code_graph_retriever()
            module = input.args.get("module", "")
            result = await retriever.search(
                query=f"modules {module}",
                method="module_deps",
                limit=input.args.get("limit", 10),
            )
            return ToolOutput(result=result, metadata={"method": "module_deps"})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return True


class ExtractFromImageTool(BaseTool):
    name = "extract_from_image"
    description = "Extract text from images using VLM"

    async def execute(self, input: ToolInput) -> ToolOutput:
        try:
            from multimodal.vlm import get_vlm_provider
            provider = get_vlm_provider()
            if not provider:
                return ToolOutput(result=None, error="No VLM provider configured", metadata={})
            result = await provider.extract_text(
                image_url=input.args.get("image_url", ""),
            )
            return ToolOutput(result={"extracted_text": result}, metadata={"source": "vlm"})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "image_url" in input


class AnalyzeVisualTool(BaseTool):
    name = "analyze_visual"
    description = "Analyze images/diagrams using VLM"

    async def execute(self, input: ToolInput) -> ToolOutput:
        try:
            from multimodal.vlm import get_vlm_provider
            provider = get_vlm_provider()
            if not provider:
                return ToolOutput(result=None, error="No VLM provider configured", metadata={})
            result = await provider.analyze_image(
                image_url=input.args.get("image_url", ""),
                prompt=input.args.get("prompt", "Describe this image"),
            )
            return ToolOutput(result=result, metadata={"source": "vlm"})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "image_url" in input and "prompt" in input


class ParseDocumentAdvancedTool(BaseTool):
    name = "parse_document_advanced"
    description = "Parse documents with OCR using Docling"

    async def execute(self, input: ToolInput) -> ToolOutput:
        try:
            from documents.parse import get_document_parser
            parser = get_document_parser()
            file_path = input.args.get("file_path")
            url = input.args.get("url")
            use_ocr = input.args.get("use_ocr", True)
            if file_path:
                result = await parser.parse_file(file_path, use_ocr=use_ocr)
            elif url:
                result = await parser.parse_url(url, use_ocr=use_ocr)
            else:
                return ToolOutput(result=None, error="file_path or url required", metadata={})
            return ToolOutput(result=result, metadata={"parsed": True})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "file_path" in input or "url" in input


class ColpalSearchTool(BaseTool):
    name = "colpal_search"
    description = "Search images using visual embeddings"

    async def execute(self, input: ToolInput) -> ToolOutput:
        try:
            from ui.colpali_integration import get_colpali_search_client
            client = get_colpali_search_client()
            if not client:
                return ToolOutput(result=None, error="ColPali not configured", metadata={})
            result = await client.search(
                query=input.args.get("query", ""),
                limit=input.args.get("limit", 10),
            )
            return ToolOutput(result=result, metadata={"source": "colpali"})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "query" in input


class UISketchSearchTool(BaseTool):
    name = "ui_sketch_search"
    description = "Search UI sketches and mockups"

    async def execute(self, input: ToolInput) -> ToolOutput:
        try:
            from ui.retriever import get_ui_retriever
            retriever = get_ui_retriever()
            if not retriever:
                return ToolOutput(result=None, error="UI retriever not configured", metadata={})
            result = await retriever.search_combined(
                query=input.args.get("query", ""),
                element_types=[],
                limit=input.args.get("limit", 10),
            )
            return ToolOutput(result=result, metadata={"source": "ui_sketch"})
        except Exception as e:
            return ToolOutput(result=None, error=str(e), metadata={})

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "query" in input


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._resources: Dict[str, Any] = {}
        self._prompts: Dict[str, Any] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        self.register(ArchitectureEvaluator())
        self.register(SecurityValidator())
        self.register(CostEstimator())
        self.register(SearchTool())
        self.register(HybridSearchTool())
        self.register(RerankTool())
        self.register(ChainReasoningTool())
        self.register(EntityReasoningTool())
        self.register(IterativeReasoningTool())
        self.register(GraphQueryTool())
        self.register(EntitySearchTool())
        self.register(IngestSourceTool())
        self.register(GetJobStatusTool())
        self.register(KubernetesSearchTool())
        self.register(HelmSearchTool())
        self.register(DockerfileSearchTool())
        self.register(GraphQLSearchTool())
        self.register(IstioSearchTool())
        self.register(FindCallersTool())
        self.register(FindCalleesTool())
        self.register(FindDeadCodeTool())
        self.register(GetComplexityTool())
        self.register(ClassHierarchyTool())
        self.register(GetModuleDepsTool())
        self.register(ExtractFromImageTool())
        self.register(AnalyzeVisualTool())
        self.register(ParseDocumentAdvancedTool())
        self.register(ColpalSearchTool())
        self.register(UISketchSearchTool())
        from ui.suggestion_tool import UISuggestionTool
        self.register(UISuggestionTool())
        self._register_pdlc_tools()

    def _register_pdlc_tools(self):
        try:
            from tools.ideation import register_ideation_tools
            from tools.requirements import register_requirements_tools
            from tools.testing import register_testing_tools
            from tools.deployment import register_deployment_tools
            from tools.observability import register_observability_tools
            from tools.feedback import register_feedback_tools
            from tools.day2 import register_day2_tools

            register_ideation_tools(self)
            register_requirements_tools(self)
            register_testing_tools(self)
            register_deployment_tools(self)
            register_observability_tools(self)
            register_feedback_tools(self)
            register_day2_tools(self)
        except ImportError:
            pass

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, str]]:
        return [
            {"name": t.name, "description": t.description} for t in self._tools.values()
        ]

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> ToolOutput:
        tool = self.get(tool_name)
        if not tool:
            return ToolOutput(
                result=None, error=f"Tool '{tool_name}' not found", metadata={}
            )

        if not tool.validate_input(args):
            return ToolOutput(result=None, error="Invalid input for tool", metadata={})

        return await tool.execute(ToolInput(args=args))

    async def execute_batch(self, calls: List[Dict[str, Any]]) -> List[ToolOutput]:
        results = []
        for call in calls:
            tool_name = call.get("name")
            args = call.get("arguments", {})
            result = await self.execute(tool_name, args)
            results.append(result)
        return results

    def list_resources(self) -> List[Dict[str, Any]]:
        return [
            {"uri": f"resource://{name}", "name": name, "description": desc}
            for name, desc in self._resources.items()
        ]

    def register_resource(self, name: str, description: str, data: Any):
        self._resources[name] = {"description": description, "data": data}

    def get_resource(self, name: str) -> Optional[Any]:
        return self._resources.get(name)

    def list_prompts(self) -> List[Dict[str, Any]]:
        return [
            {"name": name, "description": desc} for name, desc in self._prompts.items()
        ]

    def register_prompt(self, name: str, description: str, template: str):
        self._prompts[name] = {"description": description, "template": template}

    def get_prompt(self, name: str) -> Optional[Dict[str, Any]]:
        return self._prompts.get(name)


_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
