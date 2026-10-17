"""Target adapters (D-040). A target is where an extension ships (store + manifest format).
Only `chrome-mv3` exists; WordPress plugins (v4) add the second. Callers ask `get(id)` or
`for_recipe(ext)` instead of hard-coding Chrome paths, limits or manifest shape."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from .chrome_mv3 import ChromeMV3, Limits, StoreImages

DEFAULT = "chrome-mv3"


class Target(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def limits(self) -> Limits: ...

    @property
    def store_images(self) -> StoreImages: ...

    @property
    def templates(self) -> tuple[str, ...]: ...

    @property
    def shared_template(self) -> str: ...

    def templates_dir(self, tool_dir: Path) -> Path: ...

    def manifest(self, ext: dict[str, Any]) -> dict[str, Any]: ...

    def built_dir(self, workspace: Path, slug: str) -> Path: ...


TARGETS: dict[str, Target] = {DEFAULT: ChromeMV3()}


class TargetError(Exception):
    """Unknown target id."""


def get(target_id: str = DEFAULT) -> Target:
    try:
        return TARGETS[target_id]
    except KeyError as e:
        raise TargetError(f"unknown target {target_id!r} (known: {', '.join(TARGETS)})") from e


def for_recipe(ext: dict[str, Any]) -> Target:
    return get(str(ext.get("target") or DEFAULT))
