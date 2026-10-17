"""Resolve TOOL_DIR, WORKSPACE_DIR, and the builder path. WORKSPACE_DIR is never hardcoded."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .constants import CONFIG_FILE, DEFAULT_BUILDER, ENV_BUILDER, ENV_WORKSPACE

# cli/tabmill/config.py → repo root is two levels above the package dir.
TOOL_DIR = Path(__file__).resolve().parents[2]


class ConfigError(Exception):
    """Configuration missing or invalid; message names the fix."""


@dataclass(frozen=True)
class Config:
    tool_dir: Path
    workspace: Path
    builder: Path
    tool_repo: str
    hub_repo: Path
    ai_model: str = ""  # `claude -p --model`; empty = Claude Code's default


def _read_config_file(tool_dir: Path) -> dict[str, str]:
    path = tool_dir / CONFIG_FILE
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ConfigError(f"{path} is not valid JSON ({e}).") from e
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a JSON object.")
    return {k: str(v) for k, v in data.items()}


def _resolve(raw: str, base: Path) -> Path:
    p = Path(os.path.expanduser(raw))
    return (p if p.is_absolute() else base / p).resolve()


def load(tool_dir: Path = TOOL_DIR, *, require_workspace: bool = True) -> Config:
    """Env vars win over tabmill.config.json; relative paths resolve against TOOL_DIR."""
    file_cfg = _read_config_file(tool_dir)
    ws_raw = os.environ.get(ENV_WORKSPACE) or file_cfg.get("workspace")
    if not ws_raw:
        if require_workspace:
            raise ConfigError(
                f"No workspace configured. Set {ENV_WORKSPACE} or add "
                f'"workspace" to {tool_dir / CONFIG_FILE}, or run `tabmill settings init <dir>`.'
            )
        ws_raw = "."
    builder_raw = os.environ.get(ENV_BUILDER) or file_cfg.get("builder") or DEFAULT_BUILDER
    return Config(
        tool_dir=tool_dir,
        workspace=_resolve(ws_raw, tool_dir),
        builder=_resolve(builder_raw, tool_dir),
        tool_repo=file_cfg.get("tool_repo", ""),
        hub_repo=_resolve(file_cfg.get("hub_repo") or "~/work/projects/sites/lamill.io", tool_dir),
        ai_model=file_cfg.get("ai_model", ""),
    )
