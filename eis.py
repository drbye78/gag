#!/usr/bin/env python3
"""
Engineering Intelligence System - CLI Wrapper

Simplifies running the project without 'uv run' prefix.
Automatically detects and uses the virtual environment.
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
UV = "uv"


def get_python():
    """Get Python executable from venv or fall back to system."""
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    return sys.executable


def run_command(cmd, use_uv=False, capture=False):
    """Run a command with the appropriate Python."""
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    if use_uv:
        result = subprocess.run(
            [UV, "run", "python", "-c", cmd] if cmd.startswith("import") else [UV, "run"] + cmd.split(),
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=capture,
            text=True,
        )
    else:
        python = get_python()
        result = subprocess.run(
            python + " -c " + cmd if cmd else python.split() + cmd.split(),
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=capture,
            text=True,
            shell=True,
        )

    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def cmd_api(args):
    """Start the API server."""
    host = args.host or "0.0.0.0"
    port = args.port or "8000"
    reload = "--reload" if args.reload else ""

    print(f"Starting API at http://{host}:{port}")
    return subprocess.run(
        [get_python(), "-m", "uvicorn", "api.main:app", "--host", host, "--port", port, reload],
        cwd=PROJECT_ROOT,
    ).returncode


def cmd_test(args):
    """Run tests."""
    if args.file:
        cmd = f"-m pytest tests/{args.file} -v"
    elif args.keyword:
        cmd = f'-m pytest -k "{args.keyword}" -v'
    elif args.unit:
        cmd = "-m pytest tests/test_core.py tests/test_agents.py -v"
    else:
        cmd = "-m pytest tests/ -v"

    print(f"Running: {cmd}")
    return subprocess.run(
        f'{get_python()} {cmd}',
        cwd=PROJECT_ROOT,
        shell=True,
    ).returncode


def cmd_shell(args):
    """Start an interactive Python shell."""
    print("Starting Python shell... (Ctrl+D to exit)")
    return subprocess.run(
        [get_python()],
        cwd=PROJECT_ROOT,
    ).returncode


def cmd_install(args):
    """Install dependencies."""
    return subprocess.run(
        [UV, "pip", "install", "-r", "requirements.txt"],
        cwd=PROJECT_ROOT,
    ).returncode


def cmd_check(args):
    """Run linting and type checking."""
    print("Running ruff...")
    result = subprocess.run(
        [get_python(), "-m", "ruff", "check", "."],
        cwd=PROJECT_ROOT,
        capture_output=True,
    )
    if result.returncode == 0:
        print("✓ Ruff: OK")

    print("Running pyright...")
    result = subprocess.run(
        [get_python(), "-m", "pyright", "."],
        cwd=PROJECT_ROOT,
        capture_output=True,
    )
    if result.returncode == 0:
        print("✓ Pyright: OK")

    return 0


def cmd_eval(args):
    """Run evaluation against known test cases."""
    from evaluation.test_cases import TEST_CASES, get_evaluation_framework

    results_dir = PROJECT_ROOT / "evaluation" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    framework = get_evaluation_framework()

    async def run_eval():
        from agents.orchestration import get_orchestration_engine

        engine = get_orchestration_engine()

        cases = TEST_CASES[: args.limit] if args.limit else TEST_CASES
        if args.case:
            cases = [c for c in TEST_CASES if c.id == args.case]
            if not cases:
                print(
                    f"Test case '{args.case}' not found. "
                    f"Available: {[c.id for c in TEST_CASES]}"
                )
                return 1

        print(f"Running {len(cases)} evaluation cases...")
        print("=" * 60)

        eval_results = []

        for i, case in enumerate(cases, 1):
            print(f"\n[{i}/{len(cases)}] {case.id}: {case.query}")
            start = time.time()

            try:
                result = await engine.execute(case.query, max_iterations=2)
                answer = result.get("answer", "")
                answer = str(answer) if answer else ""
                took_ms = int((time.time() - start) * 1000)
            except Exception as e:
                answer = f"ERROR: {e}"
                took_ms = int((time.time() - start) * 1000)

            eval_result = await framework.evaluate(case.id, answer)
            if eval_result:
                eval_results.append(eval_result)
                print(
                    f"  Score: {eval_result.overall:.2f} | "
                    f"C:{eval_result.correctness:.2f} "
                    f"R:{eval_result.relevance:.2f} "
                    f"A:{eval_result.architecture_quality:.2f} | {took_ms}ms"
                )
            else:
                print(f"  No evaluation result | {took_ms}ms")

        # Print summary
        summary = framework.get_summary(eval_results)

        print()
        print("=" * 60)
        print("EVALUATION SUMMARY")
        print("=" * 60)
        print(f"  Cases:      {summary['count']}")
        print(f"  Overall:    {summary['overall']:.2%}")
        print(f"  Correctness:{summary.get('correctness_avg', 0):.2%}")
        print(f"  Relevance:  {summary.get('relevance_avg', 0):.2%}")
        print(f"  Arch Qual:  {summary.get('architecture_quality_avg', 0):.2%}")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = results_dir / f"eval_{timestamp}.json"
        report = {
            "timestamp": timestamp,
            "summary": summary,
            "results": [r.to_dict() for r in eval_results],
        }

        report_path.write_text(json.dumps(report, indent=2))
        print(f"\nResults saved to: {report_path}")

        return 0

    return asyncio.run(run_eval())


def main():
    parser = argparse.ArgumentParser(
        description="Engineering Intelligence System CLI",
        prog="eis.py"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # api command
    api_parser = subparsers.add_parser("api", help="Start the API server")
    api_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    api_parser.add_argument("--port", default="8000", help="Port to bind to")
    api_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # test command
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument("--file", help="Specific test file (e.g., test_core.py)")
    test_parser.add_argument("--keyword", help="Test keyword to filter")
    test_parser.add_argument("--unit", action="store_true", help="Run unit tests only")

    # shell command
    shell_parser = subparsers.add_parser("shell", help="Start Python shell")

    # install command
    install_parser = subparsers.add_parser("install", help="Install dependencies")

    # check command
    check_parser = subparsers.add_parser("check", help="Run linting and type checking")

    # eval command
    eval_parser = subparsers.add_parser("eval", help="Run evaluation pipeline")
    eval_parser.add_argument("--limit", type=int, help="Limit number of test cases")
    eval_parser.add_argument("--case", help="Run a specific test case by ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "api": cmd_api,
        "test": cmd_test,
        "shell": cmd_shell,
        "install": cmd_install,
        "check": cmd_check,
        "eval": cmd_eval,
    }

    return commands.get(args.command, lambda a: parser.print_help())(args)


if __name__ == "__main__":
    sys.exit(main())