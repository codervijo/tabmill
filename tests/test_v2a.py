"""v2.A: recipe schema v2 + migration, portfolio.yaml, lifecycle stages, the `bootstrap` rename,
and the `slots` / `templates` / `doctor` commands (D-040)."""

from __future__ import annotations

import shutil
import typing
from pathlib import Path
from typing import Any

import pytest
import typer
from typer.testing import CliRunner

from tabmill import (
    catalog,
    cli,
    extension,
    generate,
    lifecycle,
    portfolio,
    preflight,
    recipe_v2,
    registry,
    schema,
    surfaces,
)
from tabmill.catalog import Row
from tabmill.config import TOOL_DIR, Config

runner = CliRunner()
REAL = sorted(p.name for p in (TOOL_DIR / "recipes").iterdir() if p.is_dir())


@pytest.fixture
def app_cfg(cfg: Config, monkeypatch: pytest.MonkeyPatch) -> Config:
    cfg.workspace.mkdir(parents=True)
    monkeypatch.setattr(cli, "_load", lambda *_: cfg)
    monkeypatch.setattr(cli, "_config_and_workspace", lambda: (cfg, cfg.workspace))
    return cfg


def _copy_recipes(tool_dir: Path) -> None:
    shutil.copytree(TOOL_DIR / "recipes", tool_dir / "recipes", dirs_exist_ok=True)


def _as_v1(path: Path) -> None:
    """Strip the v2 keys so a real recipe looks like it did before the migration."""
    keys = ("schema_version:", "target:", "recipe_revision:", "trigger:")
    lines = path.read_text().splitlines(keepends=True)
    path.write_text("".join(x for x in lines if not x.startswith(keys)))


@pytest.mark.parametrize("slug", REAL)
def test_migration_only_adds_keys_and_keeps_comments(tool_dir: Path, slug: str) -> None:
    _copy_recipes(tool_dir)
    path = tool_dir / "recipes" / slug / "extension.yaml"
    _as_v1(path)
    before = path.read_text()
    assert recipe_v2.version_of(extension.load_file(path)) == 1
    assert recipe_v2.migrate(tool_dir, slug)
    after = path.read_text()
    added = [x for x in after.splitlines() if x not in before.splitlines()]
    assert [a.split(":")[0] for a in added] == [
        "schema_version",
        "target",
        "recipe_revision",
        "trigger",
    ]
    assert [x for x in after.splitlines() if x not in added] == before.splitlines()
    ext = generate.load_recipe(tool_dir, slug)
    assert ext["schema_version"] == 2
    assert not recipe_v2.migrate(tool_dir, slug)  # idempotent


def test_v1_recipe_still_loads(tool_dir: Path) -> None:
    _copy_recipes(tool_dir)
    _as_v1(tool_dir / "recipes" / REAL[0] / "extension.yaml")
    assert generate.load_recipe(tool_dir, REAL[0])["slug"] == REAL[0]


def test_template_literal_matches_the_registry() -> None:
    assert typing.get_args(schema.Template) == surfaces.NAMES
    assert "page-overlay" in surfaces.NAMES and "page-overlay" not in surfaces.IMPLEMENTED


def test_recipe_json_schema_file_is_current() -> None:
    assert (TOOL_DIR / recipe_v2.SCHEMA_FILE).read_text() == recipe_v2.json_schema()


def test_starter_recipe_is_v2(tool_dir: Path) -> None:
    path = catalog.create(tool_dir, None, "demo", "popup")
    assert recipe_v2.version_of(extension.load_file(path)) == 2


def test_portfolio_seed_and_slots(tool_dir: Path, tmp_path: Path) -> None:
    _copy_recipes(tool_dir)
    ws = tmp_path / "ws"
    ws.mkdir()
    registry.upsert(ws, REAL[0], {"published_state": "PUBLISHED"})
    assert portfolio.seed(tool_dir, ws) == REAL
    assert portfolio.seed(tool_dir, ws) == []
    data = portfolio.read(tool_dir)
    assert {i.approval for i in data.items.values()} == {"migrated"}
    data.items[REAL[1]].slot = "reserved"
    portfolio.write(tool_dir, data)
    view = portfolio.slots(tool_dir, ws)
    assert (view.published, view.reserved, view.free) == ([REAL[0]], [REAL[1]], 0)


def test_portfolio_rejects_unknown_fields(tool_dir: Path) -> None:
    (tool_dir / portfolio.PORTFOLIO_FILE).write_text("slots: {limit: 2}\nbogus: 1\n")
    with pytest.raises(portfolio.PortfolioError):
        portfolio.read(tool_dir)


@pytest.mark.parametrize(
    ("row", "reg", "approved", "released", "want"),
    [
        (Row("a", "invalid"), {}, False, False, "invalid"),
        (Row("a", "recipe"), {}, False, False, "shaped"),
        (Row("a", "recipe"), {}, True, False, "approved"),
        (Row("a", "generated", "0.1.0"), {}, True, False, "bootstrapped"),
        (Row("a", "built", "0.1.0"), {"checked_version": "0.1.0"}, True, False, "checked"),
        (Row("a", "built", "0.1.1"), {"checked_version": "0.1.0"}, True, False, "bootstrapped"),
        (Row("a", "built", "0.1.0"), {}, True, True, "shipped"),
        (Row("a", "built"), {"store_id": "x"}, True, False, "shipped"),
        (
            Row("a", "built"),
            {"store_id": "x", "published_state": "PUBLISHED"},
            True,
            True,
            "published",
        ),
        (
            Row("a", "built"),
            {"store_id": "x", "published_state": "PUBLISHED", "submitted_version": "0.1.1"},
            True,
            True,
            "maintained",
        ),
    ],
)
def test_lifecycle_stage(
    row: Row, reg: dict[str, Any], approved: bool, released: bool, want: str
) -> None:
    assert lifecycle.stage(row, reg, approved, released) == want


def test_new_slug_is_a_deprecated_alias_for_bootstrap(app_cfg: Config) -> None:
    result = runner.invoke(cli.app, ["new", "demo"])
    assert result.exit_code == 0 and "deprecated" in result.stdout
    assert (app_cfg.tool_dir / "recipes" / "demo" / "extension.yaml").exists()


def test_new_with_a_later_stage_name_says_when_it_arrives(app_cfg: Config) -> None:
    result = runner.invoke(cli.app, ["new", "verdict"])
    assert result.exit_code == 1 and "v2.F" in result.stdout


def test_bootstrap_refuses_a_stub_template(app_cfg: Config) -> None:
    runner.invoke(cli.app, ["bootstrap", "demo"])
    path = app_cfg.tool_dir / "recipes" / "demo" / "extension.yaml"
    text = (
        path.read_text()
        .replace("‹FILL›", "Demo thing")
        .replace(
            "template: popup",
            "template: page-overlay",
        )
    )
    text = text.replace(
        "    justification: Read the current page only after the user clicks the toolbar button.\n",
        "    justification: Read the current page only after the user clicks the toolbar button.\n"
        "  - name: scripting\n    justification: Draw the overlay on click.\n",
    )
    path.write_text(text)
    result = runner.invoke(cli.app, ["bootstrap", "demo"])
    assert result.exit_code == 1 and "isn't built yet" in result.stdout
    assert "demo" not in registry.slugs(app_cfg.workspace)


def test_check_records_the_checked_version(
    app_cfg: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry.upsert(app_cfg.workspace, "one", {"version": "0.1.0"})
    monkeypatch.setattr(cli, "_sync", lambda *_, **__: None)
    monkeypatch.setattr(cli, "_recipe", lambda *_: {"version": "0.1.0"})
    monkeypatch.setattr(cli, "_test", lambda *_: None)
    monkeypatch.setattr(cli, "_lint", lambda *_, **__: True)
    assert runner.invoke(cli.app, ["check"]).exit_code == 0
    assert registry.read(app_cfg.workspace)["extensions"]["one"]["checked_version"] == "0.1.0"


def test_doctor_fix_migrates_and_seeds(app_cfg: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    _copy_recipes(app_cfg.tool_dir)
    for slug in REAL:
        _as_v1(app_cfg.tool_dir / "recipes" / slug / "extension.yaml")
    monkeypatch.setattr(preflight, "run", lambda *_: [])
    first = runner.invoke(cli.app, ["doctor"])
    assert first.exit_code == 0 and "schema v1" in first.stdout
    fixed = runner.invoke(cli.app, ["doctor", "--fix"])
    assert fixed.exit_code == 0 and "seeded" in fixed.stdout
    assert set(portfolio.read(app_cfg.tool_dir).items) == set(REAL)
    again = runner.invoke(cli.app, ["doctor"])
    assert "schema v1" not in again.stdout and "every recipe listed" in again.stdout


def test_templates_and_slots_commands(app_cfg: Config) -> None:
    out = runner.invoke(cli.app, ["templates"]).stdout
    assert "page-overlay" in out and "stub" in out
    result = runner.invoke(cli.app, ["slots"])
    assert result.exit_code == 0 and "2 free" in result.stdout


def test_publish_moved_to_the_top_level() -> None:
    top = typer.main.get_command(cli.app)
    adv = typer.main.get_command(cli.advanced_app)
    assert isinstance(top, typer.core.TyperGroup) and isinstance(adv, typer.core.TyperGroup)
    assert "publish" in top.commands and "publish" not in adv.commands
