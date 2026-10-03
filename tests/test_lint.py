from __future__ import annotations

import shutil

import pytest

from tabmill import lint, registry
from tabmill.config import TOOL_DIR, Config

SLUG = "save-page-pdf-md"


@pytest.fixture
def setup(cfg: Config) -> Config:
    shutil.copytree(TOOL_DIR / "recipes" / SLUG, cfg.tool_dir / "recipes" / SLUG)
    cfg.workspace.mkdir(parents=True)
    registry.upsert(cfg.workspace, SLUG, {"version": "0.1.0"})
    return cfg


def _build(cfg: Config, files: dict[str, str]) -> None:
    out = cfg.workspace / "extensions" / SLUG / ".output" / "chrome-mv3"
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text("{}")
    for name, text in files.items():
        (out / name).write_text(text)


def _ids(findings: list[lint.Finding]) -> dict[str, str]:
    return {f.rule: f.severity for f in findings}


def test_placeholder_warns_in_dev_and_blocks_release(setup: Config) -> None:
    _build(setup, {"a.js": "browser.scripting.executeScript; browser.storage.session"})
    assert _ids(lint.lint(setup.tool_dir, setup.workspace, SLUG, release=False)) == {
        "fill-placeholder": "warn",
        "store-images": "warn",
    }
    assert _ids(lint.lint(setup.tool_dir, setup.workspace, SLUG, release=True)) == {
        "fill-placeholder": "error",
        "store-images": "error",
    }


def test_bundle_rules(setup: Config) -> None:
    _build(
        setup,
        {
            "a.js": 'eval("x"); import("https://cdn.example.com/x.js")',
            "p.html": '<script src="https://evil.example/x.js"></script>',
        },
    )
    ids = _ids(lint.lint(setup.tool_dir, setup.workspace, SLUG, release=False))
    assert ids["mv3-no-eval"] == "error"
    assert ids["mv3-no-remote-script"] == "error"
    assert ids["perm-unused"] == "warn"  # scripting / storage never referenced


def test_evaluate_is_not_eval(setup: Config) -> None:
    _build(setup, {"a.js": "x.evaluate(y); browser.scripting; browser.storage"})
    assert "mv3-no-eval" not in _ids(
        lint.lint(setup.tool_dir, setup.workspace, SLUG, release=False)
    )


def test_not_built(setup: Config) -> None:
    ids = _ids(lint.lint(setup.tool_dir, setup.workspace, SLUG, release=True))
    assert ids["not-built"] == "error"


def test_broad_host_and_similarity(setup: Config) -> None:
    path = setup.tool_dir / "recipes" / SLUG / "extension.yaml"
    text = path.read_text().replace(
        "optional_permissions: []",
        "optional_permissions: []\nhost_permissions:\n  - name: <all_urls>\n    justification: x",
    )
    path.write_text(text)
    twin = setup.tool_dir / "recipes" / "twin"
    twin.mkdir()
    (twin / "extension.yaml").write_text(
        "single_purpose: Save the current web page as clean Markdown or a branded PDF.\n"
    )
    ids = _ids(lint.lint(setup.tool_dir, setup.workspace, SLUG, release=False))
    assert ids["perm-broad-host"] == "error"
    assert ids["portfolio-similarity"] == "error"


def test_similarity() -> None:
    assert lint.similarity("Audit local SEO", "audit local seo") == 1.0
    assert lint.similarity("Save page as PDF", "Decode JWT tokens") == 0.0


def test_store_images_and_keyword_repeat(setup: Config) -> None:
    import struct

    _build(setup, {"a.js": "browser.scripting; browser.storage"})
    store = setup.workspace / "extensions" / SLUG / ".output" / "store"
    store.mkdir(parents=True)

    def png(name: str, w: int, h: int) -> None:
        ihdr = struct.pack(">II", w, h)
        (store / name).write_bytes(
            b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + ihdr + b"\x08\x06"
        )

    png("icon-128.png", 128, 128)
    png("promo-440x280.png", 440, 280)
    png("screenshot-1.png", 1280, 720)  # wrong size
    (store / "listing.md").write_text(
        "## Title\nmarkdown\n## Detailed description\n" + "markdown " * 6
    )
    ids = _ids(lint.lint(setup.tool_dir, setup.workspace, SLUG, release=True))
    assert ids["store-images"] == "error"
    assert ids["keyword-repeat"] == "error"
    png("screenshot-1.png", 1280, 800)
    (store / "listing.md").write_text(
        "## Title\nmarkdown\n## Detailed description\n" + "markdown " * 5
    )
    ids = _ids(lint.lint(setup.tool_dir, setup.workspace, SLUG, release=True))
    assert "store-images" not in ids and "keyword-repeat" not in ids
