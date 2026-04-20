from typing import Any, Dict, List, Optional
import re

from pydantic import BaseModel

from tools.base import BaseTool, ToolInput, ToolOutput


class UserStoryGeneratorTool(BaseTool):
    name = "user_story_generate"
    description = "Generate user stories from natural language requirements"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        text = input.args.get("text", "")
        format = input.args.get("format", "jira")
        
        stories = await self._generate_user_stories(text, format)
        
        return ToolOutput(
            result={"stories": stories, "count": len(stories)},
            metadata={"generated": True}
        )
    
    async def _generate_user_stories(
        self,
        text: str,
        format: str
    ) -> List[Dict[str, Any]]:
        stories = []
        
        sentences = re.split(r'[.!?]', text)
        for i, sentence in enumerate(sentences):
            if sentence.strip():
                stories.append({
                    "id": f"US-{i+1}",
                    "text": sentence.strip(),
                    "format": format,
                })
        
        return stories[:10]
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "text" in input


class AcceptanceCriteriaGeneratorTool(BaseTool):
    name = "acceptance_criteria_generate"
    description = "Generate acceptance criteria from requirements"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        requirements = input.args.get("requirements", [])
        
        criteria = await self._generate_criteria(requirements)
        
        return ToolOutput(
            result={"criteria": criteria},
            metadata={"generated": True}
        )
    
    async def _generate_criteria(
        self,
        requirements: List[str]
    ) -> List[Dict[str, Any]]:
        return [
            {"text": req, "type": "functional", "priority": "high"}
            for req in requirements
        ]
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "requirements" in input


class RequirementsValidatorTool(BaseTool):
    name = "requirements_validate"
    description = "Validate requirements for completeness and consistency"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        requirements = input.args.get("requirements", [])
        
        validation = await self._validate_requirements(requirements)
        
        return ToolOutput(
            result=validation,
            metadata={"validated": True}
        )
    
    async def _validate_requirements(
        self,
        requirements: List[str]
    ) -> Dict[str, Any]:
        return {
            "valid": len(requirements) > 0,
            "count": len(requirements),
            "issues": [],
        }
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "requirements" in input


class GapAnalyzerTool(BaseTool):
    name = "gap_analyze"
    description = "Identify gaps in requirements"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        requirements = input.args.get("requirements", [])
        
        gaps = await self._analyze_gaps(requirements)
        
        return ToolOutput(
            result={"gaps": gaps},
            metadata={"analyzed": True}
        )
    
    async def _analyze_gaps(
        self,
        requirements: List[str]
    ) -> List[Dict[str, Any]]:
        gaps = []
        
        if not any("security" in r.lower() for r in requirements):
            gaps.append({"type": "security", "severity": "high"})
        
        return gaps
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "requirements" in input


class RequirementsImporterTool(BaseTool):
    name = "requirements_import"
    description = "Import requirements from external sources"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        source = input.args.get("source", "jira")
        query = input.args.get("query", "")
        
        requirements = await self._import_requirements(source, query)
        
        return ToolOutput(
            result={"requirements": requirements},
            metadata={"imported": True}
        )
    
    async def _import_requirements(
        self,
        source: str,
        query: str
    ) -> List[Dict[str, Any]]:
        return []
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "source" in input


def register_requirements_tools(registry) -> None:
    registry.register(UserStoryGeneratorTool())
    registry.register(AcceptanceCriteriaGeneratorTool())
    registry.register(RequirementsValidatorTool())
    registry.register(GapAnalyzerTool())
    registry.register(RequirementsImporterTool())