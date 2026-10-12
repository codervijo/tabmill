"""Lamill's shared privacy policy (D-036): `privacy-policy.yaml` → lamill.io privacy.json.

One policy covers every extension. `coverage()` lists what a recipe does beyond it — the
release lint `privacy-coverage` fails on any of these.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

POLICY_FILE = "privacy-policy.yaml"
EXPORT_FILE = "src/content/privacy.json"


class PolicyError(Exception):
    pass


class Policy(BaseModel):
    """Mirror of lamill.io `privacySchema` (src/lib/privacy.ts)."""

    model_config = ConfigDict(extra="forbid")
    version: int
    updated: dt.date
    permissions: dict[str, str]

    @property
    def marker(self) -> str:
        """Text the live page must show, so an undeployed policy change is caught."""
        return f"Policy version {self.version}"


def load(tool_dir: Path) -> Policy:
    path = tool_dir / POLICY_FILE
    if not path.exists():
        raise PolicyError(f"{POLICY_FILE} missing in {tool_dir}")
    try:
        return Policy.model_validate(yaml.safe_load(path.read_text()))
    except (yaml.YAMLError, ValidationError) as e:
        raise PolicyError(f"{POLICY_FILE} invalid: {e}") from e


def coverage(ext: dict[str, Any], policy: Policy) -> list[str]:
    """Everything the extension does that the shared policy doesn't cover."""
    gaps = [
        f"permission `{p['name']}` isn't in {POLICY_FILE}"
        for key in ("permissions", "optional_permissions")
        for p in ext.get(key) or []
        if p["name"] not in policy.permissions
    ]
    if ext.get("host_permissions"):
        gaps.append("host permissions — the policy promises none")
    if ext.get("analytics"):
        gaps.append("analytics on — the policy promises none")
    if ext.get("remote_code"):
        gaps.append("remote code — the policy promises none")
    if ext.get("data_collected"):
        gaps.append("data_collected not empty — the policy promises nothing is collected")
    return gaps


def write(hub_repo: Path, policy: Policy) -> tuple[Path, bool]:
    """Write lamill.io privacy.json; returns (path, changed)."""
    path = hub_repo / EXPORT_FILE
    text = json.dumps(policy.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text() == text:
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path, True
