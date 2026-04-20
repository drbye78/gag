import logging
from typing import Any, Dict, List, Optional
import re

from pydantic import BaseModel

from tools.base import BaseTool, ToolInput, ToolOutput

logger = logging.getLogger(__name__)


class UserStory(BaseModel):
    id: str
    text: str
    format: str = "jira"


class AcceptanceCriterion(BaseModel):
    text: str
    type: str = "functional"
    priority: str = "high"


class ValidationResult(BaseModel):
    valid: bool
    count: int
    issues: List[str] = []


class Gap(BaseModel):
    type: str
    severity: str
    description: str = ""


class UserStoryGeneratorTool(BaseTool):
    name = "user_story_generate"
    description = "Generate user stories from natural language requirements"

    async def execute(self, input: ToolInput) -> ToolOutput:
        text = input.args.get("text", "")
        format_style = input.args.get("format", "jira")

        logger.info(f"Generating user stories from {len(text)} chars")

        try:
            stories = await self._generate_llm(text, format_style)
            method = "llm"
        except Exception as e:
            logger.warning(f"LLM failed, using fallback: {e}")
            stories = await self._generate_fallback(text, format_style)
            method = "fallback"

        return ToolOutput(
            result={"stories": [s.model_dump() if hasattr(s, 'model_dump') else s for s in stories], "count": len(stories)},
            metadata={"generated": True, "method": method}
        )

    async def _generate_llm(self, text: str, format_style: str) -> List[UserStory]:
        from llm.router import get_router
        router = get_router()

        prompt = f"""Extract user stories from the following requirements text.
Format: {format_style}

Requirements:
{text}

For each user story provide:
- id: US-1, US-2, etc.
- text: As a [role], I want [action], so that [benefit]
- format: {format_style}

Respond ONLY with JSON array of user stories."""

        response = await router.chat(prompt=prompt, temperature=0.3, max_tokens=1500)
        import json
        data = json.loads(response.choices[0]["message"]["content"])
        return [UserStory(**story) for story in data[:10]]

    async def _generate_fallback(self, text: str, format_style: str) -> List[UserStory]:
        sentences = re.split(r'[.!?]', text)
        stories = []
        for i, sentence in enumerate(sentences):
            if sentence.strip():
                stories.append(UserStory(
                    id=f"US-{i+1}",
                    text=f"As a user, I want to {sentence.strip()[:100]}, so that I can benefit",
                    format=format_style
                ))
        return stories[:10]

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "text" in input


class AcceptanceCriteriaGeneratorTool(BaseTool):
    name = "acceptance_criteria_generate"
    description = "Generate acceptance criteria from requirements"

    async def execute(self, input: ToolInput) -> ToolOutput:
        requirements = input.args.get("requirements", [])

        logger.info(f"Generating acceptance criteria for {len(requirements)} requirements")

        try:
            criteria = await self._generate_llm(requirements)
            method = "llm"
        except Exception as e:
            logger.warning(f"LLM failed, using fallback: {e}")
            criteria = await self._generate_fallback(requirements)
            method = "fallback"

        return ToolOutput(
            result={"criteria": [c.model_dump() if hasattr(c, 'model_dump') else c for c in criteria]},
            metadata={"generated": True, "method": method}
        )

    async def _generate_llm(self, requirements: List[str]) -> List[AcceptanceCriterion]:
        from llm.router import get_router
        router = get_router()

        prompt = f"""Generate acceptance criteria for these requirements:
{requirements}

For each criterion provide:
- text: Specific testable condition
- type: functional/non-functional/performance
- priority: high/medium/low

Respond ONLY with JSON array."""

        response = await router.chat(prompt=prompt, temperature=0.3, max_tokens=1500)
        import json
        data = json.loads(response.choices[0]["message"]["content"])
        return [AcceptanceCriterion(**c) for c in data]

    async def _generate_fallback(self, requirements: List[str]) -> List[AcceptanceCriterion]:
        return [
            AcceptanceCriterion(text=f"Verify {req}", type="functional", priority="high")
            for req in requirements
        ]

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "requirements" in input


class RequirementsValidatorTool(BaseTool):
    name = "requirements_validate"
    description = "Validate requirements for completeness and consistency"

    async def execute(self, input: ToolInput) -> ToolOutput:
        requirements = input.args.get("requirements", [])

        logger.info(f"Validating {len(requirements)} requirements")

        validation = await self._validate(requirements)

        return ToolOutput(
            result=validation.model_dump(),
            metadata={"validated": True}
        )

    async def _validate(self, requirements: List[str]) -> ValidationResult:
        issues = []

        if not requirements:
            issues.append("No requirements provided")

        required_keywords = ["shall", "must", "should", "will"]
        for i, req in enumerate(requirements):
            if not any(kw in req.lower() for kw in required_keywords):
                issues.append(f"Requirement {i+1} lacks measurable criteria")

        if len(requirements) < 3:
            issues.append("Insufficient requirements for complete feature")

        return ValidationResult(
            valid=len(issues) == 0,
            count=len(requirements),
            issues=issues
        )

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "requirements" in input


class GapAnalyzerTool(BaseTool):
    name = "gap_analyze"
    description = "Identify gaps in requirements"

    async def execute(self, input: ToolInput) -> ToolOutput:
        requirements = input.args.get("requirements", [])

        logger.info(f"Analyzing gaps in {len(requirements)} requirements")

        gaps = await self._analyze_gaps(requirements)

        return ToolOutput(
            result={"gaps": [g.model_dump() if hasattr(g, 'model_dump') else g for g in gaps]},
            metadata={"analyzed": True}
        )

    async def _analyze_gaps(self, requirements: List[str]) -> List[Gap]:
        gaps = []
        req_text = " ".join(requirements).lower()

        if "security" not in req_text:
            gaps.append(Gap(type="security", severity="high", description="No security requirements found"))

        if "performance" not in req_text and "scalability" not in req_text:
            gaps.append(Gap(type="performance", severity="medium", description="No performance requirements"))

        if "error" not in req_text and "exception" not in req_text:
            gaps.append(Gap(type="error_handling", severity="medium", description="No error handling requirements"))

        if "test" not in req_text:
            gaps.append(Gap(type="testing", severity="low", description="No testing requirements"))

        return gaps

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "requirements" in input


class RequirementsImporterTool(BaseTool):
    name = "requirements_import"
    description = "Import requirements from external sources"

    async def execute(self, input: ToolInput) -> ToolOutput:
        source = input.args.get("source", "jira")
        query = input.args.get("query", "")

        logger.info(f"Importing requirements from {source}")

        try:
            requirements = await self._import_from_source(source, query)
            method = "api"
        except NotImplementedError as e:
            logger.warning(f"Import not implemented: {e}")
            requirements = []
            method = "not_implemented"
        except Exception as e:
            logger.error(f"Import failed: {e}")
            requirements = []
            method = "error"

        return ToolOutput(
            result={"requirements": requirements, "source": source},
            metadata={"imported": True, "method": method}
        )

    async def _import_from_source(self, source: str, query: str) -> List[Dict[str, Any]]:
        if source == "jira":
            return await self._import_jira(query)
        elif source == "confluence":
            return await self._import_confluence(query)
        else:
            raise ValueError(f"Unsupported source: {source}")

    async def _import_jira(self, query: str) -> List[Dict[str, Any]]:
        logger.info(f"Importing from Jira with query: {query}")
        raise NotImplementedError("Jira integration requires jira-client library")

    async def _import_confluence(self, query: str) -> List[Dict[str, Any]]:
        logger.info(f"Importing from Confluence with query: {query}")
        raise NotImplementedError("Confluence integration requires confluence-client library")

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "source" in input


def register_requirements_tools(registry) -> None:
    registry.register(UserStoryGeneratorTool())
    registry.register(AcceptanceCriteriaGeneratorTool())
    registry.register(RequirementsValidatorTool())
    registry.register(GapAnalyzerTool())
    registry.register(RequirementsImporterTool())