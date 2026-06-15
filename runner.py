#!/usr/bin/env python3
"""CLI utility — imports a solution module and runs algorithm tests against it."""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import sys
import traceback
from pathlib import Path


def load_solution(path: Path):
    """Import a solution module from *path* as ``algo_monster_solution``."""
    spec = importlib.util.spec_from_file_location("algo_monster_solution", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load solution module.")
    module = importlib.util.module_from_spec(spec)
    sys.modules["algo_monster_solution"] = module
    spec.loader.exec_module(module)
    return module


def _generate_test_code(test: dict, function_name: str) -> str:
    """Generate test code from input/output fields when 'code' is missing."""
    if "code" in test and isinstance(test["code"], str):
        return test["code"]

    name = test.get("name", "Unnamed test")
    expected = test.get("output")
    input_expr = test.get("input", "")

    code = f"# Test: {name}\n"
    if input_expr:
        code += f"_args = {input_expr}\n"
        code += f"_result = {function_name}(*_args) if isinstance(_args, tuple) else {function_name}(_args)\n"
    else:
        code += f"_result = {function_name}()\n"
    if expected is not None:
        expected_str = json.dumps(expected) if not isinstance(expected, str) else expected
        code += f"assert _result == {expected_str}\n"

    return code


def load_tests(path: Path) -> list[dict]:
    """Parse *tests.json*, supporting both 'code' and 'input'/'output' formats."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        # { "function": "binary_search", "test_cases": [...] } format
        function_name = data.get("function", "solution")
        tests_list = data.get("test_cases", data.get("tests", []))
        for test in tests_list:
            if "code" not in test or not isinstance(test["code"], str):
                test["code"] = _generate_test_code(test, function_name)
        return tests_list
    if not isinstance(data, list):
        raise ValueError("tests.json must contain a list.")
    return data


def run_test(test: dict, namespace: dict) -> dict:
    """Execute one test's code in *namespace*; return a result dict."""
    name = test.get("name", "Unnamed test")
    code = test.get("code")
    if not isinstance(code, str):
        return {
            "name": name,
            "passed": False,
            "error": "Test has no code.",
            "stdout": "",
        }

    stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout):
            exec(code, namespace, namespace)
        return {"name": name, "passed": True, "error": "", "stdout": stdout.getvalue()}
    except Exception:
        return {
            "name": name,
            "passed": False,
            "error": traceback.format_exc(limit=4),
            "stdout": stdout.getvalue(),
        }


def main() -> None:
    """CLI entry point — loads solution + tests, runs them, prints JSON result."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--algorithm-dir", required=True)
    parser.add_argument("--solution", required=True)
    parser.add_argument("--test-index", type=int)
    args = parser.parse_args()

    algorithm_dir = Path(args.algorithm_dir)
    solution_path = Path(args.solution)

    try:
        module = load_solution(solution_path)
        tests = load_tests(algorithm_dir / "tests.json")
    except Exception:
        result = {
            "ok": False,
            "summary": {"passed": 0, "failed": 1, "total": 1},
            "results": [
                {
                    "name": "Load solution",
                    "passed": False,
                    "error": traceback.format_exc(limit=4),
                    "stdout": "",
                }
            ],
        }
        print(json.dumps(result))
        return

    selected_tests = tests
    if args.test_index is not None:
        if args.test_index < 0 or args.test_index >= len(tests):
            result = {
                "ok": False,
                "summary": {"passed": 0, "failed": 1, "total": 1},
                "results": [
                    {
                        "name": "Select test",
                        "passed": False,
                        "error": "Test index is out of range.",
                        "stdout": "",
                    }
                ],
            }
            print(json.dumps(result))
            return
        selected_tests = [tests[args.test_index]]

    namespace = dict(vars(module))
    results = [run_test(test, namespace) for test in selected_tests]
    passed = sum(1 for result in results if result["passed"])
    failed = len(results) - passed
    print(
        json.dumps(
            {
                "ok": failed == 0,
                "summary": {"passed": passed, "failed": failed, "total": len(results)},
                "results": results,
            }
        )
    )


if __name__ == "__main__":
    main()
