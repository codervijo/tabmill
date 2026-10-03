from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from tabmill import config, workspace
from tabmill.config import Config


def test_scaffold_creates_seed_files(cfg: Config) -> None:
    assert workspace.scaffold(cfg)
    ws = cfg.workspace
    for rel in ("package.json", "registry.json", "TODO.md", ".gitignore"):
        assert (ws / rel).exists(), rel
    assert (ws / "extensions").is_dir()
    assert json.loads((ws / "registry.json").read_text()) == {"extensions": {}}
    assert not (ws / "Makefile").exists()  # managed files come from sync, not scaffold


def test_managed_files_use_computed_relative_layout(cfg: Config) -> None:
    files = {k: v.decode() for k, v in workspace.managed_files(cfg).items()}
    assert '"../../droyfun/tabmill/packages/*"' in files["pnpm-workspace.yaml"]
    local = files["Makefile.local"]
    assert f"VOLUME_MOUNT := {cfg.tool_dir.parents[1]}:/usr/src/app/" in local
    assert "CONTAINER_WS := /usr/src/app/plugins/chrome-extension-projects" in local
    assert "/usr/src/app/droyfun/tabmill/packages" in local
    assert "BUILDER_PATH ?= ../../builder" in files["Makefile"]
    ci = files[".github/workflows/extensions.yml"]
    assert "repository: me/tabmill" in ci and "path: droyfun/tabmill" in ci
    for rel, text in files.items():
        assert "{{" not in text.replace("${{", ""), rel


def test_scaffold_never_overwrites_existing_files(cfg: Config) -> None:
    cfg.workspace.mkdir(parents=True)
    (cfg.workspace / "TODO.md").write_text("mine")
    legacy = cfg.workspace / "chrome-dejargon" / "manifest.json"
    legacy.parent.mkdir()
    legacy.write_text("{}")
    assert workspace.scaffold(cfg)
    assert (cfg.workspace / "TODO.md").read_text() == "mine"
    assert legacy.read_text() == "{}"


def test_scaffold_fails_without_builder(cfg: Config, tmp_path: Path) -> None:
    bad = dataclasses.replace(cfg, builder=tmp_path / "nope")
    assert not workspace.scaffold(bad)


def test_config_env_wins(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "tabmill.config.json").write_text('{"workspace": "ws-from-file"}')
    monkeypatch.setenv("TABMILL_WORKSPACE", str(tmp_path / "ws-from-env"))
    assert config.load(tmp_path).workspace == tmp_path / "ws-from-env"
    monkeypatch.delenv("TABMILL_WORKSPACE")
    assert config.load(tmp_path).workspace == tmp_path / "ws-from-file"


def test_config_missing_workspace_names_fix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("TABMILL_WORKSPACE", raising=False)
    with pytest.raises(config.ConfigError, match="TABMILL_WORKSPACE"):
        config.load(tmp_path)
