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
            r"\bkubernetes\b",
            r"\bk8s\b",
            r"\bdeployment\b",
            r"\bservice\b\s+(?:mesh|account|port)",
            r"\bconfigmap\b",
            r"\bkubernetes\s+secret\b",
            r"\bingress\b",
            r"\bhelm\b",
            r"\bhelm\s+chart\b",
            r"\bvalues\.yaml\b",
            r"\bdockerfile\b",
            r"\bdocker\s+build\b",
            r"\bgraphql\b",
            r"\bgraphql\s+schema\b",
            r"\bgraphql\s+(?:query|mutation)\b",
            r"\bistio\b",
            r"\bvirtualservice\b",
            r"\bdestinationrule\b",
            r"\bistio\s+gateway\b",
        ]

        self._compile_patterns()

    def _compile_patterns(self):
        self.fact_re = [re.compile(p, re.IGNORECASE) for p in self.fact_patterns]
        self.relationship_re = [re.compile(p, re.IGNORECASE) for p in self.relationship_patterns]
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

        intents: List[Dict[str, Any]] = []

        for pattern in self.fact_re:
            if pattern.search(query):
                intents.append({"intent": QueryIntent.FACT.value, "confidence": 0.8})
                break

        for pattern in self.relationship_re:
            if pattern.search(query):
                intents.append({"intent": QueryIntent.RELATIONSHIP.value, "confidence": 0.9})
                break

        for pattern in self.code_relationship_re:
            if pattern.search(query):
                intents.append({"intent": QueryIntent.CODE_RELATIONSHIP.value, "confidence": 0.9})
                break

        for pattern in self.causal_re:
            if pattern.search(query):
                intents.append({"intent": QueryIntent.CAUSAL.value, "confidence": 0.9})
                break

        for pattern in self.list_re:
            if pattern.search(query):
                intents.append({"intent": QueryIntent.LIST.value, "confidence": 0.7})
                break

        for pattern in self.code_re:
            if pattern.search(query):
                intents.append({"intent": QueryIntent.CODE.value, "confidence": 0.6})
                break

        for pattern in self.doc_re:
            if pattern.search(query):
                intents.append({"intent": QueryIntent.DOCUMENTATION.value, "confidence": 0.7})
                break

        for pattern in self.tooling_re:
            if pattern.search(query):
                intents.append({"intent": QueryIntent.TOOLING.value, "confidence": 0.7})
                break

        if len(words) > 10:
            if not any(i["intent"] == QueryIntent.COMPLEX.value for i in intents):
                intents.append({"intent": QueryIntent.COMPLEX.value, "confidence": 0.5})

        if not intents:
            intents.append({"intent": QueryIntent.FACT.value, "confidence": 0.3})

        # Sort by confidence descending
        intents.sort(key=lambda x: x["confidence"], reverse=True)

        primary_intent = QueryIntent(intents[0]["intent"])
        intent_enums = [QueryIntent(i["intent"]) for i in intents]
        strategy = self._determine_strategy(primary_intent, intent_enums)

        result = {
            "query": query,
            "intents": intents,
            "primary_intent": primary_intent.value,
            "strategy": strategy.value,
            "requires_graph": primary_intent
            in [
                QueryIntent.RELATIONSHIP,
                QueryIntent.CAUSAL,
                QueryIntent.CODE_RELATIONSHIP,
            ],
            "requires_code_graph": primary_intent == QueryIntent.CODE_RELATIONSHIP,
            "requires_vector": primary_intent
            in [QueryIntent.FACT, QueryIntent.LIST, QueryIntent.DOCUMENTATION],
            "complexity": self._estimate_complexity(query),
        }

        if any(i["intent"] == QueryIntent.TOOLING.value for i in intents):
            result["tooling_sources"] = self._extract_tooling_sources(query)

        if any(i["intent"] == QueryIntent.CODE_RELATIONSHIP.value for i in intents):
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
        has_comparison = any(w in query.lower() for w in ["vs", "versus", "compared", "difference"])
        has_negation = any(w in query.lower() for w in ["not", "without", "except"])
        has_aggregation = any(w in query.lower() for w in ["all", "every", "total", "sum"])

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
            if (
                re.search(r"\bkubernetes\b|\bk8s\b|\bdeployment\b", query_lower)
                or re.search(r"\bservice\b\s+(?:mesh|account|port)", query_lower)
                or re.search(r"\bconfigmap\b|\bingress\b|\bsecret\b", query_lower)
            ):
                sources.append("kubernetes")
            if re.search(r"\bhelm\b|\bchart\b|\bvalues\.yaml\b", query_lower):
                sources.append("helm")
            if re.search(r"\bdockerfile\b|\bdocker\s+build\b", query_lower):
                sources.append("dockerfile")
            if re.search(r"\bgraphql\b|\bschema\b", query_lower):
                sources.append("graphql")
            if re.search(r"\bistio\b|\bvirtualservice\b", query_lower) or re.search(
                r"\bdestinationrule\b|\bgateway\b", query_lower
            ):
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
