"""
Validator Agent - Result validation and quality assurance.

Validates:
- Response accuracy against retrieved context
- Reasoning chain coherence
- Tool execution results
- Confidence scoring
"""

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.memory import get_memory_system

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationCategory(str, Enum):
    ACCURACY = "accuracy"
    COHERENCE = "coherence"
    COMPLETENESS = "completeness"
    CONFIDENCE = "confidence"
    SAFETY = "safety"


@dataclass
class ValidationIssue:
    category: str
    severity: str
    message: str
    evidence: List[str] = field(default_factory=list)
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    valid: bool
    score: float
    issues: List[ValidationIssue] = field(default_factory=list)
    confidence: float = 0.0
    citations_present: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class ValidatorAgent:
    def __init__(self, min_confidence: float = 0.7):
        self.min_confidence = min_confidence

    async def validate_response(
        self,
        query: str,
        response: str,
        retrieved_context: List[Dict[str, Any]],
        reasoning_trace: Optional[List[Dict[str, Any]]] = None,
        citations_present: bool = False,
    ) -> ValidationResult:
        issues = []
        total_checks = 0
        passed_checks = 0

        # Accuracy check: always runs (cheap, no LLM)
        accuracy_issues = await self._check_accuracy(query, response, retrieved_context)
        issues.extend(accuracy_issues)
        total_checks += 1
        if not accuracy_issues:
            passed_checks += 1

        # Faithfulness check: skip LLM call when citations are present
        if citations_present:
            logger.info(
                "Skipping LLM faithfulness check — citations present in response"
            )
            total_checks += 1
            passed_checks += 1
        else:
            llm_issues = await self._llm_faithfulness_check(query, response, retrieved_context)
            issues.extend(llm_issues)
            total_checks += 1
            if not llm_issues:
                passed_checks += 1

        coherence_issues = await self._check_coherence(response, reasoning_trace or [])
        issues.extend(coherence_issues)
        total_checks += 1
        if not coherence_issues:
            passed_checks += 1

        completeness_issues = await self._check_completeness(
            query, response, retrieved_context
        )
        issues.extend(completeness_issues)
        total_checks += 1
        if not completeness_issues:
            passed_checks += 1

        safety_issues = await self._check_safety(response)
        issues.extend(safety_issues)
        total_checks += 1
        if not safety_issues:
            passed_checks += 1

        score = passed_checks / total_checks if total_checks > 0 else 0.0

        has_errors = any(i.severity == ValidationSeverity.ERROR.value for i in issues)

        confidence = score
        if retrieved_context:
            coverage = len([r for r in retrieved_context if r.get("relevant")]) / len(
                retrieved_context
            )
            if coverage > 0.0:
                confidence = (score + coverage) / 2

        return ValidationResult(
            valid=not has_errors,
            score=score,
            issues=issues,
            confidence=confidence,
            citations_present=citations_present,
            metadata={
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "query_length": len(query),
                "response_length": len(response),
                "context_size": len(retrieved_context),
                "citations_present": citations_present,
            },
        )

    async def _check_accuracy(
        self,
        query: str,
        response: str,
        context: List[Dict[str, Any]],
    ) -> List[ValidationIssue]:
        issues = []

        if not context:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.ACCURACY.value,
                    severity=ValidationSeverity.WARNING.value,
                    message="No retrieved context available for validation",
                    suggestion="Ensure retrieval retrieved relevant documents",
                )
            )
            return issues

        response_lower = response.lower()
        query_terms = set(query.lower().split())

        for term in query_terms:
            if len(term) < 4:
                continue
            if term not in response_lower:
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.ACCURACY.value,
                        severity=ValidationSeverity.INFO.value,
                        message=f"Query term '{term}' not found in response",
                        evidence=[f"Context has {len(context)} entries"],
                    )
                )

        # Use token-level Jaccard similarity instead of naive prefix comparison
        low_overlap_sources = []
        for ctx in context[:3]:
            ctx_content = ctx.get("content", "").lower()
            if not ctx_content:
                continue
            ctx_tokens = set(ctx_content.split())
            resp_tokens = set(response_lower.split())
            if not ctx_tokens:
                continue
            intersection = ctx_tokens & resp_tokens
            union = ctx_tokens | resp_tokens
            jaccard = len(intersection) / len(union) if union else 0.0
            if jaccard < 0.1:
                low_overlap_sources.append(ctx.get("source", "unknown"))

        if len(low_overlap_sources) > 2:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.ACCURACY.value,
                    severity=ValidationSeverity.ERROR.value,
                    message="Response has low token overlap with context",
                    evidence=low_overlap_sources,
                    suggestion="Verify response against retrieved documents",
                )
            )

        return issues

    async def _llm_faithfulness_check(
        self,
        query: str,
        response: str,
        context: List[Dict[str, Any]],
    ) -> List[ValidationIssue]:
        """Use LLM to check if every claim in the response is supported by context."""
        issues = []
        try:
            from llm.router import get_router
            from core.llm_utils import extract_json_from_response

            router = get_router()
            context_text = "\n".join(
                f"- {c.get('content', '')[:300]}" for c in context[:5]
            )

            prompt = f"""Is every claim in this answer supported by the retrieved context?
Answer: {response[:1000]}
Context:
{context_text}

Return JSON: {{"supported": true/false, "unsupported_claims": ["claim1", "claim2"]}}
Return ONLY valid JSON."""

            result = await router.chat(prompt=prompt, temperature=0.1, max_tokens=500)
            data = extract_json_from_response(result)

            if data and isinstance(data, dict):
                if not data.get("supported", True):
                    unsupported = data.get("unsupported_claims", [])
                    if unsupported:
                        issues.append(ValidationIssue(
                            category=ValidationCategory.ACCURACY.value,
                            severity=ValidationSeverity.ERROR.value,
                            message=f"Response contains unsupported claims: {', '.join(unsupported[:3])}",
                            evidence=unsupported,
                            suggestion="Verify claims against retrieved context",
                        ))
        except Exception as e:
            logger.debug("LLM faithfulness check skipped: %s", e)

        return issues

    async def _check_coherence(
        self,
        response: str,
        reasoning_trace: List[Dict[str, Any]],
    ) -> List[ValidationIssue]:
        issues = []

        if not reasoning_trace:
            return issues

        trace_steps = [r.get("step", "") for r in reasoning_trace]
        if len(trace_steps) > 1:
            for i in range(len(trace_steps) - 1):
                if trace_steps[i] == trace_steps[i + 1]:
                    issues.append(
                        ValidationIssue(
                            category=ValidationCategory.COHERENCE.value,
                            severity=ValidationSeverity.WARNING.value,
                            message=f"Repeated step '{trace_steps[i]}' in reasoning chain",
                        )
                    )

        gaps = 0
        for trace in reasoning_trace:
            thinking = trace.get("thinking", "")
            if len(thinking) < 10 and trace != reasoning_trace[-1]:
                gaps += 1

        if gaps > len(reasoning_trace) // 2:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.COHERENCE.value,
                    severity=ValidationSeverity.WARNING.value,
                    message="Reasoning chain has gaps or missing context",
                    suggestion="Enhance reasoning steps with more detail",
                )
            )

        return issues

    async def _check_completeness(
        self,
        query: str,
        response: str,
        context: List[Dict[str, Any]],
    ) -> List[ValidationIssue]:
        issues = []

        question_words = {"what", "how", "why", "when", "where", "who", "which"}
        query_lower = query.lower()
        is_question = any(word in query_lower for word in question_words)

        if is_question and len(response) < 50:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.COMPLETENESS.value,
                    severity=ValidationSeverity.WARNING.value,
                    message="Response may be incomplete for question",
                    evidence=[f"Response length: {len(response)} chars"],
                    suggestion="Provide more detailed answer",
                )
            )

        if "?" in query and not response.endswith(("?", ".", "!")):
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.COMPLETENESS.value,
                    severity=ValidationSeverity.INFO.value,
                    message="Response doesn't clearly end sentence",
                )
            )

        required_topics = self._extract_topics(query)
        response_topics = self._extract_topics(response)

        missing = required_topics - response_topics
        if missing and len(missing) > len(required_topics) // 2:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.COMPLETENESS.value,
                    severity=ValidationSeverity.WARNING.value,
                    message=f"Missing topics: {', '.join(missing)}",
                    suggestion="Address all aspects of the query",
                )
            )

        return issues

    async def _check_safety(self, response: str) -> List[ValidationIssue]:
        issues = []

        dangerous_patterns = [
            (r"sudo\s+rm", "Potentially destructive command"),
            (r"DELETE\s+FROM", "SQL deletion command"),
            (r"drop\s+table", "Database destruction"),
            (r"rm\s+-rf", "Recursive force deletion"),
        ]

        for pattern, description in dangerous_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.SAFETY.value,
                        severity=ValidationSeverity.ERROR.value,
                        message=f"Potentially unsafe: {description}",
                        suggestion="Review and sanitize command",
                    )
                )

        return issues

    def _extract_topics(self, text: str) -> set:
        words = text.lower().split()
        return {w for w in words if len(w) >= 3} & {
            "api",
            "service",
            "config",
            "auth",
            "user",
            "data",
            "query",
            "system",
            "code",
            "document",
            "error",
            "file",
            "server",
            "database",
            "endpoint",
        }


_validator: Optional[ValidatorAgent] = None


def get_validator_agent() -> ValidatorAgent:
    global _validator
    if _validator is None:
        _validator = ValidatorAgent()
    return _validator
