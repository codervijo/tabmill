"""WORKSPACE_DIR/registry.json — per-extension version, store ID, status."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REGISTRY_FILE = "registry.json"


def read(workspace: Path) -> dict[str, Any]:
    path = workspace / REGISTRY_FILE
    if not path.exists():
        return {"extensions": {}}
    data: dict[str, Any] = json.loads(path.read_text())
    data.setdefault("extensions", {})
    return data


def slugs(workspace: Path) -> list[str]:
    return sorted(read(workspace)["extensions"])


DEFAULT_SLOT_LIMIT = 2  # new publishers (developer.chrome.com/docs/webstore/publish), D-026


def slots(workspace: Path) -> dict[str, int]:
    """used = items the store reports PUBLISHED; limit from registry (default 2)."""
    data = read(workspace)
    used = sum(1 for r in data["extensions"].values() if r.get("published_state") == "PUBLISHED")
    limit = int(data.get("slots", {}).get("limit", DEFAULT_SLOT_LIMIT))
    return {"used": used, "limit": limit}


def save_slots(workspace: Path) -> dict[str, int]:
    data = read(workspace)
    current = slots(workspace)
    if data.get("slots") != current:
        data["slots"] = current
        (workspace / REGISTRY_FILE).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return current


def upsert(workspace: Path, slug: str, fields: dict[str, Any]) -> bool:
    """Merge fields into the slug's row. Returns True if the file changed."""
    data = read(workspace)
    row = data["extensions"].get(slug, {"store_id": None})
    merged = {**row, **fields}
    if data["extensions"].get(slug) == merged:
        return False
    data["extensions"][slug] = merged
    (workspace / REGISTRY_FILE).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return True
