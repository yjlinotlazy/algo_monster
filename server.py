#!/usr/bin/env python3
"""Local web server for Algo Monster — serves the frontend, exposes APIs for
algorithms/solutions/progress, and runs user code against tests."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import subprocess
import sys
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
ALGORITHMS_DIR = ROOT / "algorithms"
STATIC_DIR = ROOT / "web"
RUNNER = ROOT / "runner.py"
CONFIG_DIR = (
    Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "algo_monster"
)
SOLUTIONS_DIR = CONFIG_DIR / "solutions"
PROGRESS_PATH = CONFIG_DIR / "progress.json"
TIMEOUT_SECONDS = 3


def ensure_config() -> None:
    """Create config/solutions directories and an empty progress.json if missing."""
    SOLUTIONS_DIR.mkdir(parents=True, exist_ok=True)
    if not PROGRESS_PATH.exists():
        PROGRESS_PATH.write_text("{}", encoding="utf-8")


def load_json(path: Path, default):
    """Load JSON from *path*, returning *default* on missing file or parse error."""
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json(path: Path, data) -> None:
    """Write *data* as indented JSON to *path*, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def algorithm_ids() -> set[str]:
    """Return the set of available algorithm directory names."""
    if not ALGORITHMS_DIR.exists():
        return set()
    return {
        path.name
        for path in ALGORITHMS_DIR.iterdir()
        if path.is_dir() and (path / "meta.json").exists()
    }


def safe_algorithm_id(raw_id: str) -> str:
    """Validate and URL-decode *raw_id*, raising KeyError if unknown."""
    algo_id = unquote(raw_id)
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
    ensure_config()
    progress = load_json(PROGRESS_PATH, {})
    return progress if isinstance(progress, dict) else {}


def save_progress(progress: dict) -> None:
    """Persist *progress* to disk."""
    ensure_config()
    write_json(PROGRESS_PATH, progress)


def run_tests(algo_id: str, code: str, test_index: int | None) -> dict:
    """Run user code against tests (via runner.py), returning a result dict."""
    with tempfile.TemporaryDirectory(prefix="algo_monster_") as tmp:
        solution = Path(tmp) / "solution.py"
        solution.write_text(code, encoding="utf-8")
        command = [
            sys.executable,
            str(RUNNER),
            "--algorithm-dir",
            str(ALGORITHMS_DIR / algo_id),
            "--solution",
            str(solution),
        ]
        if test_index is not None:
            command.extend(["--test-index", str(test_index)])

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "summary": {"passed": 0, "failed": 1, "total": 1},
                "results": [
                    {
                        "name": "Timeout",
                        "passed": False,
                        "error": f"Execution exceeded {TIMEOUT_SECONDS} seconds.",
                        "stdout": "",
                    }
                ],
            }

    if completed.returncode != 0 and not completed.stdout:
        return {
            "ok": False,
            "summary": {"passed": 0, "failed": 1, "total": 1},
            "results": [
                {
                    "name": "Runner error",
                    "passed": False,
                    "error": completed.stderr.strip() or "Unknown runner error.",
                    "stdout": "",
                }
            ],
        }

    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "summary": {"passed": 0, "failed": 1, "total": 1},
            "results": [
                {
                    "name": "Invalid runner output",
                    "passed": False,
                    "error": completed.stdout + completed.stderr,
                    "stdout": "",
                }
            ],
        }


class Handler(BaseHTTPRequestHandler):
    """HTTP request handler — serves static files and exposes /api/ endpoints."""

    server_version = "AlgoMonster/0.1"

    def log_message(self, format: str, *args) -> None:
        sys.stderr.write(
            "%s - - [%s] %s\n"
            % (self.client_address[0], self.log_date_time_string(), format % args)
        )

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/"):
                self.handle_api_get(parsed.path)
            else:
                self.serve_static(parsed.path)
        except Exception as exc:
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def do_PUT(self) -> None:
        try:
            self.handle_api_put(urlparse(self.path).path)
        except Exception as exc:
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def do_POST(self) -> None:
        try:
            self.handle_api_post(urlparse(self.path).path)
        except Exception as exc:
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def handle_api_get(self, path: str) -> None:
        if path == "/api/algorithms":
            progress = load_progress()
            items = []
            for algo_id in sorted(algorithm_ids()):
                meta = load_json(ALGORITHMS_DIR / algo_id / "meta.json", {})
                item = {
                    "id": algo_id,
                    "title": meta.get("title", algo_id),
                    "category": meta.get("category", ""),
                    "progress": progress.get(algo_id, {}),
                }
                items.append(item)
            self.send_json({"algorithms": items})
            return

        if path.startswith("/api/algorithms/"):
            try:
                algo_id = safe_algorithm_id(path.removeprefix("/api/algorithms/"))
            except KeyError:
                self.send_error_json(HTTPStatus.NOT_FOUND, "Unknown algorithm.")
                return
            payload = read_algorithm(algo_id)
            payload["solution"] = read_solution(algo_id)
            payload["progress"] = load_progress().get(algo_id, {})
            self.send_json(payload)
            return

        self.send_error_json(HTTPStatus.NOT_FOUND, "Unknown endpoint.")

    def handle_api_put(self, path: str) -> None:
        body = self.read_body()
        if path.startswith("/api/solutions/"):
            try:
                algo_id = safe_algorithm_id(path.removeprefix("/api/solutions/"))
            except KeyError:
                self.send_error_json(HTTPStatus.NOT_FOUND, "Unknown algorithm.")
                return
            code = body.get("code")
            if not isinstance(code, str):
                self.send_error_json(
                    HTTPStatus.BAD_REQUEST, "Expected string field: code."
                )
                return
            save_solution(algo_id, code)
            self.send_json({"ok": True})
            return

        if path.startswith("/api/progress/"):
            try:
                algo_id = safe_algorithm_id(path.removeprefix("/api/progress/"))
            except KeyError:
                self.send_error_json(HTTPStatus.NOT_FOUND, "Unknown algorithm.")
                return
            status = body.get("status")
            if status not in ("to learn", "learning", "learned"):
                self.send_error_json(HTTPStatus.BAD_REQUEST, "Invalid status.")
                return
            progress = load_progress()
            current = progress.get(algo_id, {})
            current["status"] = status
            progress[algo_id] = current
            save_progress(progress)
            self.send_json({"ok": True, "progress": current})
            return

        self.send_error_json(HTTPStatus.NOT_FOUND, "Unknown endpoint.")

    def handle_api_post(self, path: str) -> None:
        if path != "/api/run":
            self.send_error_json(HTTPStatus.NOT_FOUND, "Unknown endpoint.")
            return

        body = self.read_body()
        algo_id = body.get("algorithm_id")
        code = body.get("code")
        test_index = body.get("test_index")
        if not isinstance(algo_id, str) or not isinstance(code, str):
            self.send_error_json(
                HTTPStatus.BAD_REQUEST, "Expected algorithm_id and code."
            )
            return
        try:
            algo_id = safe_algorithm_id(algo_id)
        except KeyError:
            self.send_error_json(HTTPStatus.NOT_FOUND, "Unknown algorithm.")
            return
        if test_index is not None and not isinstance(test_index, int):
            self.send_error_json(
                HTTPStatus.BAD_REQUEST, "test_index must be an integer."
            )
            return

        result = run_tests(algo_id, code, test_index)
        if test_index is None:
            progress = load_progress()
            current = progress.get(algo_id, {})
            current["passing"] = bool(result.get("ok"))
            # Auto-save solution when all tests pass (run all)
            if result.get("ok"):
                save_solution(algo_id, code)
            progress[algo_id] = current
            save_progress(progress)
        self.send_json(result)

    def serve_static(self, path: str) -> None:
        if path == "/":
            file_path = STATIC_DIR / "index.html"
        else:
            clean = Path(unquote(path).lstrip("/"))
            file_path = (STATIC_DIR / clean).resolve()
            if (
                STATIC_DIR.resolve() not in file_path.parents
                and file_path != STATIC_DIR.resolve()
            ):
                self.send_error(HTTPStatus.FORBIDDEN)
                return

        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_type = (
            mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        )
        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON body.")
        if not isinstance(data, dict):
            raise ValueError("Expected JSON object.")
        return data

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_error_json(self, status: HTTPStatus, message: str) -> None:
        self.send_json({"ok": False, "error": message}, status)


def main() -> None:
    """Parse args, ensure config, start the ThreadingHTTPServer until interrupt."""
    parser = argparse.ArgumentParser(description="Run the Algo Monster local web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()

    ensure_config()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Algo Monster running at http://{args.host}:{args.port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Algo Monster.")


if __name__ == "__main__":
    main()
