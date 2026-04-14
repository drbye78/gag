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

        # Find similar UIs if sketch_id provided
        if sketch_id:
            similar = await retriever.find_similar_structural(sketch_id, limit=3)
            suggestions.append({"type": "similar_uis", "data": similar})

        # Get SAP component candidates
        sap_candidates = []
        for elem_type in ["table", "form", "button", "input", "select"]:
            candidates = catalog.find_for_element_type(elem_type)
            for c in candidates:
                sap_candidates.append({
                    "name": c.name, "library": c.library,
                    "element_type": elem_type, "complexity": c.complexity,
                    "properties": c.properties[:5],
                    "events": c.events[:3],
                })

        suggestions.append({
            "type": "sap_components",
            "data": sap_candidates,
            "detail_level": detail_level,
        })

        result = {
            "sketch_id": sketch_id,
            "image_url": image_url,
            "suggestions": suggestions,
            "detail_level": detail_level,
        }

        if detail_level >= 2:
            # Level 2: Add code snippets for top candidates
            code_snippets = []
            for comp in sap_candidates[:3]:
                code_snippets.append(self._generate_component_snippet(comp))
            result["code_snippets"] = code_snippets

        if detail_level >= 3:
            # Level 3: Add CAP service and structure
            services = catalog.get_all_services()
            result["btp_services"] = [
                {"name": s.name, "type": s.service_type, "capabilities": s.capabilities}
                for s in services
            ]
            result["project_structure"] = self._suggest_project_structure(sap_candidates)

        return ToolOutput(result=result, metadata={"tool": self.name})

    def _generate_component_snippet(self, comp: dict) -> dict:
        """Generate a basic SAPUI5 code snippet for a component."""
        name = comp["name"]
        if "Table" in name:
            return {
                "component": name,
                "xml": f'<{name.split(".")[-1]} items="{{/items}}">\n'
                       f'  <columns>\n    <!-- Add columns -->\n  </columns>\n'
                       f'  <items>\n    <!-- Add item template -->\n  </items>\n'
                       f'</{name.split(".")[-1]}>',
                "binding": "{/items}",
            }
        elif "Form" in name:
            return {
                "component": name,
                "xml": f'<{name.split(".")[-1]} editable="true">\n'
                       f'  <content>\n    <!-- Add form fields -->\n  </content>\n'
                       f'</{name.split(".")[-1]}>',
            }
        elif "Button" in name:
            return {
                "component": name,
                "xml": f'<{name.split(".")[-1]} text="Submit" press="onPress"/>',
            }
        elif "Input" in name:
            return {
                "component": name,
                "xml": f'<{name.split(".")[-1]} value="{{/field}}" liveChange="onLiveChange"/>',
            }
        else:
            return {"component": name, "note": "See SAPUI5 API reference"}

    def _suggest_project_structure(self, candidates: list) -> dict:
        """Suggest CAP project structure based on candidates."""
        return {
            "app": {"type": "CAP Node.js or Java", "ui_module": "SAPUI5/Fiori"},
            "services": [{"type": "OData V4", "entity": "main_entity"}],
            "btp_services": ["XSUAA", "Destination", "HTML5 Application Repository"],
            "components": [c["name"] for c in candidates[:5]],
        }


def get_ui_retriever():
    from ui.retriever import get_ui_retriever

    return get_ui_retriever()


def get_sap_catalog():
    from ui.sap_knowledge import get_sap_catalog

    return get_sap_catalog()
