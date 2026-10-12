from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tabmill.config import TOOL_DIR, Config


@pytest.fixture
def tool_dir(tmp_path: Path) -> Path:
    """A copy of the real skills/templates/ci so tests can mutate sources safely."""
    root = tmp_path / "projects" / "droyfun" / "tabmill"
    for name in ("skills", "templates", "ci"):
        shutil.copytree(TOOL_DIR / name, root / name)
    shutil.copy(TOOL_DIR / "privacy-policy.yaml", root / "privacy-policy.yaml")
    return root


@pytest.fixture
def builder(tmp_path: Path) -> Path:
    b = tmp_path / "projects" / "builder"
    b.mkdir(parents=True)
    (b / "Makefile").write_text("# stub builder\n")
    return b


@pytest.fixture
def cfg(tool_dir: Path, builder: Path, tmp_path: Path) -> Config:
    ws = tmp_path / "projects" / "plugins" / "chrome-extension-projects"
    return Config(
        tool_dir=tool_dir,
        workspace=ws,
        builder=builder,
        tool_repo="me/tabmill",
        hub_repo=tmp_path / "projects" / "sites" / "lamill.io",
    )
