"""v1.L: the lifecycle command surface and the next-step logic behind `tabmill status`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import typer
from typer.testing import CliRunner

from tabmill import cli, lifecycle, registry
from tabmill.catalog import Row
from tabmill.config import Config

runner = CliRunner()


@pytest.fixture
def app_cfg(cfg: Config, monkeypatch: pytest.MonkeyPatch) -> Config:
    cfg.workspace.mkdir(parents=True)
    monkeypatch.setattr(cli, "_load", lambda *_: cfg)
    monkeypatch.setattr(cli, "_config_and_workspace", lambda: (cfg, cfg.workspace))
    return cfg


def test_top_level_is_the_lifecycle() -> None:
    group = typer.main.get_command(cli.app)
    assert isinstance(group, typer.core.TyperGroup)
    assert list(group.commands) == [
        "new",
        "bootstrap",
        "try",
        "check",
        "ship",
        "publish",
        "status",
        "slots",
        "templates",
        "doctor",
        "brief",
        "evidence",
        "settings",
        "advanced",
    ]


def test_old_commands_live_under_advanced_and_settings() -> None:
    for args in (["advanced", "release"], ["advanced", "lint"], ["settings", "preflight"]):
        assert runner.invoke(cli.app, [*args, "--help"]).exit_code == 0
    assert runner.invoke(cli.app, ["release", "--help"]).exit_code != 0


@pytest.mark.parametrize(
    ("row", "reg", "released", "want"),
    [
        (Row("a", "invalid"), {}, False, "fix recipes/a/extension.yaml"),
        (Row("a", "recipe", placeholders=["name"]), {}, False, "fill ‹FILL›"),
        (Row("a", "recipe", placeholders=["cta_url"]), {}, False, "tabmill bootstrap a"),
        (Row("a", "generated"), {}, False, "tabmill try a"),
        (Row("a", "built", placeholders=["cta_url"]), {}, False, "fill cta_url"),
        (Row("a", "built"), {}, False, "tabmill ship a"),
        (Row("a", "built", "1.0"), {}, True, "upload releases/a-1.0/"),
        (Row("a", "built"), {"store_id": "x"}, True, "tabmill status a --refresh"),
        (Row("a", "built"), {"store_id": "x", "warned": True}, True, "policy problem"),
        (
            Row("a", "built", "1.1"),
            {"store_id": "x", "published_state": "PUBLISHED", "submitted_version": "1.0"},
            True,
            "tabmill publish a",
        ),
        (Row("a", "built"), {"store_id": "x", "published_state": "PUBLISHED"}, True, "—"),
    ],
)
def test_next_step(row: Row, reg: dict[str, Any], released: bool, want: str) -> None:
    assert lifecycle.next_step(row, reg, released).startswith(want)


def test_new_writes_the_recipe_first_then_refuses_until_filled(app_cfg: Config) -> None:
    first = runner.invoke(cli.app, ["new", "demo"])
    recipe = app_cfg.tool_dir / "recipes" / "demo" / "extension.yaml"
    assert first.exit_code == 0 and recipe.exists()
    assert "demo" not in registry.slugs(app_cfg.workspace)
    second = runner.invoke(cli.app, ["new", "demo"])
    assert second.exit_code == 1 and "demo" not in registry.slugs(app_cfg.workspace)


def test_status_json_carries_the_next_command(app_cfg: Config) -> None:
    runner.invoke(cli.app, ["new", "demo"])
    rows = json.loads(runner.invoke(cli.app, ["status", "--json"]).stdout)
    assert [(r["slug"], r["status"]) for r in rows] == [("demo", "recipe")]
    assert rows[0]["next"].startswith("fill ‹FILL›")
    assert runner.invoke(cli.app, ["status", "nope"]).exit_code == 1


def _register(ws: Path, slug: str, **fields: Any) -> None:
    registry.upsert(ws, slug, {"version": "0.1.0", "status": "generated", **fields})


def test_publish_refuses_unattended_before_any_work(
    app_cfg: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    _register(app_cfg.workspace, "demo", store_id="abc")

    def no_work(*_: object, **__: object) -> None:
        raise AssertionError("work started before the attended check")

    for name in ("_recipe", "_release", "_make", "_preflight"):
        monkeypatch.setattr(cli, name, no_work)
    result = runner.invoke(cli.app, ["publish", "demo"])
    assert result.exit_code == 1 and "unattended" in result.stdout
    # D-040: ship never uploads.
    result = runner.invoke(cli.app, ["ship", "demo", "--publish"])
    assert result.exit_code == 1 and "tabmill publish demo" in result.stdout


def test_check_without_slug_runs_every_extension_and_keeps_going(
    app_cfg: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    for slug in ("one", "two"):
        _register(app_cfg.workspace, slug)
    ran: list[str] = []

    def fake_test(_: Config, slug: str) -> None:
        ran.append(slug)
        if slug == "one":
            raise typer.Exit(2)

    monkeypatch.setattr(cli, "_sync", lambda *_, **__: None)
    monkeypatch.setattr(cli, "_recipe", lambda *_: {})
    monkeypatch.setattr(cli, "_test", fake_test)
    monkeypatch.setattr(cli, "_lint", lambda *_, **__: True)
    result = runner.invoke(cli.app, ["check"])
    assert ran == ["one", "two"]
    assert result.exit_code == 1 and "1 of 2 failed — one" in result.stdout
