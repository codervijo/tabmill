from __future__ import annotations

from typing import Any

import pytest

from tabmill import extension

BASE: dict[str, Any] = {
    "name": "Save Page as Markdown or PDF",
    "slug": "demo",
    "version": "0.1.0",
    "summary": "Save the current page as Markdown or PDF.",
    "single_purpose": "Save the current web page as clean Markdown or a PDF.",
    "template": "popup",
    "permissions": [{"name": "activeTab", "justification": "Read the page on click."}],
    "portfolio_site": "markpdf.dev",
    "cta_text": "x",
    "cta_url": "https://markpdf.dev",
    "utm_campaign": "demo",
    "target_keywords": ["demo tool"],
    "store_category": "Tools",
}


def test_valid_extension_has_no_errors() -> None:
    assert extension.validate(dict(BASE), "demo") == []


@pytest.mark.parametrize(
    ("patch", "needle"),
    [
        ({"name": "x" * 76}, "`name` is 76"),
        ({"summary": "x" * 133}, "`summary` is 133"),
        ({"template": "toolbar"}, "`template`"),
        ({"slug": "other"}, "directory"),
        ({"analytics": True}, "analytics"),
        ({"permissions": [{"name": "tabs", "justification": " "}]}, "tabs` has no justification"),
    ],
)
def test_validation_errors(patch: dict[str, Any], needle: str) -> None:
    errors = extension.validate({**BASE, **patch}, "demo")
    assert any(needle in e for e in errors), errors


@pytest.mark.parametrize(
    ("patch", "needle"),
    [
        ({"permision": []}, "unknown field `permision`"),
        ({"version": "1.0"}, "`version`"),
        ({"remote_code": True}, "`remote_code`"),
        ({"permissions": []}, "`permissions`"),
        ({"target_keywords": "seo"}, "`target_keywords`"),
    ],
)
def test_schema_errors(patch: dict[str, Any], needle: str) -> None:
    errors = extension.validate({**BASE, **patch}, "demo")
    assert any(needle in e for e in errors), errors


def test_missing_fields_reported() -> None:
    assert "missing field `cta_url`" in extension.validate(
        {k: v for k, v in BASE.items() if k != "cta_url"}, "demo"
    )


@pytest.mark.parametrize(
    ("url", "placeholder"),
    [
        ("https://rankmill.example/local-seo-audit", True),
        ("https://example.com/x", True),
        ("https://foo.test", True),
        ("‹FILL›", True),
        ("", True),
        ("https://markpdf.dev", False),
        ("https://www.example-store.com", False),
    ],
)
def test_placeholder_detection(url: str, placeholder: bool) -> None:
    assert extension.is_placeholder(url) is placeholder
