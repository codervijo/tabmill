from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tabmill import catalog, generate, registry
from tabmill.config import TOOL_DIR, Config


@pytest.fixture
def tool(cfg: Config) -> Path:
    shutil.copytree(
        TOOL_DIR / "recipes" / "save-page-pdf-md", cfg.tool_dir / "recipes" / "save-page-pdf-md"
    )
    cfg.workspace.mkdir(parents=True)
    return cfg.tool_dir


def _fill(path: Path) -> None:
    text = path.read_text()
    for key, value in {
        "name": "Demo Tool",
        "summary": "Do one thing.",
        "single_purpose": "Do one useful thing on the current page.",
    }.items():
        text = text.replace(f"{key}: ‹FILL›", f"{key}: {value}", 1)
    path.write_text(text)


def test_create_writes_starter_recipe(tool: Path, cfg: Config) -> None:
    path = catalog.create(tool, cfg.workspace, "demo-tool", "popup")
    text = path.read_text()
    assert "slug: demo-tool" in text and "utm_campaign: demo-tool" in text
    assert "template: popup" in text and "{{" not in text
    assert not (cfg.workspace / "extensions" / "demo-tool").exists()  # never touches workspace


@pytest.mark.parametrize("slug", ["Demo", "demo_tool", "-demo", "demo--x", "x" * 41, ""])
def test_create_rejects_bad_slugs(tool: Path, cfg: Config, slug: str) -> None:
    with pytest.raises(catalog.CreateError, match="valid slug"):
        catalog.create(tool, cfg.workspace, slug, "popup")


def test_create_refuses_existing_recipe(tool: Path, cfg: Config) -> None:
    with pytest.raises(catalog.CreateError, match="already exists"):
        catalog.create(tool, cfg.workspace, "save-page-pdf-md", "popup")


def test_create_refuses_registered_slug(tool: Path, cfg: Config) -> None:
    registry.upsert(cfg.workspace, "ghost", {"version": "1.0.0"})
    with pytest.raises(catalog.CreateError, match="already registered"):
        catalog.create(tool, cfg.workspace, "ghost", "popup")


@pytest.mark.parametrize(
    ("template", "msg"), [("toolbar", "unknown"), ("page-overlay", "isn't implemented")]
)
def test_create_refuses_bad_template(tool: Path, cfg: Config, template: str, msg: str) -> None:
    with pytest.raises(catalog.CreateError, match=msg):
        catalog.create(tool, cfg.workspace, "demo", template)


def test_new_refuses_unfilled_manifest_fields(tool: Path, cfg: Config) -> None:
    catalog.create(tool, cfg.workspace, "demo", "popup")
    with pytest.raises(generate.RecipeError, match="`name` is still ‹FILL›"):
        generate.load_recipe(tool, "demo")


def test_filled_starter_loads_and_reports_remaining_placeholders(tool: Path, cfg: Config) -> None:
    path = catalog.create(tool, cfg.workspace, "demo", "popup")
    _fill(path)
    ext = generate.load_recipe(tool, "demo")
    assert catalog.unfilled_manifest_fields(ext) == []
    left = catalog.placeholders(ext)
    assert {"portfolio_site", "cta_text", "cta_url", "store_category", "target_keywords[0]"} <= set(
        left
    )


def test_list_statuses(tool: Path, cfg: Config) -> None:
    ws = cfg.workspace
    _fill(catalog.create(tool, ws, "demo", "popup"))  # recipe only
    registry.upsert(ws, "save-page-pdf-md", {"version": "0.1.0", "status": "generated"})
    built = ws / "extensions" / "save-page-pdf-md" / ".output" / "chrome-mv3"
    built.mkdir(parents=True)
    (built / "manifest.json").write_text("{}")
    registry.upsert(ws, "gone", {"version": "2.0.0"})  # orphan
    bad = tool / "recipes" / "broken"
    bad.mkdir()
    (bad / "extension.yaml").write_text("name: [unclosed")
    by_slug = {r.slug: r for r in catalog.rows(tool, ws)}
    assert by_slug["save-page-pdf-md"].status == "built"
    assert by_slug["save-page-pdf-md"].placeholders == []
    assert by_slug["demo"].status == "recipe"
    assert by_slug["gone"].status == "orphan" and by_slug["gone"].version == "2.0.0"
    assert by_slug["broken"].status == "invalid" and "invalid YAML" in by_slug["broken"].error
    json.dumps([r.to_dict() for r in by_slug.values()])  # serializable


def test_list_without_workspace_shows_recipes(tool: Path) -> None:
    rows = catalog.rows(tool, None)
    assert [(r.slug, r.status) for r in rows] == [("save-page-pdf-md", "recipe")]


def test_placeholder_cta_flagged(tool: Path, cfg: Config) -> None:
    path = catalog.create(tool, cfg.workspace, "seo", "popup")
    _fill(path)
    path.write_text(
        path.read_text().replace(
            "cta_url: ‹FILL›", "cta_url: https://rankmill.example/local-seo-audit"
        )
    )
    row = {r.slug: r for r in catalog.rows(tool, cfg.workspace)}["seo"]
    assert "cta_url" in row.placeholders
