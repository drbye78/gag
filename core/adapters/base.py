from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from models.ir import IRFeature, PlatformContext


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


class AdapterRegistry:
    def __init__(self):
        self._adapters: Dict[str, PlatformAdapter] = {}
        self._default: Optional[PlatformAdapter] = None
    
    def register(self, adapter: PlatformAdapter) -> None:
        self._adapters[adapter.platform_id] = adapter
    
    def get(self, platform_id: str) -> Optional[PlatformAdapter]:
        return self._adapters.get(platform_id)
    
    def get_default(self) -> PlatformAdapter:
        if self._default is None:
            raise RuntimeError("No default adapter configured")
        return self._default
    
    def list_platforms(self) -> List[str]:
        return list(self._adapters.keys())
    
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


_adapter_registry: Optional[AdapterRegistry] = None


def get_adapter_registry() -> AdapterRegistry:
    global _adapter_registry
    if _adapter_registry is None:
        _adapter_registry = AdapterRegistry()
    return _adapter_registry