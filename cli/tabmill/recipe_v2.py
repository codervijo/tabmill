"""Recipe schema v2 migration (D-040). Text insertion, not a YAML round-trip: recipe comments
hold decisions (e.g. D-035 notes) and must survive. Idempotent."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import extension, generate, schema, surfaces

SCHEMA_FILE = "schemas/recipe_v2.schema.json"
_KEY_RE = re.compile(r"^[a-z_]+:", re.M)


def version_of(ext: dict[str, Any]) -> int:
    return int(ext.get("schema_version", 1))


def v2_lines(ext: dict[str, Any]) -> str:
    trigger = surfaces.SURFACES.get(str(ext.get("template")), surfaces.SURFACES["popup"]).trigger
    return (
        f"schema_version: {schema.SCHEMA_VERSION}  # recipe schema (D-040)\n"
        f"target: {surfaces.TARGET}\n"
        "recipe_revision: 1  # bump to change frozen fields after `tabmill approve`\n"
        f"trigger: {trigger}\n"
    )


def migrate_text(text: str, ext: dict[str, Any]) -> str:
    """v1 recipe text → v2: the v2 keys go before the first top-level key; nothing else moves."""
    if version_of(ext) >= schema.SCHEMA_VERSION:
        return text
    m = _KEY_RE.search(text)
    at = m.start() if m else len(text)
    return text[:at] + v2_lines(ext) + text[at:]


def migrate(tool_dir: Path, slug: str) -> bool:
    """Rewrite recipes/<slug>/extension.yaml as v2. True if the file changed."""
    path = generate.recipe_dir(tool_dir, slug) / generate.RECIPE_FILE
    text = path.read_text()
    new = migrate_text(text, extension.load_file(path))
    if new == text:
        return False
    path.write_text(new)
    return True


def json_schema() -> str:
    """schemas/recipe_v2.schema.json content, generated from the pydantic model."""
    return json.dumps(schema.Recipe.model_json_schema(), indent=2, sort_keys=True) + "\n"
