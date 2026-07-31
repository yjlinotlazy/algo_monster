#!/usr/bin/env python3
"""Local web server for Algo Monster — serves the frontend, exposes APIs."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from algorithm_handler import (
    algorithm_ids,
    load_progress,
    read_algorithm,
    read_solution,
    run_tests,
    safe_algorithm_id,
    save_progress,
    save_solution,
    validate_config_algo,
)
from mle_handler import (
    attach_mle_progress,
    find_question,
    grade_answer,
    load_mle_categories,
    load_question_graded,
)

# Import utility functions needed by handlers or directly used in server logic where cleaner
from utils import (  # for direct usage if needed elsewhere
    ALGORITHMS_DIR,
    CONFIG_DIR,
    MLE_DIR,
    MODEL_CONFIGS,
    PROGRESS_MLE_PATH,
    STATIC_DIR,
    load_json,
    write_json,
)


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
            if parsed.path == "/health":
                self.send_json({"ok": True, "status": "healthy"})
                return
            if parsed.path.startswith("/api/"):
                self.handle_api_get(parsed.path)
            else:
                self.route_index(parsed.path)
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
        # ── Algorithm endpoints ──
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

        # Algorithm save solution
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

        # Algorithm progress
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

        # MLE progress update
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
        from datetime import datetime, timezone

        # MLE grading
        if path == "/api/mle/grade":
            body = self.read_body()
            question_id = body.get("question_id") or ""
            answer = body.get("answer", "")
            model_type = body.get("model_type", "ollama")
            if not isinstance(question_id, str) or not isinstance(answer, str):
                self.send_error_json(
                    HTTPStatus.BAD_REQUEST, "Expected question_id and answer."
                )
                return
            q = find_question(load_mle_categories(), question_id)
            if not q:
                self.send_error_json(HTTPStatus.NOT_FOUND, "Question not found.")
                return

            result = grade_answer(
                question_id, q["question"], answer, model_type=model_type
            )
            if result.get("ok") and isinstance(result.get("score"), int):
                prog_progress = load_progress()
                mle = prog_progress.setdefault("mle", {})
                entry = mle.get(
                    question_id,
                    {"status": "to learn", "score": None, "graded_at": None},
                )
                entry["score"] = result["score"]
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

        # MLE graded answers save
        if path == "/api/mle/graded/save":
            body = self.read_body()
            question_id = body.get("question_id", "") or ""
            user_answer = body.get("user_answer", "") or ""
            score = body.get("score")
            llm_feedback = body.get("llm_feedback", "") or ""

            validate_config_algo()  # ensure dirs exist
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
            self.send_json({**graded_data[question_id], "ok": True})
            return

        # Run tests (Algorithm)
        if path == "/api/run":
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
                if result.get("ok"):
                    save_solution(algo_id, code)
                progress[algo_id] = current
                save_progress(progress)
            self.send_json(result)
            return

        self.send_error_json(HTTPStatus.NOT_FOUND, "Unknown endpoint.")

    def route_index(self, path: str) -> None:
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

    validate_config_algo()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Algo Monster running at http://{args.host}:{args.port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Algo Monster.")


if __name__ == "__main__":
    main()
