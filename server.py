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
import urllib.error
import urllib.request
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
PROGRESS_MLE_PATH = CONFIG_DIR / "mle"
TIMEOUT_SECONDS = 3
MLE_TIMEOUT_SECONDS = int(os.environ.get("MLE_LLM_TIMEOUT", "180"))
MLE_DIR = ROOT / "mle"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "sk-placeholder")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1")


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
        expected_str = (
            json.dumps(expected) if not isinstance(expected, str) else expected
        )
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


# ── MLE Grading ─────────────────────────────────────────────


def grade_answer(question_id: str, question_text: str, user_answer: str) -> dict:
    """Forward the question + user answer to the configured LLM and parse score/feedback."""
    system_prompt = (
        "You are a grading assistant for ML interview questions. "
        "Grade the candidate's answer on a scale of 1-5: "
        "1=knows nothing, 2=partial understanding, 3=solid with gaps, "
        "4=strong but missing detail, 5=excellent and comprehensive.\n"
        "Respond ONLY with valid JSON of this shape: "
        '{"score": <int 1-5>, "feedback": "<text>"}.'
    )
    body = json.dumps(
        {
            "model": os.environ.get("OLLAMA_MODEL", "qwen-large2"),
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Question: {question_text}\n\n"
                        f"Candidate's answer:\n{user_answer}"
                    ),
                },
            ],
        },
    ).encode("utf-8")
    req = urllib.request.Request(
        OPENAI_BASE_URL.rstrip("/") + "/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=MLE_TIMEOUT_SECONDS) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "error": f"LLM request failed: HTTP {exc.code} {detail}"}
    except (urllib.error.URLError, OSError) as exc:
        return {"ok": False, "error": f"LLM unavailable: {exc}"}
    except (json.JSONDecodeError, KeyError, TypeError):
        return {"ok": False, "error": "Unexpected LLM response format."}

    content = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        cleaned = content.strip()
        for fence in ("```json\n", "```\n", "```"):
            if cleaned.startswith(fence):
                cleaned = cleaned[len(fence) :]
        try:
            end_brace = cleaned.rfind("}")
            parsed = json.loads(cleaned[: end_brace + 1])
        except json.JSONDecodeError:
            return {"ok": False, "error": "LLM did not return valid score/feedback."}

    score = (
        int(parsed.get("score", 0))
        if isinstance(parsed.get("score"), (int, float))
        else 0
    )
    feedback = str(parsed.get("feedback", "")) if parsed else ""
    return {"ok": True, "score": max(1, min(score, 5)), "feedback": feedback}


def load_mle_categories() -> dict[str, list[dict]]:
    """Load bundled MLE questions from per-category files under mle/."""
    CATEGORIES = {
        "ml_fundamentals.json": "ML fundamentals",
        "deep_learning.json": "Deep learning",
        "llm_ai.json": "LLM / AI",
        "metrics_evaluation.json": "Metrics / Evaluation",
        "data.json": "Data",
        "productionization.json": "Productionization",
        "experimentation.json": "Experimentation",
    }
    categories: dict[str, list[dict]] = {}
    if not MLE_DIR.exists():
        return categories
    for fname, category in CATEGORIES.items():
        path = MLE_DIR / fname
        questions = load_json(path, [])
        if not isinstance(questions, list):
            continue
        valid_items: list[dict] = []
        for item in questions:
            if isinstance(item, dict):
                valid_items.append({"category": category, **item})
        categories[category] = valid_items
    return categories


def attach_mle_progress(
    categories: dict[str, list[dict]], progress: dict | None = None
) -> dict[str, list[dict]]:
    """Return category-keyed MLE questions with per-question progress attached."""
    groups: dict[str, list[dict]] = {}
    mle_progress = progress or {}
    for category, questions in categories.items():
        groups[category] = []
        for q in questions:
            question_id = q.get("id")
            if not isinstance(question_id, str):
                continue
            item = dict(q)
            item["progress"] = mle_progress.get(question_id, {})
            groups[category].append(item)
    return groups


def find_question(categories: dict[str, list[dict]], question_id: str) -> dict | None:
    """Return the matching question or None."""
    for questions in categories.values():
        for q in questions:
            if q.get("id") == question_id:
                return q
    return None


def load_question_graded(question_id: str) -> dict | None:
    """Load a previously saved graded answer for *question_id*."""
    print("looking for", question_id)
    if not question_id:
        return None
    graded_dir = PROGRESS_MLE_PATH
    if not graded_dir.exists():
        return None
    graded_file = PROGRESS_MLE_PATH / f"{question_id}.json"
    data = load_json(graded_file, {})
    if not isinstance(data, dict):
        return None
    entry = data.get(question_id)
    if entry and isinstance(entry, dict):
        return entry
    # Fallback: scan for a matching key (handles old storage format)
    for k, v in data.items():
        if k == question_id and isinstance(v, dict):
            return v
    return None


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

        # ── MLE endpoints ──
        if path == "/api/mle/questions":
            progress = load_progress().get("mle", {})
            categories = attach_mle_progress(load_mle_categories(), progress)
            self.send_json({"categories": categories, "questions": categories})
            return

        if path.startswith("/api/mle/questions/"):
            question_id = unquote(path.removeprefix("/api/mle/questions/"))
            q = find_question(load_mle_categories(), question_id)
            if not q:
                self.send_error_json(HTTPStatus.NOT_FOUND, "Question not found.")
                return
            progress = load_progress().get("mle", {}).get(question_id, {})
            graded = load_question_graded(question_id)
            self.send_json({**q, "progress": progress, "graded": graded})
            return

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

        # ── MLE progress update ──
        if path.startswith("/api/mle/progress/"):
            question_id = unquote(path.removeprefix("/api/mle/progress/"))
            if not find_question(load_mle_categories(), question_id):
                self.send_error_json(HTTPStatus.NOT_FOUND, "Question not found.")
                return
            status = body.get("status")
            if status not in ("to learn", "learning", "learned"):
                self.send_error_json(HTTPStatus.BAD_REQUEST, "Invalid status.")
                return
            progress = load_progress()
            mle = progress.setdefault("mle", {})
            entry = mle.get(
                question_id, {"status": "to learn", "score": None, "graded_at": None}
            )
            entry["status"] = status
            if "score" in body and isinstance(body.get("score"), (int, float)):
                score_val = int(body.get("score") or 0)
                entry["score"] = score_val
                if int(score_val) >= 4 and status not in ("to learn",):
                    entry["status"] = "learned"
            elif status == "to learn" and body.get("reset", False):
                entry["score"] = None
                entry["graded_at"] = None
            mle[question_id] = entry
            progress["mle"] = mle
            save_progress(progress)
            self.send_json({"ok": True, "progress": entry})
            return

        self.send_error_json(HTTPStatus.NOT_FOUND, "Unknown endpoint.")

    def handle_api_post(self, path: str) -> None:
        # ── MLE grading ──
        if path == "/api/mle/grade":
            body = self.read_body()
            question_id = body.get("question_id") or ""
            answer = body.get("answer", "")
            if not isinstance(question_id, str) or not isinstance(answer, str):
                self.send_error_json(
                    HTTPStatus.BAD_REQUEST, "Expected question_id and answer."
                )
                return
            q = find_question(load_mle_categories(), question_id)
            if not q:
                self.send_error_json(HTTPStatus.NOT_FOUND, "Question not found.")
                return
            result = grade_answer(question_id, q["question"], answer)
            # Persist progress on successful grading
            if result.get("ok") and isinstance(result.get("score"), int):
                prog_progress = load_progress()
                mle = prog_progress.setdefault("mle", {})
                entry = mle.get(
                    question_id,
                    {"status": "to learn", "score": None, "graded_at": None},
                )
                entry["score"] = result["score"]
                from datetime import datetime, timezone

                entry["graded_at"] = datetime.now(timezone.utc).isoformat()
                if result["score"] >= 4:
                    entry["status"] = "learned"
                else:
                    entry["status"] = "learning"
                mle[question_id] = entry
                prog_progress["mle"] = mle
                save_progress(prog_progress)
                result["progress"] = entry
            self.send_json(result)
            return
        # ── MLE graded answers save ──
        if path == "/api/mle/graded/save":
            body = self.read_body()
            question_id = body.get("question_id", "") or ""
            user_answer = body.get("user_answer", "") or ""
            score = body.get("score")
            llm_feedback = body.get("llm_feedback", "") or ""
            from datetime import datetime, timezone

            ensure_config()
            os.makedirs(PROGRESS_MLE_PATH, exist_ok=True)
            graded_file = PROGRESS_MLE_PATH / f"{question_id}.json"
            graded_data = load_json(graded_file, {})
            if not isinstance(graded_data, dict):
                graded_data = {}
            graded_data[question_id] = {
                "user_answer": user_answer,
                "score": score,
                "llm_feedback": llm_feedback,
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }
            write_json(graded_file, graded_data)
            self.send_json({"ok": True})
            return

        elif path == "/api/run":
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
            return

        self.send_error_json(HTTPStatus.NOT_FOUND, "Unknown endpoint.")

    def serve_static(self, path: str) -> None:
        # Route /algo and /mle to their product directories.
        if path in ("/algo", "/algo/"):
            path = "/algo_monster/index.html"
        elif path in ("/mle", "/mle/"):
            path = "/mle_monster/index.html"

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
