from __future__ import annotations

import json
import shutil

import pytest

from tabmill import hub, lint, listing, privacy, registry
from tabmill.config import TOOL_DIR, Config

SLUG = "save-page-pdf-md"


@pytest.fixture
def setup(cfg: Config) -> Config:
    shutil.copytree(TOOL_DIR / "recipes" / SLUG, cfg.tool_dir / "recipes" / SLUG)
    cfg.workspace.mkdir(parents=True)
    registry.upsert(cfg.workspace, SLUG, {"version": "0.1.0"})
    return cfg


def test_real_recipes_are_covered_by_the_shared_policy() -> None:
    from tabmill import catalog, extension, generate

    policy = privacy.load(TOOL_DIR)
    for slug in catalog.recipe_slugs(TOOL_DIR):
        ext = extension.load_file(generate.recipe_dir(TOOL_DIR, slug) / generate.RECIPE_FILE)
        assert privacy.coverage(ext, policy) == [], slug


def test_coverage_names_every_gap() -> None:
    policy = privacy.load(TOOL_DIR)
    ext = {
        "permissions": [{"name": "activeTab"}, {"name": "downloads"}],
        "host_permissions": [{"name": "https://example.com/*"}],
        "analytics": True,
        "remote_code": True,
        "data_collected": ["email"],
    }
    gaps = privacy.coverage(ext, policy)
    assert len(gaps) == 5 and "`downloads`" in gaps[0]


def _uncovered(cfg: Config) -> None:
    recipe = cfg.tool_dir / "recipes" / SLUG / "extension.yaml"
    recipe.write_text(recipe.read_text().replace("analytics: false", "analytics: true"))


def test_lint_privacy_coverage_warns_in_dev_blocks_release(setup: Config) -> None:
    _uncovered(setup)
    dev = [f for f in lint.lint(setup.tool_dir, None, SLUG, release=False)]
    rel = [f for f in lint.lint(setup.tool_dir, None, SLUG, release=True)]
    assert any(f.rule == "privacy-coverage" and f.severity == "warn" for f in dev)
    assert any(f.rule == "privacy-coverage" and f.severity == "error" for f in rel)


def test_live_page_must_show_current_version(
    setup: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    draft = listing.store_dir(setup.workspace, SLUG) / listing.LISTING_FILE
    draft.parent.mkdir(parents=True, exist_ok=True)
    draft.write_text(f"{hub.PRIVACY_URL}\n{hub.SUPPORT_URL}\n")
    monkeypatch.setattr(lint, "_fetch", lambda url: (200, "Policy version 0"))
    msgs = [f.message for f in lint.lint(setup.tool_dir, setup.workspace, SLUG, release=True)]
    assert any("doesn't show “Policy version 1”" in m for m in msgs)


def test_export_matches_policy(cfg: Config) -> None:
    policy = privacy.load(cfg.tool_dir)
    path, changed = privacy.write(cfg.hub_repo, policy)
    data = json.loads(path.read_text())
    assert changed and data["version"] == policy.version
    assert set(data) == {"version", "updated", "permissions"}
    assert privacy.write(cfg.hub_repo, policy)[1] is False


def test_privacy_slug_reserved() -> None:
    assert "privacy" in hub.RESERVED_SLUGS
