from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tabmill import extension, generate, landing
from tabmill.config import TOOL_DIR, Config

SLUG = "save-page-pdf-md"


@pytest.fixture
def tool(cfg: Config) -> Path:
    shutil.copytree(TOOL_DIR / "recipes" / SLUG, cfg.tool_dir / "recipes" / SLUG)
    return cfg.tool_dir


def _ext(tool: Path) -> dict[str, object]:
    return extension.load_file(generate.recipe_dir(tool, SLUG) / "extension.yaml")


def test_url_defaults_to_first_keyword(tool: Path) -> None:
    ext = {**_ext(tool), "landing_path": None}
    assert landing.landing_url(ext) == "https://markpdf.dev/save-webpage-as-pdf"
    assert (
        landing.landing_url({**ext, "landing_path": "tools/save"})
        == "https://markpdf.dev/tools/save"
    )


def test_brief_without_store_says_coming_soon(tool: Path) -> None:
    text = landing.brief(_ext(tool), None, None)
    assert "Primary query: **save webpage as pdf**" in text
    assert "Coming soon" in text and "utm_" not in text
    assert "https://lamill.io/extensions/privacy" in text
    assert "Invent numbers" in text


def test_brief_with_store_has_utm_link(tool: Path) -> None:
    text = landing.brief(_ext(tool), "abc123", "## Detailed description\nIt saves pages.\n")
    assert (
        "chromewebstore.google.com/detail/abc123?utm_source=markpdf.dev&utm_medium=landing" in text
    )
    assert "It saves pages." in text


def test_brief_drops_repeated_and_unfilled_listing_copy(tool: Path) -> None:
    ext = _ext(tool)
    draft = f"## Detailed description\n{ext['summary']}\n\n‹FILL› — how to use it\n\nReal copy.\n"
    text = landing.brief(ext, None, draft)
    assert text.count(ext["summary"]) == 1
    assert "‹FILL›" not in text and "Real copy." in text


def test_set_landing_url_edits_only_that_line(tool: Path) -> None:
    path = generate.recipe_dir(tool, SLUG) / "extension.yaml"
    before = path.read_text()
    assert landing.set_landing_url(tool, SLUG, "https://markpdf.dev/markdown-to-pdf")
    after = path.read_text()
    assert "landing_page_url: https://markpdf.dev/markdown-to-pdf" in after
    assert len(after.splitlines()) == len(before.splitlines())
    assert not landing.set_landing_url(tool, SLUG, "https://markpdf.dev/markdown-to-pdf")
    assert generate.load_recipe(tool, SLUG)["landing_page_url"].endswith("/markdown-to-pdf")


def test_precheck_flags_placeholder_site() -> None:
    assert landing.precheck({"portfolio_site": "‹FILL›", "target_keywords": ["x"]})
