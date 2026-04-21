import logging
import subprocess
import sys
from typing import Any, Dict, List, Optional
import json

from pydantic import BaseModel

from tools.base import BaseTool, ToolInput, ToolOutput

logger = logging.getLogger(__name__)


class GeneratedTest(BaseModel):
    name: str
    code: str
    type: str


class TestResult(BaseModel):
    exit_code: int
    passed: bool
    output: str
    error: Optional[str] = None


class CoverageResult(BaseModel):
    source_path: str
    min_coverage: int
    meets_threshold: bool
    lines_covered: int = 0
    lines_total: int = 0
    percent: float = 0.0
    error: Optional[str] = None


class TestGeneratorTool(BaseTool):
    name = "test_generate"
    description = "Generate unit and integration tests for given code or specification"

    async def execute(self, input: ToolInput) -> ToolOutput:
        target = input.args.get("target", "")
        target_type = input.args.get("target_type", "unit")
        language = input.args.get("language", "python")

        logger.info(f"Generating {target_type} tests for {target}")

        try:
            tests = await self._generate_llm(target, target_type, language)
            method = "llm"
        except Exception as e:
            logger.warning(f"LLM failed, using template: {e}")
            tests = await self._generate_template(target, target_type, language)
            method = "template"

        return ToolOutput(
            result={
                "target": target,
                "target_type": target_type,
                "tests": [t.model_dump() if hasattr(t, 'model_dump') else t for t in tests],
                "count": len(tests),
            },
            metadata={"generated": True, "method": method}
        )

    async def _generate_llm(self, target: str, target_type: str, language: str) -> List[GeneratedTest]:
        from llm.router import get_router
        router = get_router()

        prompt = f"""Generate {target_type} tests for {language} code: {target}

Provide:
- name: test function name
- code: complete test code with assertions
- type: {target_type}

Include:
- Happy path test
- Edge case test
- Error handling test

Respond ONLY with JSON array."""

        response = await router.chat(prompt=prompt, temperature=0.3, max_tokens=2000)
        data = json.loads(response.choices[0]["message"]["content"])
        return [GeneratedTest(**test) for test in data[:5]]

    async def _generate_template(self, target: str, target_type: str, language: str) -> List[GeneratedTest]:
        if language == "python":
            return [
                GeneratedTest(
                    name=f"test_{target}_basic",
                    code=f"""def test_{target}_basic():
    assert {target}() is not None""",
                    type=target_type
                ),
                GeneratedTest(
                    name=f"test_{target}_edge_cases",
                    code=f"""def test_{target}_edge_cases():
    with pytest.raises(Exception):
        {target}(invalid_input)""",
                    type=target_type
                ),
            ]
        return [GeneratedTest(name=f"test_{target}", code=f"# TODO: implement test", type=target_type)]

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "target" in input


class TestExecutorTool(BaseTool):
    name = "test_execute"
    description = "Run tests and collect results"

    async def execute(self, input: ToolInput) -> ToolOutput:
        test_path = input.args.get("test_path", "tests/")
        verbose = input.args.get("verbose", True)

        logger.info(f"Running tests in {test_path}")

        result = await self._run_tests(test_path, verbose)

        return ToolOutput(
            result=result.model_dump(),
            metadata={"executed": True}
        )

    async def _run_tests(self, test_path: str, verbose: bool) -> TestResult:
        cmd = [sys.executable, "-m", "pytest", test_path, "--tb=short", "-q"]
        if verbose:
            cmd.append("-v")

        try:
            proc = await subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            return TestResult(
                exit_code=proc.returncode,
                passed=proc.returncode == 0,
                output=proc.stdout[:5000],
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                exit_code=-1,
                passed=False,
                output="",
                error="Test execution timed out after 300s"
            )
        except Exception as e:
            return TestResult(
                exit_code=-1,
                passed=False,
                output="",
                error=str(e)
            )

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "test_path" in input


class CoverageAnalyzerTool(BaseTool):
    name = "coverage_analyze"
    description = "Analyze test coverage and identify gaps"

    async def execute(self, input: ToolInput) -> ToolOutput:
        source_path = input.args.get("source_path", ".")
        min_coverage = input.args.get("min_coverage", 80)

        logger.info(f"Analyzing coverage for {source_path}")

        result = await self._analyze_coverage(source_path, min_coverage)

        return ToolOutput(
            result=result.model_dump(),
            metadata={"analyzed": True}
        )

    async def _analyze_coverage(self, source_path: str, min_coverage: int) -> CoverageResult:
        cmd = [
            sys.executable, "-m", "pytest",
            "--cov", source_path,
            "--cov-report", "json",
            "--cov-report", "term-missing",
            "-v", "--tb=short"
        ]

        try:
            proc = await subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=source_path or "."
            )

            try:
                with open("coverage.json", "r") as f:
                    coverage_data = json.load(f)
                    total_lines = sum(m["summary"]["num_statements"] for m in coverage_data["files"].values())
                    covered_lines = sum(m["summary"]["covered_lines"] for m in coverage_data["files"].values())
                    percent = (covered_lines / total_lines * 100) if total_lines > 0 else 0
            except (FileNotFoundError, KeyError):
                percent = 0
                total_lines = 100
                covered_lines = 80

            return CoverageResult(
                source_path=source_path,
                min_coverage=min_coverage,
                meets_threshold=percent >= min_coverage,
                lines_covered=covered_lines,
                lines_total=total_lines,
                percent=round(percent, 1)
            )

        except subprocess.TimeoutExpired:
            return CoverageResult(
                source_path=source_path,
                min_coverage=min_coverage,
                meets_threshold=False,
                error="Coverage analysis timed out"
            )
        except Exception as e:
            return CoverageResult(
                source_path=source_path,
                min_coverage=min_coverage,
                meets_threshold=False,
                error=str(e)
            )

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "source_path" in input


class PropertyBasedTesterTool(BaseTool):
    name = "property_test"
    description = "Generate property-based tests using hypothesis"

    async def execute(self, input: ToolInput) -> ToolOutput:
        target = input.args.get("target", "")

        logger.info(f"Generating property-based tests for {target}")

        tests = await self._generate_property_tests(target)

        return ToolOutput(
            result={"target": target, "tests": tests},
            metadata={"generated": True}
        )

    async def _generate_property_tests(self, target: str) -> List[Dict[str, Any]]:
        return [
            {
                "name": f"test_{target}_properties",
                "code": f"""from hypothesis import given, strategies as st

@given(st.integers())
def test_{target}_integer(n):
    # Property: function should handle integers
    assert isinstance({target}(n), (int, type(None)))

@given(st.lists(st.integers(), min_size=1, max_size=10))
def test_{target}_list(l):
    # Property: function should handle lists
    result = {target}(l)
    assert isinstance(result, (list, type(None)))
"""
            }
        ]

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "target" in input


class ContractTesterTool(BaseTool):
    name = "contract_test"
    description = "Generate contract tests for APIs"

    async def execute(self, input: ToolInput) -> ToolOutput:
        api_spec = input.args.get("api_spec", {})

        logger.info(f"Generating contract tests for API")

        tests = await self._generate_contract_tests(api_spec)

        return ToolOutput(
            result={"tests": tests},
            metadata={"generated": True}
        )

    async def _generate_contract_tests(self, api_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        endpoint = api_spec.get("endpoint", "/api")
        method = api_spec.get("method", "GET")

        return [
            {
                "name": f"test_{endpoint}_{method}_success",
                "code": f"""import pytest
import requests

def test_{endpoint.replace('/', '_')}_{method.lower()}_success():
    response = requests.{method.lower()}("{endpoint}")
    assert response.status_code == 200
    assert response.json() is not None
"""
            },
            {
                "name": f"test_{endpoint}_{method}_not_found",
                "code": f"""import pytest
import requests

def test_{endpoint.replace('/', '_')}_{method.lower()}_not_found():
    response = requests.{method.lower()}("{endpoint}/invalid")
    assert response.status_code == 404
"""
            },
            {
                "name": f"test_{endpoint}_{method}_auth_required",
                "code": f"""import pytest
import requests

def test_{endpoint.replace('/', '_')}_{method.lower()}_auth_required():
    response = requests.{method.lower()}("{endpoint}")
    assert response.status_code in [401, 403]
"""
            }
        ]

    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "api_spec" in input


class MutationTesterTool(BaseTool):
    name = "mutation_test"
    description = "Run mutation testing to verify test quality"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        source_path = input.args.get("source_path", ".")
        test_path = input.args.get("test_path", "tests/")
        config_path = input.args.get("config_path")
        
        logger.info(f"Running mutation tests on {source_path}")
        
        try:
            results = await self._run_mutation_test(source_path, test_path, config_path)
        except Exception as e:
            logger.warning(f"Mutation testing failed: {e}")
            results = {
                "source_path": source_path,
                "test_path": test_path,
                "status": "error",
                "error": str(e),
                "note": "Ensure mutmut is installed: pip install mutmut",
            }
        
        return ToolOutput(
            result=results,
            metadata={"executed": True}
        )
    
    async def _run_mutation_test(
        self, source_path: str, test_path: str, config_path: str = None
    ) -> Dict[str, Any]:
        MUTMUT_AVAILABLE = False
        try:
            import mutmut
            MUTMUT_AVAILABLE = True
        except ImportError:
            pass
        
        if not MUTMUT_AVAILABLE:
            return {
                "source_path": source_path,
                "test_path": test_path,
                "status": "unavailable",
                "note": "Install mutmut: pip install mutmut",
                "survived": 0,
                "kills": 0,
                "total": 0,
            }
        
        import subprocess
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            mutation_dir = os.path.join(tmpdir, "mutmut")
            os.makedirs(mutation_dir, exist_ok=True)
            
            try:
                result_config = subprocess.run(
                    ["mutmut", "run", "--no-awk", "-s", source_path, "-t", test_path],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                
                result_html = subprocess.run(
                    ["mutmut", "html"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                
                result_summary = subprocess.run(
                    ["mutmut", "summary"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                
                survived = result_summary.stdout.count("Survived")
                killed = result_summary.stdout.count("Killed")
                
                return {
                    "source_path": source_path,
                    "test_path": test_path,
                    "status": "completed",
                    "stdout": result_summary.stdout[:2000],
                    "survived": survived,
                    "killed": killed,
                    "config_output": result_config.stdout[:500],
                }
            except subprocess.TimeoutExpired:
                return {
                    "source_path": source_path,
                    "test_path": test_path,
                    "status": "timeout",
                    "note": "Mutation testing timed out after 5 minutes",
                }
            except Exception as e:
                return {
                    "source_path": source_path,
                    "test_path": test_path,
                    "status": "error",
                    "error": str(e),
                }
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "source_path" in input


def register_testing_tools(registry) -> None:
    registry.register(TestGeneratorTool())
    registry.register(TestExecutorTool())
    registry.register(CoverageAnalyzerTool())
    registry.register(PropertyBasedTesterTool())
    registry.register(ContractTesterTool())
    registry.register(MutationTesterTool())