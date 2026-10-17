"""portfolio.yaml (tool repo, D-040): store slot limit and per-extension approval / slot
reservation — the slow-changing, tabmill-side record. Store-side state (store_id, review and
published state, checked version) stays in the workspace's registry.json."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from . import catalog, registry

PORTFOLIO_FILE = "portfolio.yaml"
HEADER = (
    "# Tabmill portfolio (D-040): store slots + approval per extension.\n"
    "# Written by `tabmill doctor --fix` and `tabmill approve`; store state lives in the\n"
    "# workspace registry.json.\n"
)


class PortfolioError(Exception):
    """portfolio.yaml unreadable or invalid; message names the fix."""


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # migrated = recipe predates the v2 approve gate (grandfathered, no verdict);
    # proposed = written by the idea stage (`new --apply`), not yet approved.
    approval: Literal["migrated", "proposed", "approved", "override"]
    idea_id: str = ""
    recipe_revision: int = Field(default=1, ge=1)
    frozen_sha256: str = ""
    approved_at: str = ""
    slot: Literal["none", "reserved"] = "none"
    override_reason: str = ""


class Slots(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=registry.DEFAULT_SLOT_LIMIT, ge=1)


class Portfolio(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slots: Slots = Slots()
    items: dict[str, Item] = {}


APPROVED = ("migrated", "approved", "override")
# Fields tabmill itself rewrites during a release stay outside the freeze (D-040).
# cta_url / store_category are the ‹FILL› decisions completed after approve.
UNFROZEN = (
    "version",
    "changelog",
    "landing_page_url",
    "recipe_revision",
    "cta_url",
    "store_category",
)


def frozen_sha256(ext: dict[str, Any]) -> str:
    """Hash of the recipe's frozen fields (parsed values, so comment edits don't count)."""
    frozen = {k: v for k, v in ext.items() if k not in UNFROZEN}
    blob = json.dumps(frozen, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def is_approved(tool_dir: Path, slug: str) -> bool:
    item = read(tool_dir).items.get(slug)
    return item is not None and item.approval in APPROVED


def drift(tool_dir: Path, slug: str, ext: dict[str, Any]) -> str | None:
    """Why a frozen (approved) recipe may not be built as it is now; None = fine."""
    item = read(tool_dir).items.get(slug)
    if item is None or item.approval not in ("approved", "override"):
        return None
    revision = int(ext.get("recipe_revision", 1))
    if frozen_sha256(ext) == item.frozen_sha256 and revision == item.recipe_revision:
        return None
    how = f"tabmill approve {item.idea_id}" if item.idea_id else "tabmill approve"
    if revision == item.recipe_revision:
        return (
            f"frozen fields of recipes/{slug} changed since approve — bump "
            f"recipe_revision to {revision + 1} and re-run `{how}`"
        )
    return f"recipe_revision {revision} isn't approved (approved: {item.recipe_revision}) — `{how}`"


def path(tool_dir: Path) -> Path:
    return tool_dir / PORTFOLIO_FILE


def read(tool_dir: Path) -> Portfolio:
    p = path(tool_dir)
    if not p.exists():
        return Portfolio()
    try:
        return Portfolio.model_validate(yaml.safe_load(p.read_text()) or {})
    except (yaml.YAMLError, ValidationError) as e:
        raise PortfolioError(f"{p}: invalid ({e})") from e


def write(tool_dir: Path, data: Portfolio) -> bool:
    """True if the file changed."""
    body = yaml.safe_dump(
        data.model_dump(mode="json", exclude_defaults=True), sort_keys=True, allow_unicode=True
    )
    text = HEADER + body
    p = path(tool_dir)
    if p.exists() and p.read_text() == text:
        return False
    p.write_text(text)
    return True


def seed(tool_dir: Path, workspace: Path | None) -> list[str]:
    """Add every recipe missing from portfolio.yaml as `migrated`. Returns the slugs added."""
    data = read(tool_dir)
    added = [s for s in catalog.recipe_slugs(tool_dir) if s not in data.items]
    for slug in added:
        data.items[slug] = Item(approval="migrated")
    if workspace is not None and workspace.exists() and not path(tool_dir).exists():
        data.slots.limit = registry.slots(workspace)["limit"]
    if added or not path(tool_dir).exists():
        write(tool_dir, data)
    return added


@dataclass
class SlotView:
    limit: int
    published: list[str] = field(default_factory=list)
    reserved: list[str] = field(default_factory=list)

    @property
    def free(self) -> int:
        return max(0, self.limit - len(self.published) - len(self.reserved))


def slots(tool_dir: Path, workspace: Path | None) -> SlotView:
    """Published (store says PUBLISHED) + reserved (approved, not yet published) vs the limit."""
    data = read(tool_dir)
    reg: dict[str, Any] = (
        registry.read(workspace)["extensions"] if workspace and workspace.exists() else {}
    )
    published = sorted(s for s, r in reg.items() if r.get("published_state") == "PUBLISHED")
    reserved = sorted(
        s for s, i in data.items.items() if i.slot == "reserved" and s not in published
    )
    return SlotView(data.slots.limit, published, reserved)
