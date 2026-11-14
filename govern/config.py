"""Configuration loading.

This is the only module permitted to know threshold values (see SPEC 3.11 and
AGENTS.md). Everything else must read them from here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, fields
from pathlib import Path

DEFAULT_PATH = Path("config") / "config.json"
APP_VERSION_FILE = "app_version.txt"


class ConfigError(Exception):
    """Raised when the config file is missing, malformed or incomplete."""


@dataclass(frozen=True)
class Config:
    app_version: str
    model_id: str
    temperature: float
    max_tokens: int
    seed: int
    tau_review_ms: int
    mech_dwell_ms: int
    pair_tolerance: float
    impact_recall_min: float
    impact_precision_min: float
    n_participants: int
    block_size: int
    retention_days: int
    conditions: tuple[str, ...]
    card_item_max_chars: int
    task_time_limit_s: int
    test_timeout_s: int


def _read_app_version(fallback: str, project_root: Path) -> str:
    """Prefer app_version.txt (written by the release script) over config."""
    marker = project_root / APP_VERSION_FILE
    if marker.is_file():
        value = marker.read_text(encoding="utf-8").strip()
        if value:
            return value
    return fallback


def load(path: str | Path = DEFAULT_PATH) -> Config:
    """Load and validate the configuration file."""
    p = Path(path)
    if not p.is_file():
        raise ConfigError(f"config not found: {p}")

    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"config is not valid JSON: {p}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"config must be a JSON object: {p}")

    known = {f.name for f in fields(Config)}
    unknown = sorted(set(raw) - known)
    if unknown:
        raise ConfigError(f"unknown config keys: {', '.join(unknown)}")
    missing = sorted(known - set(raw))
    if missing:
        raise ConfigError(f"missing config keys: {', '.join(missing)}")

    raw["conditions"] = tuple(raw["conditions"])
    raw["app_version"] = _read_app_version(raw["app_version"], p.parent.parent)
    return Config(**raw)
