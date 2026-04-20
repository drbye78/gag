import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from tools.base import BaseTool, ToolInput, ToolOutput

logger = logging.getLogger(__name__)


class GeneratedIdea(BaseModel):
    name: str
    description: str
    platforms: List[str] = []
    technologies: List[str] = []
    risk_level: str = "medium"
    effort_estimate: str = "M"


class TechnologyRecommendation(BaseModel):
    category: str
    options: List[Dict[str, Any]]
    selected: str


class PatternMatch(BaseModel):
    id: str
    name: str
    type: str
    description: str
    platforms: List[str]
    components: List[str]
    quality_attributes: Dict[str, str]


class IdeaGeneratorTool(BaseTool):
    name = "idea_generate"
    description = "Generate project ideas based on domain, constraints, and existing knowledge"

    async def execute(self, input: ToolInput) -> ToolOutput:
        domain = input.args.get("domain", "")
        constraints = input.args.get("constraints", [])
        existing_ideas = input.args.get("existing_ideas", [])

        logger.info(f"Generating ideas for domain={domain}, constraints={constraints}")

        try:
            ideas = await self._generate_ideas_llm(domain, constraints, existing_ideas)
            logger.info(f"Generated {len(ideas)} ideas for domain={domain}")
            return ToolOutput(
                result={
                    "domain": domain,
                    "generated_ideas": [idea.model_dump() for idea in ideas],
                    "count": len(ideas),
                },
                metadata={"generated": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM generation failed, falling back to KB: {e}")
            ideas = await self._generate_ideas_fallback(domain, constraints, existing_ideas)
            return ToolOutput(
                result={
                    "domain": domain,
                    "generated_ideas": ideas,
                    "count": len(ideas),
                },
                metadata={"generated": True, "method": "fallback", "error": str(e)}
            )

    async def _generate_ideas_llm(
        self,
        domain: str,
        constraints: List[str],
        existing: List[str]
    ) -> List[GeneratedIdea]:
        try:
            from llm.router import get_router
            router = get_router()

            prompt = f"""Generate 5 innovative project ideas for a {domain} system.
Constraints: {', '.join(constraints) if constraints else 'none'}
Existing ideas to avoid: {', '.join(existing) if existing else 'none'}

For each idea provide a JSON object with:
- name: Creative name (max 50 chars)
- description: 2-3 sentence description
- platforms: 2-3 suitable platforms from [AWS, Azure, GCP, SAP BTP, Tanzu, Power Platform]
- technologies: Key technologies (e.g., Kubernetes, Lambda, DynamoDB)
- risk_level: low/medium/high
- effort_estimate: XS/S/M/L/XL

Respond ONLY with a JSON array of 5 ideas, no other text."""

            response = await router.chat(
                prompt=prompt,
                temperature=0.8,
                max_tokens=2000
            )

            content = response.choices[0]["message"]["content"]
            import json
            ideas_data = json.loads(content)
            
            return [GeneratedIdea(**idea) for idea in ideas_data[:5]]

        except Exception as e:
            logger.error(f"LLM idea generation failed: {e}")
            raise

    async def _generate_ideas_fallback(
        self,
        domain: str,
        constraints: List[str],
        existing: List[str]
    ) -> List[Dict[str, Any]]:
        try:
            from core.knowledge.usecases import get_use_case_repository
            from core.knowledge.reference import get_reference_architecture_repository

            uc_repo = get_use_case_repository()
            ref_repo = get_reference_architecture_repository()

            relevant_uc = [
                uc for uc in uc_repo.list_all()
                if domain.lower() in uc.name.lower() or domain.lower() in uc.description.lower()
            ]

            relevant_refs = [
                ref for ref in ref_repo.list_all()
                if not constraints or any(p in ref.platforms for p in constraints)
            ]

            ideas = []
            for ref in relevant_refs[:3]:
                ideas.append({
                    "name": f"{ref.name} for {domain}",
                    "description": ref.description,
                    "platforms": ref.platforms,
                    "technologies": ref.components,
                    "risk_level": "medium",
                    "effort_estimate": "M",
                })

            for uc in relevant_uc[:2]:
                ideas.append({
                    "name": uc.name,
                    "description": uc.description,
                    "platforms": uc.platforms,
                    "technologies": uc.technologies,
                    "risk_level": uc.risk_level or "medium",
                    "effort_estimate": uc.effort_estimate or "M",
                })

            return ideas[:5]

        except ImportError:
            return [{"name": f"Project for {domain}", "description": f"A {domain} project"}]

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "domain" in input


class BrainstormTool(BaseTool):
    name = "brainstorm"
    description = "Expand and refine ideas through collaborative brainstorming"

    async def execute(self, input: ToolInput) -> ToolOutput:
        seeds = input.args.get("seed_ideas", [])
        focus_areas = input.args.get("focus_areas", [])
        expand_count = input.args.get("expand_count", 5)

        logger.info(f"Brainstorming {len(seeds)} seed ideas")

        try:
            expanded = await self._expand_ideas_llm(seeds, focus_areas, expand_count)
            method = "llm"
        except Exception as e:
            logger.warning(f"LLM brainstorming failed, using fallback: {e}")
            expanded = await self._expand_ideas_fallback(seeds, focus_areas, expand_count)
            method = "fallback"

        return ToolOutput(
            result={
                "original_ideas": seeds,
                "expanded_ideas": expanded,
                "count": len(expanded),
            },
            metadata={"brainstormed": True, "method": method}
        )

    async def _expand_ideas_llm(
        self,
        seeds: List[str],
        focus_areas: List[str],
        count: int
    ) -> List[Dict[str, Any]]:
        from llm.router import get_router
        router = get_router()

        prompt = f"""Expand the following ideas with creative variations.
Seed ideas: {', '.join(seeds)}
Focus areas: {', '.join(focus_areas) if focus_areas else 'general innovation'}
Number of variations: {count}

For each variation provide:
- name: Creative name combining seed + strategy
- strategy: The expansion strategy applied
- description: How this builds on the original
- priority: high/medium/low

Respond ONLY with JSON array."""

        response = await router.chat(prompt=prompt, temperature=0.9, max_tokens=1500)
        import json
        content = response.choices[0]["message"]["content"]
        return json.loads(content)[:count]

    async def _expand_ideas_fallback(
        self,
        seeds: List[str],
        focus_areas: List[str],
        count: int
    ) -> List[Dict[str, Any]]:
        strategies = ["automation", "optimization", "scaling", "security", "monitoring"]
        expanded = []

        for seed in seeds:
            for strategy in strategies[:count // len(seeds) if seeds else count]:
                expanded.append({
                    "name": f"{seed} + {strategy}",
                    "strategy": strategy,
                    "description": f"Apply {strategy} to {seed}",
                    "priority": "high" if strategy in ["security", "scaling"] else "medium",
                })

        return expanded[:count]

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "seed_ideas" in input


class TechnologyRecommenderTool(BaseTool):
    name = "technology_recommend"
    description = "Recommend technology stack based on requirements, constraints, and domain"

    async def execute(self, input: ToolInput) -> ToolOutput:
        requirements = input.args.get("requirements", {})
        constraints = input.args.get("constraints", {})
        domain = input.args.get("domain", "")

        logger.info(f"Recommending technology for domain={domain}")

        try:
            recommendations = await self._recommend_llm(requirements, constraints, domain)
            method = "llm"
        except Exception as e:
            logger.warning(f"LLM recommendation failed, using fallback: {e}")
            recommendations = await self._recommend_fallback(requirements, constraints, domain)
            method = "fallback"

        return ToolOutput(
            result={"domain": domain, "recommendations": recommendations},
            metadata={"recommended": True, "method": method}
        )

    async def _recommend_llm(
        self,
        requirements: Dict[str, Any],
        constraints: Dict[str, Any],
        domain: str
    ) -> List[Dict[str, Any]]:
        from llm.router import get_router
        router = get_router()

        prompt = f"""Recommend technology stack for a {domain} system.
Requirements: {requirements}
Constraints: {constraints}

For each category provide:
- category: compute/database/cache/messaging/etc
- options: array of {{name, score}}
- selected: The best choice with reasoning

Respond ONLY with JSON array."""

        response = await router.chat(prompt=prompt, temperature=0.3, max_tokens=1500)
        import json
        return json.loads(response.choices[0]["message"]["content"])

    async def _recommend_fallback(
        self,
        requirements: Dict[str, Any],
        constraints: Dict[str, Any],
        domain: str
    ) -> List[Dict[str, Any]]:
        scale = requirements.get("scale", "medium")
        analytics = requirements.get("analytics", False)

        recommendations = []

        if scale in ["large", "massive"]:
            recommendations.append({
                "category": "compute",
                "options": [
                    {"name": "AWS Lambda", "score": 0.9},
                    {"name": "Azure Functions", "score": 0.85},
                ],
                "selected": "AWS Lambda",
            })
        else:
            recommendations.append({
                "category": "compute",
                "options": [
                    {"name": "Kubernetes/EKS", "score": 0.9},
                    {"name": "Azure AKS", "score": 0.85},
                ],
                "selected": "Kubernetes/EKS",
            })

        if analytics:
            recommendations.append({
                "category": "analytics",
                "options": [{"name": "BigQuery", "score": 0.9}],
                "selected": "BigQuery",
            })

        return recommendations

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "requirements" in input or "domain" in input


class PatternFinderTool(BaseTool):
    name = "pattern_find"
    description = "Find architectural patterns from knowledge base for given context"

    async def execute(self, input: ToolInput) -> ToolOutput:
        context = input.args.get("context", "")
        platform = input.args.get("platform", "")

        logger.info(f"Finding patterns for context={context}, platform={platform}")

        patterns = await self._find_patterns(context, platform)

        return ToolOutput(
            result={
                "context": context,
                "platform": platform,
                "patterns": [p.model_dump() if hasattr(p, 'model_dump') else p for p in patterns],
            },
            metadata={"found": True}
        )

    async def _find_patterns(self, context: str, platform: str) -> List[PatternMatch]:
        try:
            from core.knowledge.reference import get_reference_architecture_repository

            ref_repo = get_reference_architecture_repository()
            all_patterns = ref_repo.list_all()

            if platform:
                all_patterns = [p for p in all_patterns if platform in p.platforms]

            if context:
                all_patterns = [
                    p for p in all_patterns
                    if context.lower() in p.name.lower()
                    or context.lower() in p.description.lower()
                ]

            return [
                PatternMatch(
                    id=p.id,
                    name=p.name,
                    type=p.type.value,
                    description=p.description,
                    platforms=p.platforms,
                    components=p.components,
                    quality_attributes=p.quality_attributes,
                )
                for p in all_patterns[:5]
            ]

        except ImportError:
            return []

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "context" in input


def register_ideation_tools(registry) -> None:
    registry.register(IdeaGeneratorTool())
    registry.register(BrainstormTool())
    registry.register(TechnologyRecommenderTool())
    registry.register(PatternFinderTool())