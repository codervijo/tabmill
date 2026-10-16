"""Surface templates registry (`tabmill templates`, D-040). One place for template ids, what
each is for, and the permissions its own code needs. `stub` entries can be named by recipes and
template-fit checks but can't be generated yet."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Status = Literal["implemented", "stub"]
TARGET = "chrome-mv3"  # the only target until the v2.G adapter seam


@dataclass(frozen=True)
class Surface:
    name: str
    status: Status
    trigger: str  # toolbar | shortcut | context_menu | side_panel
    use_for: str
    permissions: tuple[tuple[str, str], ...] = ()  # (permission, justification) the code needs


SURFACES: dict[str, Surface] = {
    s.name: s
    for s in (
        Surface("popup", "implemented", "toolbar", "a small panel from the toolbar button"),
        Surface(
            "side-panel",
            "implemented",
            "toolbar",
            "results that stay open beside the page",
            (
                (
                    "sidePanel",
                    "Show results in Chrome's side panel, opened from the toolbar button.",
                ),
            ),
        ),
        Surface(
            "maps-overlay",
            "implemented",
            "toolbar",
            "drawing on top of Google Maps",
            (
                (
                    "scripting",
                    "Add the overlay to the current tab when the user clicks the toolbar button.",
                ),
            ),
        ),
        Surface(
            "page-overlay",
            "stub",
            "toolbar",
            "measuring or annotating on top of any page (not built yet)",
            (
                (
                    "scripting",
                    "Add the overlay to the current tab when the user clicks the toolbar button.",
                ),
            ),
        ),
    )
}
NAMES = tuple(SURFACES)
IMPLEMENTED = tuple(n for n, s in SURFACES.items() if s.status == "implemented")


def needed_permissions(template: str) -> tuple[str, ...]:
    surface = SURFACES.get(template)
    return tuple(p for p, _ in surface.permissions) if surface else ()


def permission_reason(template: str, permission: str) -> str:
    return dict(SURFACES[template].permissions)[permission]
