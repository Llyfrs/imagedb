from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml

# Defaults can be overridden via the interactive init command.
DEFAULT_VISION_MODEL = "google/gemini-2.0-flash-lite-001"


def get_config_path() -> Path:
    """
    Return the path to the YAML config file, honoring XDG base dir.
    """
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    config_dir = base / "imagedb"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.yaml"


def load_config() -> Dict[str, Any]:
    """
    Load configuration from disk.
    Raises FileNotFoundError if config is missing.
    """
    config_path = get_config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found at {config_path}. Run `imagedb init`.")

    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if "api_key" not in data or not data["api_key"]:
        raise ValueError("Config missing 'api_key'. Run `imagedb init`.")

    if "vision_model" not in data or not data["vision_model"]:
        data["vision_model"] = DEFAULT_VISION_MODEL

    return data


def save_config(api_key: str, vision_model: str | None = None) -> Path:
    """
    Persist configuration to disk. Returns the path written.
    """
    config_path = get_config_path()
    vision = vision_model or DEFAULT_VISION_MODEL
    payload = {
        "api_key": api_key,
        "vision_model": vision,
    }
    with config_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f)
    return config_path

