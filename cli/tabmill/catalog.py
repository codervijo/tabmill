"""All extensions in one view (`tabmill list`) and starter recipes (`tabmill create`)."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import extension, generate, registry
from .templates import render

RECIPE_TEMPLATE = "templates/recipe/extension.yaml.tmpl"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SLUG_MAX = 40
BUILT_MANIFEST = ".output/chrome-mv3/manifest.json"
# Manifest-facing fields: `new` / `build` refuse while these hold ‹FILL›.
MANIFEST_FIELDS = ("name", "summary", "single_purpose")
TEMPLATE_PERMISSION_REASONS = {
    "sidePanel": "Show results in Chrome's side panel, opened from the toolbar button.",
}


class CreateError(Exception):
    """`create` refused; message names why and the fix."""


@dataclass
class Row:
    slug: str
    status: str  # recipe | generated | built | orphan | invalid
    version: str = ""
    template: str = ""
    store_id: str | None = None
    placeholders: list[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def fill_fields(ext: dict[str, Any], prefix: str = "") -> list[str]:
    """Dotted paths of every value still holding the ‹FILL› marker."""
    found: list[str] = []
    for key, value in ext.items():
        path = f"{prefix}{key}"
        if isinstance(value, str) and extension.FILL_MARKER in value:
            found.append(path)
        elif isinstance(value, dict):
            found += fill_fields(value, f"{path}.")
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, str) and extension.FILL_MARKER in item:
                    found.append(f"{path}[{i}]")
                elif isinstance(item, dict):
                    found += fill_fields(item, f"{path}[{i}].")
    return found


def placeholders(ext: dict[str, Any]) -> list[str]:
    fields = fill_fields(ext)
    return fields + [f for f in extension.placeholder_fields(ext) if f not in fields]


def unfilled_manifest_fields(ext: dict[str, Any]) -> list[str]:
    return [f for f in MANIFEST_FIELDS if f in fill_fields(ext)]


def recipe_slugs(tool_dir: Path) -> list[str]:
    root = tool_dir / generate.RECIPES_DIR
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if (p / generate.RECIPE_FILE).exists())


def rows(tool_dir: Path, workspace: Path | None) -> list[Row]:
    reg = registry.read(workspace)["extensions"] if workspace and workspace.exists() else {}
    out: list[Row] = []
    for slug in sorted(set(recipe_slugs(tool_dir)) | set(reg)):
        entry: dict[str, Any] = reg.get(slug, {})
        row = Row(slug=slug, status="recipe", store_id=entry.get("store_id"))
        path = generate.recipe_dir(tool_dir, slug) / generate.RECIPE_FILE
        if not path.exists():
            row.status, row.version = "orphan", str(entry.get("version", ""))
            row.error = "registered in the workspace but no recipe in tabmill"
            out.append(row)
            continue
        try:
            ext = extension.load_file(path)
        except extension.ExtensionError as e:
            row.status, row.error = "invalid", str(e)
            out.append(row)
            continue
        row.version, row.template = str(ext.get("version", "")), str(ext.get("template", ""))
        row.placeholders = placeholders(ext)
        if slug in reg:
            built = (
                workspace is not None
                and (workspace / "extensions" / slug / BUILT_MANIFEST).exists()
            )
            row.status = "built" if built else "generated"
        out.append(row)
    return out


def implemented_templates(tool_dir: Path) -> list[str]:
    root = tool_dir / generate.EXT_TEMPLATES_DIR
    return [t for t in extension.TEMPLATES if (root / t).is_dir()]


def create(tool_dir: Path, workspace: Path | None, slug: str, template: str) -> Path:
    """Write recipes/<slug>/extension.yaml from the starter. Returns the file path."""
    if not SLUG_RE.match(slug) or len(slug) > SLUG_MAX:
        raise CreateError(
            f"`{slug}` isn't a valid slug — lowercase letters, digits, single hyphens, "
            f"≤ {SLUG_MAX} chars (e.g. jwt-inspector)"
        )
    if template not in extension.TEMPLATES:
        raise CreateError(f"unknown template `{template}` ({', '.join(extension.TEMPLATES)})")
    if not (tool_dir / generate.EXT_TEMPLATES_DIR / template).exists():
        have = ", ".join(implemented_templates(tool_dir)) or "none"
        raise CreateError(f"template `{template}` isn't implemented yet (available: {have})")
    target = generate.recipe_dir(tool_dir, slug)
    if target.exists():
        raise CreateError(f"recipe `{slug}` already exists at {target}")
    if workspace and workspace.exists() and slug in registry.slugs(workspace):
        raise CreateError(f"`{slug}` is already registered in {workspace / 'registry.json'}")
    extra = "".join(
        f"  - name: {perm}\n    justification: {TEMPLATE_PERMISSION_REASONS[perm]}\n"
        for perm in extension.TEMPLATE_PERMISSIONS.get(template, ())
    )
    text = render(
        (tool_dir / RECIPE_TEMPLATE).read_text(),
        {"slug": slug, "template": template, "template_permissions": extra},
    )
    target.mkdir(parents=True)
    path = target / generate.RECIPE_FILE
    path.write_text(text)
    return path
