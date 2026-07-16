from typing import Any, Dict, List, Optional


class EvaluationCase:
    def __init__(
        self,
        id: str,
        query: str,
        expected_aspects: List[str],
        ground_truth: Optional[str] = None,
    ):
        self.id = id
        self.query = query
        self.expected_aspects = expected_aspects
        self.ground_truth = ground_truth


class EvaluationResult:
    def __init__(
        self,
        case_id: str,
        correctness: float,
        relevance: float,
        architecture_quality: float,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.case_id = case_id
        self.correctness = correctness
        self.relevance = relevance
        self.architecture_quality = architecture_quality
        self.details = details or {}

    @property
    def overall(self) -> float:
        return (self.correctness + self.relevance + self.architecture_quality) / 3.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "correctness": self.correctness,
            "relevance": self.relevance,
            "architecture_quality": self.architecture_quality,
            "overall": self.overall,
            "details": self.details,
        }


TEST_CASES = [
    EvaluationCase(
        id="tc001",
        query="How does the authentication flow work?",
        expected_aspects=["auth", "flow", "login"],
        ground_truth="OAuth2 with JWT tokens",
    ),
    EvaluationCase(
        id="tc002",
        query="What components are in the architecture?",
        expected_aspects=["components", "services", "API"],
        ground_truth="API, Auth, Database services",
    ),
    EvaluationCase(
        id="tc003",
        query="Show me the login implementation",
        expected_aspects=["login", "function", "code"],
        ground_truth="Function in auth.py",
    ),
    EvaluationCase(
        id="tc004",
        query="What are the open tickets?",
        expected_aspects=["tickets", "open", "status"],
        ground_truth="T001, T002",
    ),
    EvaluationCase(
        id="tc005",
        query="Check system performance",
        expected_aspects=["metrics", "performance", "CPU"],
        ground_truth="CPU usage 45%",
    ),
]


class EvaluationFramework:
    def __init__(self):
        self.test_cases = TEST_CASES

    def _evaluate_correctness(self, answer: str, ground_truth: Optional[str]) -> float:
        if not ground_truth:
            return 0.5

        answer_lower = answer.lower()
        truth_lower = ground_truth.lower()

        if truth_lower in answer_lower:
            return 1.0

        keywords = truth_lower.split()
        matched = sum(1 for kw in keywords if kw in answer_lower)

        return matched / len(keywords) if keywords else 0.0

    def _evaluate_relevance(self, answer: str, expected_aspects: List[str]) -> float:
        answer_lower = answer.lower()

        matched = sum(1 for aspect in expected_aspects if aspect in answer_lower)

        return matched / len(expected_aspects) if expected_aspects else 0.0

    def _evaluate_architecture_quality(self, answer: str, query: str) -> float:
        score = 0.5

        if "architecture" in query.lower():
            if any(kw in answer.lower() for kw in ["component", "service", "api"]):
                score += 0.25

        if any(kw in answer.lower() for kw in ["database", "cache", "queue"]):
            score += 0.25

        return min(score, 1.0)

    async def evaluate(self, case_id: str, answer: str) -> Optional[EvaluationResult]:
        case = None
        for tc in self.test_cases:
            if tc.id == case_id:
                case = tc
                break

        if not case:
            return None

        correctness = self._evaluate_correctness(answer, case.ground_truth)
        relevance = self._evaluate_relevance(answer, case.expected_aspects)
        arch_quality = self._evaluate_architecture_quality(answer, case.query)

        return EvaluationResult(
            case_id=case_id,
            correctness=correctness,
            relevance=relevance,
            architecture_quality=arch_quality,
            details={
                "query": case.query,
                "answer": answer[:100],
                "expected_aspects": case.expected_aspects,
            },
        )

    async def run_all(self, answers: Dict[str, str]) -> List[EvaluationResult]:
        results = []

        for case_id, answer in answers.items():
            result = await self.evaluate(case_id, answer)
            if result:
                results.append(result)

        return results

    def get_summary(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        if not results:
            return {"overall": 0.0, "count": 0}

        overall_scores = [r.overall for r in results]

        return {
            "overall": sum(overall_scores) / len(overall_scores),
            "count": len(results),
            "correctness_avg": sum(r.correctness for r in results) / len(results),
            "relevance_avg": sum(r.relevance for r in results) / len(results),
            "architecture_quality_avg": sum(r.architecture_quality for r in results)
            / len(results),
        }


_evaluation_framework: Optional[EvaluationFramework] = None


def get_evaluation_framework() -> EvaluationFramework:
    global _evaluation_framework
    if _evaluation_framework is None:
        _evaluation_framework = EvaluationFramework()
    return _evaluation_framework
