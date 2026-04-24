from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Use protocols for dependency inversion - core layer defines interfaces
from core.protocols import IRFeatureProtocol, PlatformContextProtocol
from core.knowledge.graph import get_knowledge_graph, NodeType, EdgeType


# For backwards compatibility, create type aliases
# Actual implementations come from models.ir
from models.ir import IRFeature, PlatformContext


def get_adapter_registry() -> "AdapterRegistry":
    from core.adapters import get_adapter_registry as _get_registry
    return _get_registry()


class AdapterInput(BaseModel):
    ir_features: IRFeature
    pattern_matches: List[Any] = []
    constraint_violations: List[Any] = []
    platform_context: PlatformContext


class AdapterOutput(BaseModel):
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    architecture_diagram: Optional[str] = None
    config_templates: Dict[str, str] = Field(default_factory=dict)
    code_snippets: Dict[str, str] = Field(default_factory=dict)
    deployment_manifests: Dict[str, str] = Field(default_factory=dict)
    explanation: str = ""
    confidence: float = 0.0
    can_deploy: bool = True
    platform: Optional[str] = None


class PlatformAdapter(ABC):
    @property
    @abstractmethod
    def platform_id(self) -> str:
        pass
    
    @property
    @abstractmethod
    def supported_services(self) -> List[str]:
        pass
    
    @property
    @abstractmethod
    def patterns(self) -> List[Any]:
        pass
    
    @property
    @abstractmethod
    def constraints(self) -> Any:
        pass
    
    @abstractmethod
    def transform_ir_to_platform(self, input: AdapterInput) -> AdapterOutput:
        pass
    
    @abstractmethod
    def generate_config(self, features: IRFeature) -> Dict[str, str]:
        pass
    
    @abstractmethod
    def generate_code(self, features: IRFeature) -> Dict[str, str]:
        pass
    
    def get_knowledge_node(self) -> Optional[Any]:
        graph = get_knowledge_graph()
        return graph.get_node(self.platform_id)
    
    def get_related_services(self) -> List[str]:
        graph = get_knowledge_graph()
        related = graph.find_related(
            self.platform_id,
            edge_types=[EdgeType.PROVIDES],
            depth=1
        )
        return [n.id for n in related]


class AdapterRegistry:
    def __init__(self):
        self._adapters: Dict[str, PlatformAdapter] = {}
        self._default: Optional[PlatformAdapter] = None
    
    def register(self, adapter: PlatformAdapter) -> None:
        self._adapters[adapter.platform_id] = adapter
        
        graph = get_knowledge_graph()
        from core.knowledge.graph import KnowledgeNode
        graph.add_node(KnowledgeNode(
            id=adapter.platform_id,
            name=adapter.platform_id.upper(),
            type=NodeType.PLATFORM,
            properties={"services": adapter.supported_services},
        ))
        
        for svc in adapter.supported_services:
            from core.knowledge.graph import KnowledgeNode, KnowledgeEdge
            graph.add_node(KnowledgeNode(
                id=svc,
                name=svc,
                type=NodeType.SERVICE,
                properties={"platform": adapter.platform_id},
            ))
            graph.add_edge(KnowledgeEdge(
                source_id=adapter.platform_id,
                target_id=svc,
                type=EdgeType.PROVIDES,
            ))
    
    def get(self, platform_id: str) -> Optional[PlatformAdapter]:
        return self._adapters.get(platform_id)
    
    def get_default(self) -> PlatformAdapter:
        if self._default is None:
            raise RuntimeError("No default adapter configured")
        return self._default
    
    def list_platforms(self) -> List[str]:
        return list(self._adapters.keys())
    
    def list_adapters(self) -> List[Dict[str, Any]]:
        return [
            {
                "platform_id": pid,
                "adapter": adapter,
                "supported_services": adapter.supported_services,
                "is_default": adapter is self._default,
            }
            for pid, adapter in self._adapters.items()
        ]
    
    def auto_detect(self, features: IRFeature) -> PlatformAdapter:
        feature_dict = features.model_dump()
        feature_str = str(feature_dict).lower()
        
        detect_rules = {
            "sap": ["xsuaa", "hana", "btp", "cap", "cloudfoundry", "kyma", "cf"],
            "salesforce": ["sf", "salesforce", "lightning", "apex", "visualforce"],
            "powerplatform": ["powerapps", "powerautomate", "powerpages", "dataverse", "dax"],
            "tanzu": ["tanzu", "pivotal", "spring", "cf", "kubernetes"],
            "aws": ["lambda", "s3", "dynamodb", "iam", "ec2", "ecs"],
            "azure": ["azure", "function", "app service", "cosmos", "aks"],
        }
        
        for platform_id, keywords in detect_rules.items():
            if any(kw in feature_str for kw in keywords):
                adapter = self._adapters.get(platform_id)
                if adapter:
                    return adapter
        
        return self.get_default()
