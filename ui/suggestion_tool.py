"""UISuggestionTool - MCP tool for UI sketch understanding."""

from typing import Any, Dict, List, Optional

from tools.base import BaseTool, ToolInput, ToolOutput
from ui.knowledge import get_ui_knowledge_registry


class UISuggestionTool(BaseTool):
    name = "ui_suggest_implementation"
    description = "Given a UI sketch (by ID or image), suggest implementation for any domain"

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "ui_sketch_id" in input or "image_url" in input

async def execute(self, input: ToolInput) -> ToolOutput:
        sketch_id = input.args.get("ui_sketch_id")
        image_url = input.args.get("image_url")
        detail_level = min(max(int(input.args.get("detail_level", 1)), 1), 3)

        registry = get_ui_knowledge_registry()
        all_domains = registry.all_domains()
        suggestions = []
        matched_element_types: List[str] = []

        if sketch_id:
            from ui.ingestion_job import get_ui_job_registry
            job_registry = get_ui_job_registry()
            job = await job_registry.get(sketch_id)
            if job:
                elements = job.metadata.get("elements", [])
                element_types = list(set(
                    e.get("element_type", "unknown")
                    for e in elements
                    if isinstance(e, dict)
                ))
                matched_element_types = element_types

        if image_url and not matched_element_types:
            try:
                from ui.vlm_extractor import VLMUIExtractor
                extractor = VLMUIExtractor()
                result = await extractor.extract(image_url=image_url)
                if result:
                    element_types = list(set(
                        str(getattr(e, "element_type", "unknown"))
                        for e in result.elements
                    ))
                    matched_element_types = element_types
            except Exception:
                pass

        if not matched_element_types:
            matched_element_types = ["table", "form", "button", "input", "select"]

        for elem_type in matched_element_types:
            for domain_id, comp in registry.find_components(elem_type):
                suggestions.append({
                    "domain": domain_id,
                    "component": comp.name,
                    "library": comp.library,
                    "element_type": elem_type,
                    "complexity": comp.complexity,
                    "properties": comp.properties[:detail_level * 3],
                    "events": comp.events[:3],
                })

        if not suggestions:
            for elem_type in ["table", "form", "button", "input", "select"]:
                for domain_id, comp in registry.find_components(elem_type):
                    suggestions.append({
                        "domain": domain_id,
                        "component": comp.name,
                        "library": comp.library,
                        "element_type": elem_type,
                        "complexity": comp.complexity,
                    })

        return ToolOutput(
            result={
                "sketch_id": sketch_id,
                "image_url": image_url,
                "suggestions": suggestions[:20],
                "detail_level": detail_level,
                "matched_element_types": matched_element_types,
            },
            metadata={"domains": all_domains},
        )