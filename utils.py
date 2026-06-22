#!/usr/bin/env python3
"""Shared utilities for Algo Monster and MLE Monster."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALGORITHMS_DIR = ROOT / "algorithms"
MLE_DIR = ROOT / "mle"
STATIC_DIR = ROOT / "web"
RUNNER = ROOT / "runner.py"
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "algo_monster"
SOLUTIONS_DIR = CONFIG_DIR / "solutions"
PROGRESS_PATH = CONFIG_DIR / "progress.json"
PROGRESS_MLE_PATH = CONFIG_DIR / "mle"
TIMEOUT_SECONDS = 3
MLE_TIMEOUT_SECONDS = int(os.environ.get("MLE_LLM_TIMEOUT", "180"))

DEFAULT_CONFIGS = {
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key": "dummy",
        "model": "qwen-large2",
    },
    "gpt": {
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-placeholder",
        "model": "gpt-4o-mini",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "sk-placeholder",
        "model": "deepseek-chat",
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "api_key": "sk-placeholder",
        "model": "gemini-3.5-flash",
    },
}


def _load_llm_config() -> dict[str, dict]:
    """Load LLM configs from env vars or config/llm.json file."""
    configs = {k: dict(v) for k, v in DEFAULT_CONFIGS.items()}

    llm_config_path = Path(__file__).resolve().parent / "config" / "llm.json"
    if llm_config_path.exists():
        try:
            local_cfg = json.loads(llm_config_path.read_text())
            if isinstance(local_cfg, dict):
                for key in ["ollama", "gpt", "deepseek"]:
                    if key in local_cfg and isinstance(local_cfg[key], dict):
                        configs[key].update(local_cfg[key])
        except json.JSONDecodeError:
            pass

    ollama_base = os.environ.get("OLLAMA_BASE_URL") or DEFAULT_CONFIGS["ollama"]["base_url"]
    ollama_key = os.environ.get("OLLAMA_API_KEY") or DEFAULT_CONFIGS["ollama"]["api_key"]
    ollama_model = os.environ.get("OLLAMA_MODEL") or DEFAULT_CONFIGS["ollama"]["model"]

    gpt_base = os.environ.get("GPT_BASE_URL") or DEFAULT_CONFIGS["gpt"]["base_url"]
    gpt_key = os.environ.get("GPT_API_KEY") or os.environ.get("OPENAI_API_KEY") or DEFAULT_CONFIGS["gpt"]["api_key"]
    gpt_model = os.environ.get("GPT_MODEL") or DEFAULT_CONFIGS["gpt"]["model"]

    deepseek_base = os.environ.get("DEEPSEEK_BASE_URL") or DEFAULT_CONFIGS["deepseek"]["base_url"]
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY") or DEFAULT_CONFIGS["deepseek"]["api_key"]
    deepseek_model = os.environ.get("DEEPSEEK_MODEL") or DEFAULT_CONFIGS["deepseek"]["model"]

    google_base = os.environ.get("GOOGLE_BASE_URL") or DEFAULT_CONFIGS["google"]["base_url"]
    google_key = os.environ.get("GOOGLE_API_KEY") or DEFAULT_CONFIGS["google"]["api_key"]
    google_model = os.environ.get("GOOGLE_MODEL") or DEFAULT_CONFIGS["google"]["model"]

    configs.update({
        "ollama": {"base_url": ollama_base, "api_key": ollama_key, "model": ollama_model},
        "gpt": {"base_url": gpt_base, "api_key": gpt_key, "model": gpt_model},
        "deepseek": {"base_url": deepseek_base, "api_key": deepseek_key, "model": deepseek_model},
        "google": {"base_url": google_base, "api_key": google_key, "model": google_model},
    })

    return configs


MODEL_CONFIGS = _load_llm_config()


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
