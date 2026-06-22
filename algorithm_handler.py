#!/usr/bin/env python3
"""Algorithm Monster specific logic: loading algorithms, running tests, managing progress."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from utils import (
    ALGORITHMS_DIR,
    PROGRESS_PATH,
    RUNNER,
    SOLUTIONS_DIR,
    TIMEOUT_SECONDS,
    load_json,
    write_json,
)


def validate_config_algo() -> None:
    """Ensure config directories and progress file exist."""
    SOLUTIONS_DIR.mkdir(parents=True, exist_ok=True)
    if not PROGRESS_PATH.exists():
        PROGRESS_PATH.write_text("{}", encoding="utf-8")


def algorithm_ids() -> set[str]:
    """Return the set of available algorithm directory names."""
    if not ALGORITHMS_DIR.exists():
        return set()
    return {path.name for path in ALGORITHMS_DIR.iterdir() if path.is_dir() and (path / "meta.json").exists()}


def safe_algorithm_id(raw_id: str) -> str:
    """Validate and URL-decode *raw_id*, raising KeyError if unknown."""
    from urllib.parse import unquote
    algo_id = unquote(raw_id.lstrip("/"))
    if algo_id not in algorithm_ids():
        raise KeyError(algo_id)
    return algo_id


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


def read_algorithm(algo_id: str) -> dict:
    """Read an algorithm's metadata, prompt, starter code, and test list."""
    algo_dir = ALGORITHMS_DIR / algo_id
    meta = load_json(algo_dir / "meta.json", {})
    tests_raw = load_json(algo_dir / "tests.json", [])
    if isinstance(tests_raw, dict):
        function_name = tests_raw.get("function", "solution")
        tests_list = tests_raw.get("test_cases", tests_raw.get("tests", []))
        tests = []
        for index, test in enumerate(tests_list):
            code = test.get("code")
            if not code or not isinstance(code, str):
                code = _generate_test_code(test, function_name)
            tests.append({"name": test.get("name", f"Test {index + 1}"), "code": code})
    else:
        tests = [
            {"name": test.get("name", f"Test {index + 1}"), "code": test["code"]}
            for index, test in enumerate(tests_raw)
        ]
    return {
        "id": algo_id,
        "meta": meta,
        "prompt": (algo_dir / "prompt.md").read_text(encoding="utf-8"),
        "starter": (algo_dir / "starter.py").read_text(encoding="utf-8"),
        "tests": tests,
    }


def solution_path(algo_id: str) -> Path:
    """Return the Path where the saved solution for *algo_id* lives."""
    return SOLUTIONS_DIR / f"{algo_id}.py"


def read_solution(algo_id: str) -> str:
    """Read saved solution for *algo_id*, falling back to the starter template."""
    saved = solution_path(algo_id)
    if saved.exists():
        return saved.read_text(encoding="utf-8")
    return (ALGORITHMS_DIR / algo_id / "starter.py").read_text(encoding="utf-8")


def save_solution(algo_id: str, code: str) -> None:
    """Write *code* as the saved solution for *algo_id*."""
    SOLUTIONS_DIR.mkdir(parents=True, exist_ok=True)
    solution_path(algo_id).write_text(code, encoding="utf-8")


def load_progress() -> dict:
    """Load user progress from config, guaranteeing a dict return."""
    validate_config_algo()
    progress = load_json(PROGRESS_PATH, {})
    return progress if isinstance(progress, dict) else {}


def save_progress(progress: dict) -> None:
    """Persist *progress* to disk."""
    validate_config_algo()
    write_json(PROGRESS_PATH, progress)


def run_tests(algo_id: str, code: str, test_index: int | None) -> dict:
    """Run user code against tests (via runner.py), returning a result dict."""
    with tempfile.TemporaryDirectory(prefix="algo_monster_") as tmp:
        solution = Path(tmp) / "solution.py"
        solution.write_text(code, encoding="utf-8")
        command = [sys.executable, str(RUNNER), "--algorithm-dir", str(ALGORITHMS_DIR / algo_id), "--solution", str(solution)]
        if test_index is not None:
            command.extend(["--test-index", str(test_index)])

        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False)
        except subprocess.TimeoutExpired:
            return {"ok": False, "summary": {"passed": 0, "failed": 1, "total": 1}, "results": [{"name": "Timeout", "passed": False, "error": f"Execution exceeded {TIMEOUT_SECONDS} seconds.", "stdout": ""}]}

    if completed.returncode != 0 and not completed.stdout:
        return {"ok": False, "summary": {"passed": 0, "failed": 1, "total": 1}, "results": [{"name": "Runner error", "passed": False, "error": completed.stderr.strip() or "Unknown runner error.", "stdout": ""}]}

    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "summary": {"passed": 0, "failed": 1, "total": 1}, "results": [{"name": "Invalid runner output", "passed": False, "error": completed.stdout + completed.stderr, "stdout": ""}]}
