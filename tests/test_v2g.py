"""v2.G: target-adapter seam — chrome-mv3 behind `targets`, data in target.yaml."""

from __future__ import annotations

from pathlib import Path

import pytest

from tabmill import extension, generate, rules, targets
from tabmill.config import TOOL_DIR

BASE = {
    "name": "N",
    "summary": "S",
    "version": "0.1.0",
    "permissions": [{"name": "activeTab", "justification": "x"}],
}


def test_registry_and_unknown_target() -> None:
    assert targets.get().id == "chrome-mv3" and targets.for_recipe({}).id == "chrome-mv3"
    with pytest.raises(targets.TargetError, match="wordpress"):
        targets.get("wordpress")


def test_manifest_action_only_for_panel_templates() -> None:
    t = targets.get()
    assert "action" not in t.manifest({**BASE, "template": "popup"})
    panel = t.manifest({**BASE, "template": "side-panel"})
    assert panel["action"] == {"default_title": "N"}
    assert extension.to_manifest({**BASE, "template": "maps-overlay"})["action"]


def test_target_data_drives_limits_and_paths(tool_dir: Path) -> None:
    t = targets.get()
    assert (t.limits.name, t.limits.summary) == (75, 132)
    assert t.templates_dir(tool_dir) == tool_dir / "templates" / "extension"
    assert t.store_images.screenshots == [(1280, 800), (640, 400)]
    long = {"name": "x" * 76, "single_purpose": "Count words.", "template": "popup"}
    found = rules.evaluate(rules.Subject(long, "x", tool_dir), "idea")
    assert any(f.rule == "name-length" and "max 75" in f.message for f in found)


def test_real_recipes_generate_through_the_target() -> None:
    for slug in ("save-page-pdf-md", "local-seo-checker", "pressure-wash-quote"):
        files = generate.extension_files(TOOL_DIR, slug)
        assert extension.GENERATED_MANIFEST in files and "package.json" in files
