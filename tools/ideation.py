"""
IDEATION Phase Tools for MCP Interface

Tools for PDLC Phase 1: IDEATION
- IdeaGenerator: Generate project ideas based on domain and constraints
- BrainstormTool: Collaborative brainstorming session
- TechnologyRecommender: Recommend technology stack based on requirements
- PatternFinder: Find architectural patterns for ideation
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from tools.base import BaseTool, ToolInput, ToolOutput


class IdeationToolInput(BaseModel):
    """Input schema for ideation tools."""
    domain: str
    constraints: List[str] = []
    existing_ideas: List[str] = []


class IdeaGeneratorTool(BaseTool):
    """Generate project ideas based on domain and constraints."""
    
    name = "idea_generate"
    description = "Generate project ideas based on domain, constraints, and existing knowledge"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        domain = input.args.get("domain", "")
        constraints = input.args.get("constraints", [])
        existing_ideas = input.args.get("existing_ideas", [])
        
        # Use knowledge base to generate ideas
        ideas = await self._generate_ideas(domain, constraints, existing_ideas)
        
        return ToolOutput(
            result={
                "domain": domain,
                "generated_ideas": ideas,
                "count": len(ideas),
            },
            metadata={"generated": True}
        )
    
    async def _generate_ideas(
        self, 
        domain: str, 
        constraints: List[str], 
        existing: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate ideas using knowledge base patterns."""
        # Import knowledge base for pattern matching
        try:
            from core.knowledge.usecases import get_use_case_repository
            from core.knowledge.reference import get_reference_architecture_repository
            
            repo = get_use_case_repository()
            ref_repo = get_reference_architecture_repository()
            
            # Find relevant use cases for domain
            relevant_use_cases = [
                uc for uc in repo.list_all()
                if domain.lower() in uc.name.lower() or domain.lower() in uc.description.lower()
            ]
            
            # Find relevant patterns
            relevant_patterns = ref_repo.list_all()
            
            # Generate ideas based on patterns
            ideas = []
            for pattern in relevant_patterns[:3]:
                ideas.append({
                    "name": f"{pattern.name} for {domain}",
                    "type": pattern.type.value,
                    "description": pattern.description,
                    "platforms": pattern.platforms,
                    "components": pattern.components,
                    "quality_attributes": pattern.quality_attributes,
                })
            
            # Add use case based ideas
            for uc in relevant_use_cases[:2]:
                ideas.append({
                    "name": uc.name,
                    "type": "use_case",
                    "description": uc.description,
                    "platforms": uc.platforms,
                    "technologies": uc.technologies,
                })
            
            return ideas[:5]  # Return top 5 ideas
            
        except ImportError:
            # Fallback if knowledge base not available
            return [
                {
                    "name": f"Project for {domain}",
                    "type": "generic",
                    "description": f"A {domain} project using modern best practices",
                    "platforms": ["aws", "azure", "gcp"],
                }
            ]
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "domain" in input


class BrainstormTool(BaseTool):
    """Collaborative brainstorming session with idea expansion."""
    
    name = "brainstorm"
    description = "Expand and refine ideas through collaborative brainstorming"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        seeds = input.args.get("seed_ideas", [])
        focus_areas = input.args.get("focus_areas", [])
        expand_count = input.args.get("expand_count", 5)
        
        expanded = await self._expand_ideas(seeds, focus_areas, expand_count)
        
        return ToolOutput(
            result={
                "original_ideas": seeds,
                "expanded_ideas": expanded,
                "count": len(expanded),
            },
            metadata={"brainstormed": True}
        )
    
    async def _expand_ideas(
        self,
        seeds: List[str],
        focus_areas: List[str],
        count: int
    ) -> List[Dict[str, Any]]:
        """Expand seed ideas into more detailed concepts."""
        expanded = []
        
        # Expansion strategies
        strategies = [
            "automation",
            "integration",
            "optimization",
            "scaling",
            "security",
            "monitoring",
            "analytics",
        ]
        
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
    """Recommend technology stack based on requirements and constraints."""
    
    name = "technology_recommend"
    description = "Recommend technology stack based on requirements, constraints, and domain knowledge"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        requirements = input.args.get("requirements", {})
        constraints = input.args.get("constraints", {})
        domain = input.args.get("domain", "")
        
        recommendations = await self._recommend_technology(requirements, constraints, domain)
        
        return ToolOutput(
            result={
                "domain": domain,
                "recommendations": recommendations,
            },
            metadata={"recommended": True}
        )
    
    async def _recommend_technology(
        self,
        requirements: Dict[str, Any],
        constraints: Dict[str, Any],
        domain: str
    ) -> List[Dict[str, Any]]:
        """Recommend technology stack."""
        # Parse requirements
        scale = requirements.get("scale", "medium")
        realtime = requirements.get("realtime", False)
        analytics = requirements.get("analytics", False)
        budget = constraints.get("budget", "medium")
        
        recommendations = []
        
        # Compute recommendations
        if scale in ["large", "massive"]:
            recommendations.append({
                "category": "compute",
                "options": [
                    {"name": "AWS Lambda", "score": 0.9},
                    {"name": "Azure Functions", "score": 0.85},
                    {"name": "GCP Cloud Functions", "score": 0.8},
                ],
                "selected": "AWS Lambda",
            })
            recommendations.append({
                "category": "database",
                "options": [
                    {"name": "Amazon DynamoDB", "score": 0.9},
                    {"name": "Azure Cosmos DB", "score": 0.85},
                    {"name": "Google Firestore", "score": 0.8},
                ],
                "selected": "Amazon DynamoDB",
            })
        else:
            recommendations.append({
                "category": "compute",
                "options": [
                    {"name": "Kubernetes/EKS", "score": 0.9},
                    {"name": "Azure AKS", "score": 0.85},
                    {"name": "GCP GKE", "score": 0.8},
                ],
                "selected": "Kubernetes/EKS",
            })
            recommendations.append({
                "category": "database",
                "options": [
                    {"name": "PostgreSQL", "score": 0.95},
                    {"name": "MySQL", "score": 0.9},
                ],
                "selected": "PostgreSQL",
            })
        
        # Analytics
        if analytics:
            recommendations.append({
                "category": "analytics",
                "options": [
                    {"name": "AWS Athena", "score": 0.9},
                    {"name": "Azure Synapse", "score": 0.85},
                    {"name": "BigQuery", "score": 0.9},
                ],
                "selected": "BigQuery",
            })
        
        return recommendations
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "requirements" in input or "domain" in input


class PatternFinderTool(BaseTool):
    """Find architectural patterns for ideation."""
    
    name = "pattern_find"
    description = "Find architectural patterns from knowledge base for given context"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        context = input.args.get("context", "")
        platform = input.args.get("platform", "")
        
        patterns = await self._find_patterns(context, platform)
        
        return ToolOutput(
            result={
                "context": context,
                "platform": platform,
                "patterns": patterns,
            },
            metadata={"found": True}
        )
    
    async def _find_patterns(self, context: str, platform: str) -> List[Dict[str, Any]]:
        """Find relevant patterns."""
        try:
            from core.knowledge.reference import get_reference_architecture_repository
            
            ref_repo = get_reference_architecture_repository()
            patterns = ref_repo.list_all()
            
            # Filter by platform if specified
            if platform:
                patterns = [p for p in patterns if platform in p.platforms]
            
            # Filter by context if specified
            if context:
                patterns = [
                    p for p in patterns 
                    if context.lower() in p.name.lower() 
                    or context.lower() in p.description.lower()
                ]
            
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "type": p.type.value,
                    "description": p.description,
                    "platforms": p.platforms,
                    "components": p.components,
                    "quality_attributes": p.quality_attributes,
                }
                for p in patterns[:5]
            ]
            
        except ImportError:
            return []
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "context" in input


class MarketAnalysisTool(BaseTool):
    name = "market_analysis"
    description = "Analyze market trends and competitor landscapes"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        domain = input.args.get("domain", "")
        competitors = input.args.get("competitors", [])
        
        analysis = await self._analyze_market(domain, competitors)
        
        return ToolOutput(
            result={"domain": domain, "analysis": analysis},
            metadata={"analyzed": True}
        )
    
    async def _analyze_market(
        self,
        domain: str,
        competitors: List[str]
    ) -> Dict[str, Any]:
        return {
            "domain": domain,
            "trends": [
                {"name": "AI-native development", "growth": 45},
                {"name": "Platform engineering", "growth": 32},
                {"name": "Autonomous agents", "growth": 78},
            ],
            "competitors": competitors,
            "opportunities": [
                {"area": "Integration", "score": 0.85},
                {"area": "Automation", "score": 0.72},
            ],
        }
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "domain" in input


def register_ideation_tools(registry) -> None:
    registry.register(IdeaGeneratorTool())
    registry.register(BrainstormTool())
    registry.register(TechnologyRecommenderTool())
    registry.register(PatternFinderTool())
    registry.register(MarketAnalysisTool())