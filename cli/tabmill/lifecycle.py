"""Where each extension stands and the one next command (`tabmill status`, D-034, D-040)."""

from __future__ import annotations

from typing import Any

from . import catalog
from .listing import RELEASES_DIR

LIVE = "—"
# D-040. Ideas before a recipe exists are read from ideas/<id>/ (v2.B on).
STAGES = (
    "idea",
    "shaped",
    "evidenced",
    "verdict",
    "approved",
    "bootstrapped",
    "checked",
    "shipped",
    "published",
    "maintained",
)


def stage(row: catalog.Row, reg: dict[str, Any], approved: bool, released: bool) -> str:
    """Lifecycle stage of a recipe-backed extension; `invalid` / `orphan` pass through.
    `approved` = portfolio.yaml has an approval (or `migrated`) for it."""
    if row.status in ("invalid", "orphan"):
        return row.status
    if row.status == "recipe":
        return "approved" if approved else "shaped"
    if reg.get("published_state") == "PUBLISHED":
        # submitted_version is only set by an API publish = an update after the manual first one.
        return "maintained" if reg.get("submitted_version") else "published"
    if released or reg.get("store_id"):
        return "shipped"
    if reg.get("checked_version") and str(reg["checked_version"]) == row.version:
        return "checked"
    return "bootstrapped"


def store_state(reg: dict[str, Any]) -> str:
    """One phrase for the store side of a registry.json row."""
    if not reg.get("store_id"):
        return "not in the store"
    if reg.get("published_state") == "PUBLISHED":
        return "published"
    review = str(reg.get("review_state") or "").lower().replace("_", " ")
    return review or "in the store, state not fetched"


def next_step(row: catalog.Row, reg: dict[str, Any], released: bool) -> str:
    """What the operator does next for this extension. `reg` is its registry.json row;
    `released` = the upload folder for the recipe's version exists."""
    slug = row.slug
    recipe = f"recipes/{slug}/extension.yaml"
    if row.status == "invalid":
        return f"fix {recipe}"
    if row.status == "orphan":
        return f"restore recipes/{slug}/ or remove it from registry.json"
    if row.status == "recipe":
        if any(f in row.placeholders for f in catalog.MANIFEST_FIELDS):
            return f"fill ‹FILL› in {recipe}, then `tabmill bootstrap {slug}`"
        return f"tabmill bootstrap {slug}"
    if row.status == "generated":
        return f"tabmill try {slug}"
    if not reg.get("store_id"):
        if row.placeholders:
            return f"fill {', '.join(row.placeholders)} in {recipe}"
        if released:
            return (
                f"upload {RELEASES_DIR}/{slug}-{row.version}/ in the Developer Dashboard, "
                "then set store_id in registry.json"
            )
        return f"tabmill ship {slug}"
    if reg.get("taken_down") or reg.get("warned"):
        return "policy problem — open the Developer Dashboard"
    if reg.get("published_state") != "PUBLISHED":
        return f"tabmill status {slug} --refresh"
    submitted = reg.get("submitted_version")
    if submitted and str(submitted) != row.version:
        return f"tabmill publish {slug}"
    return LIVE
