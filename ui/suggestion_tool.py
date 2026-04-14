"""UISuggestionTool - MCP tool for UI sketch understanding."""

from typing import Any, Dict

from tools.base import BaseTool, ToolInput, ToolOutput


class UISuggestionTool(BaseTool):
    """Given a UI sketch (by ID or image), suggest SAP BTP implementation."""

    name = "ui_suggest_implementation"
    description = "Given a UI sketch (by ID or image), suggest SAP BTP implementation"

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "ui_sketch_id" in input or "image_url" in input

    async def execute(self, input: ToolInput) -> ToolOutput:
        sketch_id = input.args.get("ui_sketch_id")
        image_url = input.args.get("image_url")
        detail_level = min(max(int(input.args.get("detail_level", 1)), 1), 3)

        retriever = get_ui_retriever()
        catalog = get_sap_catalog()

        suggestions = []

        # If sketch_id provided, find similar UIs
        if sketch_id:
            similar = await retriever.find_similar_structural(sketch_id, limit=3)
            suggestions.append({"type": "similar_uis", "data": similar})

        # Get SAP component candidates for common element types
        sap_candidates = []
        for elem_type in ["table", "form", "button", "input", "select"]:
            candidates = catalog.find_for_element_type(elem_type)
            for c in candidates:
                sap_candidates.append(
                    {
                        "name": c.name,
                        "library": c.library,
                        "element_type": elem_type,
                        "complexity": c.complexity,
                        "properties": c.properties[:5],
                    }
                )

        suggestions.append(
            {
                "type": "sap_components",
                "data": sap_candidates,
                "detail_level": detail_level,
            }
        )

        return ToolOutput(
            result={
                "sketch_id": sketch_id,
                "image_url": image_url,
                "suggestions": suggestions,
                "detail_level": detail_level,
            },
            metadata={"tool": self.name},
        )


def get_ui_retriever():
    from ui.retriever import get_ui_retriever

    return get_ui_retriever()


def get_sap_catalog():
    from ui.sap_knowledge import get_sap_catalog

    return get_sap_catalog()
