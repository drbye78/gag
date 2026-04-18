"""
Query Intent Classifier - Routes queries to optimal retrieval strategy.

Classifies queries into: FACT, RELATIONSHIP, CAUSAL, LIST, COMPLEX
to determine whether to use vector, graph, or hybrid retrieval.
"""

import re
from enum import Enum
from typing import Any, Dict, List, Optional


class QueryIntent(str, Enum):
    FACT = "fact"
    RELATIONSHIP = "relationship"
    CODE_RELATIONSHIP = "code_relationship"
    CAUSAL = "causal"
    LIST = "list"
    COMPLEX = "complex"
    CODE = "code"
    DOCUMENTATION = "documentation"
    TOOLING = "tooling"


class RetrievalStrategy(str, Enum):
    VECTOR_ONLY = "vector_only"
    GRAPH_ONLY = "graph_only"
    HYBRID = "hybrid"
    MULTI_HOP = "multi_hop"
    CASCADE = "cascade"
    ITERATIVE = "iterative"


class QueryClassifier:
    def __init__(self):
        self.fact_patterns = [
            r"^what is",
            r"^what does",
            r"^what is the",
            r"^define",
            r"^how do i use",
            r"^how to use",
            r"^find the",
        ]

        self.relationship_patterns = [
            r"who calls",
            r"who uses",
            r"who imports",
            r"what calls",
            r"what uses",
            r"what imports",
            r"depends on",
            r"related to",
            r"connected to",
            r"relationship between",
            r"trace",
        ]

        self.code_relationship_patterns = [
            r"find callers",
            r"find callees",
            r"all callers",
            r"all callees",
            r"functions that call",
            r"functions called by",
            r"who implements",
            r"overrides",
            r"parent class",
            r"class hierarchy",
            r"imports from",
            r"modules that import",
            r"dead code",
            r"unused function",
            r"unused method",
            r"never called",
            r"complexity of",
            r"cyclomatic",
            r"most complex",
            r"highest complexity",
            r"module dependencies",
            r"depends on module",
            r"call chain",
            r"execution trace",
            r"go to definition",
            r"find definition",
        ]

        self.causal_patterns = [
            r"^why",
            r"^how did",
            r"reason for",
            r"cause of",
            r"leads to",
            r"results in",
            r"triggered by",
            r"fails because",
            r"error when",
        ]

        self.list_patterns = [
            r"^list",
            r"^show all",
            r"^get all",
            r"^find all",
            r"^enumerate",
            r"all functions",
            r"all classes",
            r"all endpoints",
            r"all methods",
        ]

        self.code_patterns = [
            r"function\s+\w+",
            r"class\s+\w+",
            r"method\s+\w+",
            r"def\s+\w+",
            r"import\s+",
            r"from\s+\w+\s+import",
            r"api\s+endpoint",
            r"route\s+",
            r"controller\s+",
            r"\(\)\s*\{",
        ]

        self.doc_patterns = [
            r"documentation",
            r"docs",
            r"readme",
            r"guide",
            r"tutorial",
            r"example",
            r"how-to",
        ]

        self.tooling_patterns = [
            r"kubernetes",
            r"k8s",
            r"deployment",
            r"service",
            r"configmap",
            r"secret",
            r"ingress",
            r"helm",
            r"chart",
            r"values\.yaml",
            r"dockerfile",
            r"from\s+\w+",
            r"docker\s+build",
            r"graphql",
            r"schema",
            r"query",
            r"mutation",
            r"type\s+\w+",
            r"istio",
            r"virtualservice",
            r"destinationrule",
            r"gateway",
        ]

        self._compile_patterns()

    def _compile_patterns(self):
        self.fact_re = [re.compile(p, re.IGNORECASE) for p in self.fact_patterns]
        self.relationship_re = [
            re.compile(p, re.IGNORECASE) for p in self.relationship_patterns
        ]
        self.code_relationship_re = [
            re.compile(p, re.IGNORECASE) for p in self.code_relationship_patterns
        ]
        self.causal_re = [re.compile(p, re.IGNORECASE) for p in self.causal_patterns]
        self.list_re = [re.compile(p, re.IGNORECASE) for p in self.list_patterns]
        self.code_re = [re.compile(p, re.IGNORECASE) for p in self.code_patterns]
        self.doc_re = [re.compile(p, re.IGNORECASE) for p in self.doc_patterns]
        self.tooling_re = [re.compile(p, re.IGNORECASE) for p in self.tooling_patterns]

    def classify(self, query: str) -> Dict[str, Any]:
        query_lower = query.lower()
        words = query_lower.split()

        intents = []
        for pattern in self.fact_re:
            if pattern.search(query):
                intents.append(QueryIntent.FACT)
                break

        for pattern in self.relationship_re:
            if pattern.search(query):
                intents.append(QueryIntent.RELATIONSHIP)
                break

        for pattern in self.code_relationship_re:
            if pattern.search(query):
                intents.append(QueryIntent.CODE_RELATIONSHIP)
                break

        for pattern in self.causal_re:
            if pattern.search(query):
                intents.append(QueryIntent.CAUSAL)
                break

        for pattern in self.list_re:
            if pattern.search(query):
                intents.append(QueryIntent.LIST)
                break

        for pattern in self.code_re:
            if pattern.search(query):
                intents.append(QueryIntent.CODE)
                break

        for pattern in self.doc_re:
            if pattern.search(query):
                intents.append(QueryIntent.DOCUMENTATION)
                break

        for pattern in self.tooling_re:
            if pattern.search(query):
                intents.append(QueryIntent.TOOLING)
                break

        if len(words) > 10:
            if QueryIntent.COMPLEX not in intents:
                intents.append(QueryIntent.COMPLEX)

        if not intents:
            intents.append(QueryIntent.FACT)

        primary = intents[0]
        strategy = self._determine_strategy(primary, intents)

        result = {
            "query": query,
            "intents": [i.value for i in intents],
            "primary_intent": primary.value,
            "strategy": strategy.value,
            "requires_graph": primary
            in [
                QueryIntent.RELATIONSHIP,
                QueryIntent.CAUSAL,
                QueryIntent.CODE_RELATIONSHIP,
            ],
            "requires_code_graph": primary == QueryIntent.CODE_RELATIONSHIP,
            "requires_vector": primary
            in [QueryIntent.FACT, QueryIntent.LIST, QueryIntent.DOCUMENTATION],
            "complexity": self._estimate_complexity(query),
        }

        if QueryIntent.TOOLING in intents:
            result["tooling_sources"] = self._extract_tooling_sources(query)

        if QueryIntent.CODE_RELATIONSHIP in intents:
            result["codegraph_method"] = self._extract_codegraph_method(query)

        return result

    def _determine_strategy(
        self, primary: QueryIntent, intents: List[QueryIntent]
    ) -> RetrievalStrategy:
        complexity = self._estimate_complexity(primary.value)

        if complexity == "high":
            return RetrievalStrategy.ITERATIVE
        elif QueryIntent.RELATIONSHIP in intents or QueryIntent.CAUSAL in intents:
            return RetrievalStrategy.MULTI_HOP
        elif QueryIntent.CODE_RELATIONSHIP in intents:
            return RetrievalStrategy.HYBRID
        elif len(intents) > 1:
            return RetrievalStrategy.HYBRID
        elif primary == QueryIntent.CODE:
            return RetrievalStrategy.CASCADE
        elif primary == QueryIntent.FACT:
            return RetrievalStrategy.ITERATIVE
        elif primary == QueryIntent.LIST:
            return RetrievalStrategy.CASCADE
        else:
            return RetrievalStrategy.VECTOR_ONLY

    def _estimate_complexity(self, query: str) -> str:
        words = query.split()
        has_comparison = any(
            w in query.lower() for w in ["vs", "versus", "compared", "difference"]
        )
        has_negation = any(w in query.lower() for w in ["not", "without", "except"])
        has_aggregation = any(
            w in query.lower() for w in ["all", "every", "total", "sum"]
        )

        score = len(words) / 10.0
        if has_comparison:
            score += 1
        if has_negation:
            score += 0.5
        if has_aggregation:
            score += 0.5

        if score >= 2:
            return "high"
        elif score >= 1:
            return "medium"
        else:
            return "low"

    def get_sources(self, classification: Dict[str, Any]) -> List[str]:
        primary = classification.get("primary_intent")
        strategy = classification.get("strategy")
        requires_graph = classification.get("requires_graph", False)
        requires_vector = classification.get("requires_vector", True)

        sources = []
        if requires_vector:
            sources.append("code")
            sources.append("docs")
        if requires_graph:
            sources.append("graph")

        if strategy == RetrievalStrategy.HYBRID.value:
            sources = ["code", "graph", "docs"]
        elif strategy == RetrievalStrategy.MULTI_HOP.value:
            sources = ["graph", "code"]
        elif strategy == RetrievalStrategy.VECTOR_ONLY.value:
            sources = ["code", "docs"]

        if primary == QueryIntent.TOOLING.value:
            tooling_sources = classification.get("tooling_sources", [])
            sources.extend(tooling_sources)

        return list(dict.fromkeys(sources))

    def _extract_tooling_sources(self, query: str) -> List[str]:
        query_lower = query.lower()
        sources = []
        if any(p.search(query_lower) for p in self.tooling_re):
            if "kubernetes" in query_lower or "k8s" in query_lower or \
               "deployment" in query_lower or "service" in query_lower or \
               "configmap" in query_lower or "ingress" in query_lower:
                sources.append("kubernetes")
            if "helm" in query_lower or "chart" in query_lower:
                sources.append("helm")
            if "dockerfile" in query_lower or "docker" in query_lower:
                sources.append("dockerfile")
            if "graphql" in query_lower or "schema" in query_lower:
                sources.append("graphql")
            if "istio" in query_lower or "virtualservice" in query_lower or \
               "destinationrule" in query_lower or "gateway" in query_lower:
                sources.append("istio")
            if not sources:
                sources.append("kubernetes")
        return sources

    def _extract_codegraph_method(self, query: str) -> Optional[str]:
        query_lower = query.lower()
        
        patterns = {
            "find_callers": [r"find callers", r"who calls", r"functions that call"],
            "find_callees": [r"find callees", r"called by", r"callees"],
            "dead_code": [r"dead code", r"unused function", r"unused method", r"never called"],
            "complexity": [r"complexity of", r"cyclomatic"],
            "class_hierarchy": [r"class hierarchy", r"inheritance", r"parent class"],
            "module_deps": [r"module dependencies", r"depends on module"],
            "call_chain": [r"call chain", r"execution trace"],
        }
        
        for method, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, query_lower):
                    return method
        return None


_classifier: Optional[QueryClassifier] = None


def get_query_classifier() -> QueryClassifier:
    global _classifier
    if _classifier is None:
        _classifier = QueryClassifier()
    return _classifier
