"""extension.yaml reading, validation, and manifest fields (v1.B minimal; typed schema in v1.E).

The CLI is the only reader of extension.yaml (ADR-0002). `generate` turns the fields into
`manifest.gen.json`, which the generated `wxt.config.ts` passes to WXT (ADR-0004).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from . import schema

GENERATED_MANIFEST = "manifest.gen.json"
NAME_MAX = 75  # developer.chrome.com/docs/extensions/reference/manifest/name
SUMMARY_MAX = 132  # .../manifest/description
REQUIRED = (
    "name",
    "slug",
    "version",
    "summary",
    "single_purpose",
    "template",
    "permissions",
    "portfolio_site",
    "cta_text",
    "cta_url",
    "utm_campaign",
)
TEMPLATES = ("popup", "side-panel", "devtools", "context-menu", "maps-overlay")
# Permissions a template's own code needs; the recipe must declare + justify them.
TEMPLATE_PERMISSIONS = {"side-panel": ("sidePanel",)}
# RFC 2606 / RFC 6761 reserved names → placeholder URLs (D-015).
_RESERVED_TLDS = (".example", ".test", ".invalid", ".localhost")
_RESERVED_HOSTS = ("example.com", "example.net", "example.org")
FILL_MARKER = "‹FILL›"


class ExtensionError(Exception):
    """extension.yaml missing or unreadable."""


def load_file(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        raise ExtensionError(f"{path}: invalid YAML ({e})") from e
    if not isinstance(data, dict):
        raise ExtensionError(f"{path}: must be a mapping")
    return data


def is_placeholder(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return True
    if FILL_MARKER in value:
        return True
    host = (urlparse(value).hostname or "").lower()
    return host.endswith(_RESERVED_TLDS) or host in _RESERVED_HOSTS


def validate(ext: dict[str, Any], slug: str) -> list[str]:
    """Errors that block a build. (Policy lint proper is v1.E.)"""
    errors = schema.structure_errors(ext)
    if any(e.startswith("missing field") or "`template`" in e for e in errors):
        return errors
    if ext["slug"] != slug:
        errors.append(f"`slug` is {ext['slug']!r} but the directory is {slug!r}")
    if len(str(ext["name"])) > NAME_MAX:
        errors.append(f"`name` is {len(str(ext['name']))} chars (max {NAME_MAX})")
    if len(str(ext["summary"])) > SUMMARY_MAX:
        errors.append(f"`summary` is {len(str(ext['summary']))} chars (max {SUMMARY_MAX})")
    if ext["template"] not in TEMPLATES:
        errors.append(f"`template` must be one of {', '.join(TEMPLATES)}")
    if ext.get("analytics", False) is not False:
        errors.append("`analytics` opt-in isn't supported until v1.G")
    declared = {p.get("name") for p in ext["permissions"] if isinstance(p, dict)}
    for need in TEMPLATE_PERMISSIONS.get(str(ext["template"]), ()):
        if need not in declared:
            errors.append(f"template `{ext['template']}` needs permission `{need}`")
    for key in ("permissions", "optional_permissions", "host_permissions"):
        for perm in ext.get(key) or []:
            if not isinstance(perm, dict) or not perm.get("name"):
                errors.append(f"`{key}` entries need `name` + `justification`")
            elif not str(perm.get("justification", "")).strip():
                errors.append(f"`{key}.{perm['name']}` has no justification")
    return errors


def placeholder_fields(ext: dict[str, Any]) -> list[str]:
    """URL fields still holding placeholders — warn in dev, block at release (D-015)."""
    fields = ["cta_url"] + (["landing_page_url"] if ext.get("landing_page_url") else [])
    return [f for f in fields if is_placeholder(ext.get(f))]


def to_manifest(ext: dict[str, Any]) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "name": ext["name"],
        "description": ext["summary"],
        "version": str(ext["version"]),
        "permissions": [p["name"] for p in ext["permissions"]],
    }
    for key in ("optional_permissions", "host_permissions"):
        if ext.get(key):
            manifest[key] = [p["name"] for p in ext[key]]
    return manifest
