from typing import Any, Dict, List, Optional
from core.knowledge.graph import get_knowledge_graph, NodeType, EdgeType
from core.knowledge.usecases import get_use_case_repository
from core.knowledge.adrs import get_adr_repository
from core.knowledge.reference import get_reference_architecture_repository
from core.adapters import get_adapter_registry


class KnowledgeRetriever:
    def __init__(self):
        self.graph = get_knowledge_graph()
        self.uc_repo = get_use_case_repository()
        self.adr_repo = get_adr_repository()
        self.ref_repo = get_reference_architecture_repository()
        self.adapter_registry = get_adapter_registry()
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        query_lower = query.lower()
        results = []
        
        platforms = self._detect_platforms(query_lower)
        if platforms:
            for platform in platforms:
                platform_results = await self._retrieve_platform(platform, query_lower, limit)
                results.extend(platform_results)
        
        use_case_results = self._retrieve_use_cases(query_lower, limit)
        results.extend(use_case_results)
        
        adr_results = self._retrieve_adrs(query_lower, limit)
        results.extend(adr_results)
        
        ref_results = self._retrieve_references(query_lower, limit)
        results.extend(ref_results)
        
        results = results[:limit]
        
        return {
            "source": "knowledge",
            "results": results,
            "total": len(results),
            "platforms_detected": platforms,
            "took_ms": 1,
        }
    
    def _detect_platforms(self, query: str) -> List[str]:
        platform_keywords = {
            "aws": ["aws", "lambda", "s3", "dynamodb", "ec2", "ecs", "eks", "iam"],
            "azure": ["azure", "function", "cosmos", "aks", "app service"],
            "gcp": ["gcp", "cloud", "gke", "firestore", "cloudfunctions"],
            "sap": ["sap", "btp", "hana", "xsuaa", "kyma", "cap"],
            "tanzu": ["tanzu", "vmware", "kubernetes", "spring", "pivotal"],
            "powerplatform": ["powerapps", "powerautomate", "dataverse", "power platform"],
        }
        
        detected = []
        for platform_id, keywords in platform_keywords.items():
            if any(kw in query for kw in keywords):
                detected.append(platform_id)
        
        return detected
    
    async def _retrieve_platform(
        self,
        platform: str,
        query: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        results = []
        
        platform_nodes = self.graph.find_by_type(NodeType.PLATFORM)
        for node in platform_nodes:
            if node.id == platform:
                results.append({
                    "type": "platform",
                    "id": node.id,
                    "name": node.name,
                    "properties": node.properties,
                })
        
        service_nodes = self.graph.find_by_type(NodeType.SERVICE)
        for node in service_nodes:
            if node.properties.get("platform") == platform:
                results.append({
                    "type": "service",
                    "id": node.id,
                    "name": node.name,
                    "properties": node.properties,
                })
        
        adapter = self.adapter_registry.get(platform)
        if adapter:
            results.append({
                "type": "adapter",
                "id": platform,
                "services": adapter.supported_services,
                "patterns": adapter.patterns,
            })
        
        return results[:limit]
    
    def _retrieve_use_cases(self, query: str, limit: int) -> List[Dict[str, Any]]:
        results = []
        
        all_uc = self.uc_repo.list_all()
        for uc in all_uc:
            if any(
                kw in query
                for kw in ["use case", "scenario", "integration", "automation"]
            ):
                results.append({
                    "type": "use_case",
                    "id": uc.id,
                    "name": uc.name,
                    "description": uc.description,
                    "platforms": uc.platforms,
                    "category": uc.category.value,
                })
        
        return results[:limit]
    
    def _retrieve_adrs(self, query: str, limit: int) -> List[Dict[str, Any]]:
        results = []
        
        all_adr = self.adr_repo.list_all()
        for adr in all_adr:
            if "decision" in query or "adr" in query:
                results.append({
                    "type": "adr",
                    "id": adr.id,
                    "title": adr.title,
                    "decision": adr.decision,
                    "status": adr.status.value,
                    "platforms": adr.related_platforms,
                })
        
        return results[:limit]
    
    def _retrieve_references(self, query: str, limit: int) -> List[Dict[str, Any]]:
        results = []
        
        all_ref = self.ref_repo.list_all()
        for ref in all_ref:
            if any(
                kw in query
                for kw in ["reference", "architecture", "pattern", "serverless", "microservices"]
            ):
                results.append({
                    "type": "reference_architecture",
                    "id": ref.id,
                    "name": ref.name,
                    "type": ref.type.value,
                    "platforms": ref.platforms,
                    "quality_attributes": ref.quality_attributes,
                })
        
        return results[:limit]


_retriever_instance: Optional[KnowledgeRetriever] = None


def get_knowledge_retriever() -> KnowledgeRetriever:
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = KnowledgeRetriever()
    return _retriever_instance