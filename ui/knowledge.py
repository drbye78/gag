from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class ComponentType(str, Enum):
    CONTROL = "control"
    SERVICE = "service"
    LIBRARY = "library"


@dataclass
class UIComponent:
    component_id: str
    name: str
    library: str
    component_type: ComponentType = ComponentType.CONTROL
    supported_element_types: List[str] = field(default_factory=list)
    properties: List[str] = field(default_factory=list)
    events: List[str] = field(default_factory=list)
    documentation_url: Optional[str] = None
    complexity: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UIService:
    service_id: str
    name: str
    service_type: str
    capabilities: List[str] = field(default_factory=list)
    documentation_url: Optional[str] = None


@dataclass
class UIComponentKnowledge:
    domain_id: str
    display_name: str
    supported_element_types: List[str] = field(default_factory=list)
    components: Dict[str, UIComponent] = field(default_factory=dict)
    services: Dict[str, UIService] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)

    def map_element_to_components(self, element_type: str) -> List[UIComponent]:
        return [
            c for c in self.components.values()
            if element_type in c.supported_element_types
        ]

    def get_component(self, name: str) -> Optional[UIComponent]:
        return self.components.get(name)

    def get_service(self, name: str) -> Optional[UIService]:
        return self.services.get(name)

    def find_services_by_type(self, service_type: str) -> List[UIService]:
        return [s for s in self.services.values() if s.service_type == service_type]

    def is_stale(self, max_age_days: int = 30) -> bool:
        return (datetime.now() - self.last_updated).days > max_age_days


class UIKnowledgeRegistry:
    _knowledge: Dict[str, UIComponentKnowledge] = {}
    _initialized: bool = False

    def register(self, knowledge: UIComponentKnowledge) -> None:
        self._knowledge[knowledge.domain_id] = knowledge

    def get(self, domain_id: str) -> Optional[UIComponentKnowledge]:
        return self._knowledge.get(domain_id)

    def find_components(self, element_type: str) -> List[tuple[str, UIComponent]]:
        results = []
        for domain_id, knowledge in self._knowledge.items():
            for comp in knowledge.map_element_to_components(element_type):
                results.append((domain_id, comp))
        return results

    def all_domains(self) -> List[str]:
        return list(self._knowledge.keys())

    def all_knowledge(self) -> Dict[str, UIComponentKnowledge]:
        return self._knowledge.copy()


_registry = UIKnowledgeRegistry()


def get_ui_knowledge_registry() -> UIKnowledgeRegistry:
    return _registry