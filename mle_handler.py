#!/usr/bin/env python3
"""MLE Monster specific logic: loading MLE questions, grading, and managing MLE progress."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from utils import MLE_DIR, PROGRESS_MLE_PATH, _load_llm_config, load_json

MLE_TIMEOUT_SECONDS = 180


def load_mle_categories() -> dict[str, list[dict]]:
    """Load bundled MLE questions from per-category files under mle/."""
    CATEGORIES = {
        "ml_fundamentals.json": "ML fundamentals",
        "deep_learning.json": "Deep learning",
        "llm_ai.json": "LLM / AI",
        "agentic_ai.json": "Agentic AI",
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
    if not question_id:
        return None
    graded_file = PROGRESS_MLE_PATH / f"{question_id}.json"
    data = load_json(graded_file, {})
    if not isinstance(data, dict):
        return None
    entry = data.get(question_id)
    if entry and isinstance(entry, dict):
        return entry
    for k, v in data.items():
        if k == question_id and isinstance(v, dict):
            return v
    return None


def grade_answer(
    question_id: str, question_text: str, user_answer: str, model_type: str = "ollama"
) -> dict:
    """Forward the question + user answer to the configured LLM and parse score/feedback."""
    configs = _load_llm_config()
    cfg = configs.get(model_type, configs["ollama"])
    print("Calling", cfg)
    base_url = cfg["base_url"]
    api_key = cfg["api_key"]
    model_name = cfg["model"]
    system_prompt = (
        "You are a grading assistant for ML interview questions. "
        "Grade the candidate's answer on a scale of 1-5: "
        "1=knows nothing, 2=partial understanding, 3=solid with gaps, "
        "4=strong but missing detail, 5=excellent and comprehensive.\n"
        'Respond ONLY with valid JSON of this shape: {"score": <int 1-5>, "feedback": "<text>"}.'
    )
    body = json.dumps(
        {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Question: {question_text}\n\nCandidate's answer:\n{user_answer}",
                },
            ],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
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
    except json.JSONDecodeError:
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
