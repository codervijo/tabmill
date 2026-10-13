"""The one next command per extension (`tabmill status`, D-034): recipe → store → live."""

from __future__ import annotations

from typing import Any

from . import catalog
from .listing import RELEASES_DIR

LIVE = "—"


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
            return f"fill ‹FILL› in {recipe}, then `tabmill new {slug}`"
        return f"tabmill new {slug}"
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
        return f"tabmill ship {slug} --publish"
    return LIVE
