"""Lint (`check`, `ship`, `advanced lint`): mechanical Chrome Web Store checks
(skills/chrome-store-policy/reference.md).

Each rule has a dev and a release severity (D-015): placeholders warn while developing and
block a release. Bundle rules read the last build (`.output/chrome-mv3/`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from . import extension, generate, hub, listing, privacy, rules, targets
from .rules import Finding, Severity, similarity

__all__ = ["Finding", "Severity", "lint", "similarity"]

# Permission → token that must appear in the bundle when the API is used (perm-unused).
API_TOKENS = {
    "scripting": "scripting",
    "storage": "storage",
    "sidePanel": "sidePanel",
    "downloads": "downloads",
    "contextMenus": "contextMenus",
    "tabs": "tabs",
    "alarms": "alarms",
    "notifications": "notifications",
}
EVAL_RE = re.compile(r"(?<![\w.$])eval\(|new Function\(")
REMOTE_SCRIPT_RE = re.compile(
    r"<script[^>]+src=[\"']https?://|import\([\"']https?://|importScripts\([\"']https?://"
)


@dataclass(frozen=True)
class Rule:
    id: str
    dev: Severity
    release: Severity


# Rules that need the schema, a build, or the network. Recipe-level policy rules live in
# rules/lamill.yaml + rules.py (D-040), shared with the idea stage.
RULES = {
    r.id: r
    for r in (
        Rule("schema", "error", "error"),
        Rule("perm-unused", "warn", "error"),
        Rule("mv3-no-eval", "error", "error"),
        Rule("mv3-no-remote-script", "error", "error"),
        Rule("not-built", "warn", "error"),
        Rule("store-images", "warn", "error"),
        Rule("keyword-repeat", "warn", "error"),
        Rule("hub-urls", "warn", "error"),
        Rule("fill-placeholder", "warn", "error"),  # listing.md ‹FILL› (recipe ‹FILL›: rules.py)
    )
}


def _fetch(url: str) -> tuple[int | None, str]:
    """(HTTP status, body); status None when unreachable."""
    try:
        r = httpx.get(url, timeout=10, follow_redirects=True)
    except httpx.HTTPError:
        return None, ""
    return r.status_code, r.text


def lint(tool_dir: Path, workspace: Path | None, slug: str, *, release: bool) -> list[Finding]:
    out: list[Finding] = []

    def add(rule_id: str, message: str, severity: Severity | None = None) -> None:
        rule = RULES[rule_id]
        out.append(Finding(rule_id, severity or (rule.release if release else rule.dev), message))

    path = generate.recipe_dir(tool_dir, slug) / generate.RECIPE_FILE
    try:
        ext: dict[str, Any] = extension.load_file(path)
    except extension.ExtensionError as e:
        add("schema", str(e))
        return out
    for err in extension.validate(ext, slug):
        add("schema", err)

    try:
        out += rules.evaluate(
            rules.Subject(ext, slug, tool_dir, workspace), "release" if release else "dev"
        )
    except rules.RulesError as e:
        add("schema", str(e), "error")
    policy: privacy.Policy | None = None
    try:
        policy = privacy.load(tool_dir)
    except privacy.PolicyError:
        policy = None  # reported by the privacy-coverage rule

    if workspace is not None:
        problems = listing.image_problems(workspace, slug)
        if problems is None:
            add("store-images", "no store images — run `tabmill ship`")
        for problem in problems or []:
            add("store-images", problem)
        draft = listing.store_dir(workspace, slug) / listing.LISTING_FILE
        urls = (hub.PRIVACY_URL, hub.SUPPORT_URL)
        if not draft.exists():
            add("hub-urls", "no listing.md — run `tabmill ship` (privacy + support URLs)")
        else:
            text = draft.read_text()
            if extension.FILL_MARKER in text:
                n = text.count(extension.FILL_MARKER)
                add("fill-placeholder", f"listing.md has {n} unfilled ‹FILL›")
            for url in urls:
                if url not in text:
                    add("hub-urls", f"listing.md lacks {url}")
            if release:
                for url in urls:
                    code, body = _fetch(url)
                    if code != 200:
                        add("hub-urls", f"{url} not live (HTTP {code or 'unreachable'})")
                    elif url == hub.PRIVACY_URL and policy and policy.marker not in body:
                        add(
                            "hub-urls",
                            f"{url} doesn't show “{policy.marker}” — run `tabmill ship`, "
                            "deploy lamill.io",
                        )
        if draft.exists():
            for word, n in listing.keyword_repeats(draft.read_text()).items():
                add("keyword-repeat", f"`{word}` appears {n}× in listing.md (store limit: 5)")

    built = targets.for_recipe(ext).built_dir(workspace, slug) if workspace else None
    if built is None or not (built / "manifest.json").exists():
        add("not-built", "no build to inspect — run `tabmill try` (bundle rules skipped)")
        return out
    bundle = {
        f: f.read_text(errors="replace") for f in built.rglob("*") if f.suffix in {".js", ".html"}
    }
    for f, text in bundle.items():
        rel = f.relative_to(built)
        if f.suffix == ".js" and EVAL_RE.search(text):
            add("mv3-no-eval", f"{rel}: eval / new Function")
        if REMOTE_SCRIPT_RE.search(text):
            add("mv3-no-remote-script", f"{rel}: loads remote code")
    js = "\n".join(t for f, t in bundle.items() if f.suffix == ".js")
    for p in ext.get("permissions") or []:
        token = API_TOKENS.get(str(p.get("name"))) if isinstance(p, dict) else None
        if token and token not in js:
            add("perm-unused", f"`{p['name']}` declared but `{token}` never used in the bundle")
    return out
