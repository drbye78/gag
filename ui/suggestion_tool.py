"""UISuggestionTool - MCP tool for UI sketch understanding."""

from typing import Any, Dict

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
        suggestions = []
        all_domains = registry.all_domains()

        for elem_type in ["table", "form", "button", "input", "select"]:
            for domain_id, comp in registry.find_components(elem_type):
                suggestions.append({
                    "domain": domain_id,
                    "component": comp.name,
                    "library": comp.library,
                    "element_type": elem_type,
                    "complexity": comp.complexity,
                    "properties": comp.properties[:5],
                    "events": comp.events[:3],
                })

        return ToolOutput(
            result={
                "sketch_id": sketch_id,
                "suggestions": suggestions[:20],
                "detail_level": detail_level,
            },
            metadata={"domains": all_domains},
        )