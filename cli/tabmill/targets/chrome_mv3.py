"""chrome-mv3 target (D-040): Chrome Manifest V3 extensions built with WXT. Data in
`targets/chrome_mv3/target.yaml`; this wraps what used to be spread over `extension`,
`generate`, `listing` and `lint`, unchanged in behaviour."""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from .. import surfaces
from ..config import TOOL_DIR

DATA_FILE = "targets/chrome_mv3/target.yaml"


class Limits(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: int
    summary: int


class StoreImages(BaseModel):
    model_config = ConfigDict(extra="forbid")
    icon: tuple[int, int]
    promo: tuple[int, int]
    screenshots: list[tuple[int, int]]
    screenshot_count: tuple[int, int]


class Build(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dir: str
    dev_dir: str
    package_make_target: str


class Templates(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dir: str
    shared: str
    action_without_popup: list[str]


class Data(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    limits: Limits
    store_images: StoreImages
    build: Build
    templates: Templates


@cache
def data() -> Data:
    return Data.model_validate(yaml.safe_load((TOOL_DIR / DATA_FILE).read_text()))


class ChromeMV3:
    @property
    def id(self) -> str:
        return data().id

    @property
    def limits(self) -> Limits:
        return data().limits

    @property
    def store_images(self) -> StoreImages:
        return data().store_images

    @property
    def build(self) -> Build:
        return data().build

    @property
    def templates(self) -> tuple[str, ...]:
        """Surface templates this target can name (`surfaces` says which are built)."""
        return surfaces.NAMES

    def templates_dir(self, tool_dir: Path) -> Path:
        return tool_dir / data().templates.dir

    @property
    def shared_template(self) -> str:
        return data().templates.shared

    def manifest(self, ext: dict[str, Any]) -> dict[str, Any]:
        """Manifest fields tabmill owns; WXT adds the rest (ADR-0004)."""
        manifest: dict[str, Any] = {
            "name": ext["name"],
            "description": ext["summary"],
            "version": str(ext["version"]),
            "permissions": [p["name"] for p in ext["permissions"]],
        }
        for key in ("optional_permissions", "host_permissions"):
            if ext.get(key):
                manifest[key] = [p["name"] for p in ext[key]]
        if ext.get("template") in data().templates.action_without_popup:
            # No popup → WXT emits no `action`; the toolbar button must exist to open the panel.
            manifest["action"] = {"default_title": ext["name"]}
        return manifest

    def built_dir(self, workspace: Path, slug: str) -> Path:
        return workspace / "extensions" / slug / data().build.dir
