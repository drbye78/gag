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
    
    def __init__(self):
        super().__init__()
        from core.config import get_settings
        self._settings = get_settings()
    
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
        JIRA_AVAILABLE = False
        try:
            from jira import JIRA
            JIRA_AVAILABLE = True
        except ImportError:
            pass
        
        if not JIRA_AVAILABLE:
            return await self._import_jira_fallback(query)
        
        jira_url = self._settings.get("JIRA_URL")
        jira_email = self._settings.get("JIRA_EMAIL")
        jira_token = self._settings.get("JIRA_API_TOKEN")
        
        if not all([jira_url, jira_email, jira_token]):
            return await self._import_jira_fallback(query)
        
        try:
            jira = JIRA(jira_url, basic_auth=(jira_email, jira_token))
            issues = jira.search_issues(query, maxResults=50)
            results = []
            for issue in issues:
                results.append({
                    "id": issue.key,
                    "summary": issue.fields.summary,
                    "description": getattr(issue.fields, "description", ""),
                    "type": issue.fields.issuetype.name if hasattr(issue.fields, "issuetype") else "Story",
                    "status": getattr(issue.fields, "status", {}).name if hasattr(issue.fields, "status") else None,
                    "url": f"{jira_url}/browse/{issue.key}",
                })
            return results
        except Exception as e:
            logger.warning(f"Jira import failed: {e}")
            return await self._import_jira_fallback(query)
    
    async def _import_jira_fallback(self, query: str) -> List[Dict[str, Any]]:
        import httpx
        import os
        
        jira_url = os.getenv("JIRA_URL")
        jira_email = os.getenv("JIRA_EMAIL")
        jira_token = os.getenv("JIRA_API_TOKEN")
        
        if not all([jira_url, jira_email, jira_token]):
            return [{
                "query": query,
                "status": "unconfigured",
                "note": "Set JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN environment variables",
                "results": [],
            }]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {jira_token}",
                    "Accept": "application/json",
                }
                jql_query = query.replace(" ", "+")
                url = f"{jira_url}/rest/api/2/search?jql={jql_query}&maxResults=50"
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                results = []
                for issue in data.get("issues", []):
                    field = issue.get("fields", {})
                    results.append({
                        "id": issue.get("key"),
                        "summary": field.get("summary"),
                        "description": field.get("description", ""),
                        "type": field.get("issuetype", {}).get("name", "Story") if isinstance(field.get("issuetype"), dict) else "Story",
                        "status": field.get("status", {}).get("name") if isinstance(field.get("status"), dict) else None,
                        "url": f"{jira_url}/browse/{issue.get('key')}",
                    })
                return results
        except Exception as e:
            return [{
                "query": query,
                "status": "error",
                "error": str(e),
                "results": [],
            }]
    
    async def _import_confluence(self, query: str) -> List[Dict[str, Any]]:
        logger.info(f"Importing from Confluence with query: {query}")
        CONFLUENCE_AVAILABLE = False
        try:
            from atlassian import Confluence
            CONFLUENCE_AVAILABLE = True
        except ImportError:
            pass
        
        if not CONFLUENCE_AVAILABLE:
            return await self._import_confluence_fallback(query)
        
        confluence_url = self._settings.get("CONFLUENCE_URL")
        confluence_email = self._settings.get("CONFLUENCE_EMAIL")
        confluence_token = self._settings.get("CONFLUENCE_API_TOKEN")
        
        if not all([confluence_url, confluence_email, confluence_token]):
            return await self._import_confluence_fallback(query)
        
        try:
            confluence = Confluence(
                url=confluence_url,
                username=confluence_email,
                password=confluence_token,
            )
            pages = confluence.cql(query, expand="body.storage", limit=50)
            results = []
            for page in pages.get("results", []):
                results.append({
                    "id": page.get("id"),
                    "title": page.get("title"),
                    "url": f"{confluence_url}/pages/{page.get('id')}",
                    "space": page.get("space", {}).get("key") if isinstance(page.get("space"), dict) else None,
                })
            return results
        except Exception as e:
            logger.warning(f"Confluence import failed: {e}")
            return await self._import_confluence_fallback(query)
    
    async def _import_confluence_fallback(self, query: str) -> List[Dict[str, Any]]:
        import httpx
        import os
        
        confluence_url = os.getenv("CONFLUENCE_URL")
        confluence_email = os.getenv("CONFLUENCE_EMAIL")
        confluence_token = os.getenv("CONFLUENCE_API_TOKEN")
        
        if not all([confluence_url, confluence_email, confluence_token]):
            return [{
                "query": query,
                "status": "unconfigured",
                "note": "Set CONFLUENCE_URL, CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN",
                "results": [],
            }]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {confluence_token}",
                    "Content-Type": "application/json",
                }
                cql_query = query.replace(" ", "+")
                url = f"{confluence_url}/rest/api/content/search?cql={cql_query}&limit=50&expand=body.storage"
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                results = []
                for page in data.get("results", []):
                    body = page.get("body", {}).get("storage", {}).get("value", "")[:500]
                    results.append({
                        "id": page.get("id"),
                        "title": page.get("title"),
                        "url": f"{confluence_url}/pages/{page.get('id')}",
                        "body_preview": body,
                    })
                return results
        except Exception as e:
            return [{
                "query": query,
                "status": "error",
                "error": str(e),
                "results": [],
            }]

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "source" in input


def register_requirements_tools(registry) -> None:
    registry.register(UserStoryGeneratorTool())
    registry.register(AcceptanceCriteriaGeneratorTool())
    registry.register(RequirementsValidatorTool())
    registry.register(GapAnalyzerTool())
    registry.register(RequirementsImporterTool())