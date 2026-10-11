"""`tabmill hub`: registry + recipes → lamill.io `src/content/extensions.json` (D-028).

The contract is lamill.io's zod schema (`src/lib/extensions.ts`, README § Extensions data
contract); `HubEntry` mirrors it so tabmill refuses to write anything lamill.io would drop.
tabmill writes only that one file in the lamill.io repo and never commits or deploys it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError, field_validator

from . import catalog, extension, generate, registry

HUB_FILE = "src/content/extensions.json"
DEFAULT_HUB_REPO = "~/work/projects/sites/lamill.io"
HUB_BASE = "https://lamill.io/extensions"
STORE_DETAIL = "https://chromewebstore.google.com/detail"
RESERVED_SLUGS = {"support"}


def privacy_url(slug: str) -> str:
    return f"{HUB_BASE}/{slug}/privacy"


SUPPORT_URL = f"{HUB_BASE}/support"


class Permission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    reason: str


class Change(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    notes: str


class HubEntry(BaseModel):
    """Mirror of lamill.io `extensionSchema` (zod), re-checked 2026-10-03 (store_url nullish);
    `unlisted` added 2026-10-11 (D-035) — lamill.io must accept it before `hub` runs."""

    model_config = ConfigDict(extra="forbid")
    slug: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str
    pitch: str
    store_url: HttpUrl | None = None  # null while not in the store → "In development"
    tool_page_url: HttpUrl
    permissions: list[Permission] = []
    data_collected: list[str] = []
    analytics: bool = False
    changelog: list[Change] = []
    # unlisted (D-035): page + privacy live, hidden from the hub index — CWS needs the privacy
    # URL live before review, so every exported entry not yet PUBLISHED is unlisted.
    status: Literal["draft", "unlisted", "published"] = "draft"

    @field_validator("slug")
    @classmethod
    def _not_reserved(cls, v: str) -> str:
        if v in RESERVED_SLUGS:
            raise ValueError("slug is reserved")
        return v


@dataclass
class Export:
    entries: list[dict[str, Any]] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)  # slug → reason


def _real_url(value: object) -> str | None:
    s = str(value or "").strip()
    return s if re.match(r"^https?://", s) and not extension.is_placeholder(s) else None


def build(tool_dir: Path, workspace: Path) -> Export:
    out = Export()
    rows = registry.read(workspace)["extensions"]
    for slug in catalog.recipe_slugs(tool_dir):
        ext = extension.load_file(generate.recipe_dir(tool_dir, slug) / generate.RECIPE_FILE)
        row = rows.get(slug, {})
        store_url = f"{STORE_DETAIL}/{row['store_id']}" if row.get("store_id") else None
        tool_page = _real_url(ext.get("landing_page_url"))
        if not tool_page:
            out.skipped[slug] = "no tool_page_url yet (set `landing_page_url` in its recipe)"
            continue
        perms = [
            {"name": p["name"], "reason": p["justification"]}
            for key in ("permissions", "optional_permissions", "host_permissions")
            for p in ext.get(key) or []
        ]
        entry = {
            "slug": slug,
            "name": ext["name"],
            "pitch": ext["summary"],
            "store_url": store_url,
            "tool_page_url": tool_page,
            "permissions": perms,
            "data_collected": list(ext.get("data_collected") or []),
            "analytics": bool(ext.get("analytics")),
            "changelog": list(ext.get("changelog") or []),
            "status": "published" if row.get("published_state") == "PUBLISHED" else "unlisted",
        }
        try:
            HubEntry.model_validate(entry)
        except ValidationError as e:
            out.skipped[slug] = f"fails the hub contract: {e.errors()[0]['msg']}"
            continue
        out.entries.append(entry)
    return out


def write(hub_repo: Path, export: Export) -> tuple[Path, bool]:
    """Write extensions.json; returns (path, changed)."""
    path = hub_repo / HUB_FILE
    text = json.dumps(export.entries, indent=2, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text() == text:
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path, True
