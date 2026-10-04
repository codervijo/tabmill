"""`tabmill lint`: mechanical Chrome Web Store checks (skills/chrome-store-policy/reference.md).

Each rule has a dev and a release severity (D-015): placeholders warn while developing and
block a release. Bundle rules read the last build (`.output/chrome-mv3/`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx

from . import catalog, extension, generate, hub, listing

Severity = Literal["error", "warn"]
BROAD_HOSTS = {"<all_urls>", "*://*/*", "https://*/*", "http://*/*"}
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
SIMILARITY_WARN, SIMILARITY_ERROR = 0.6, 0.9
STOPWORDS = {
    "the",
    "a",
    "an",
    "of",
    "on",
    "for",
    "to",
    "and",
    "or",
    "as",
    "in",
    "you",
    "are",
    "page",
    "current",
    "web",
}


@dataclass(frozen=True)
class Rule:
    id: str
    dev: Severity
    release: Severity


RULES = {
    r.id: r
    for r in (
        Rule("schema", "error", "error"),
        Rule("perm-broad-host", "error", "error"),
        Rule("perm-unused", "warn", "error"),
        Rule("fill-placeholder", "warn", "error"),
        Rule("cta-placeholder", "warn", "error"),
        Rule("mv3-no-eval", "error", "error"),
        Rule("mv3-no-remote-script", "error", "error"),
        Rule("not-built", "warn", "error"),
        Rule("portfolio-similarity", "warn", "warn"),
        Rule("store-images", "warn", "error"),
        Rule("keyword-repeat", "warn", "error"),
        Rule("hub-urls", "warn", "error"),
    )
}


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: Severity
    message: str


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS}


def similarity(a: str, b: str) -> float:
    wa, wb = _words(a), _words(b)
    return len(wa & wb) / len(wa | wb) if wa | wb else 0.0


def _http_status(url: str) -> int | None:
    try:
        return httpx.get(url, timeout=10, follow_redirects=True).status_code
    except httpx.HTTPError:
        return None


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

    for key in ("permissions", "optional_permissions", "host_permissions"):
        for p in ext.get(key) or []:
            if isinstance(p, dict) and p.get("name") in BROAD_HOSTS:
                add("perm-broad-host", f"`{p['name']}` in {key} — prefer activeTab (longer review)")
    for field in catalog.fill_fields(ext):
        add("fill-placeholder", f"`{field}` is still ‹FILL›")
    for field in extension.placeholder_fields(ext):
        if field not in catalog.fill_fields(ext):
            add("cta-placeholder", f"`{field}` = {ext.get(field)!r} is a placeholder URL")

    for other in catalog.recipe_slugs(tool_dir):
        if other == slug:
            continue
        try:
            o = extension.load_file(generate.recipe_dir(tool_dir, other) / generate.RECIPE_FILE)
        except extension.ExtensionError:
            continue
        sim = similarity(str(ext.get("single_purpose", "")), str(o.get("single_purpose", "")))
        if sim >= SIMILARITY_WARN:
            sev: Severity = "error" if sim >= SIMILARITY_ERROR else "warn"
            add(
                "portfolio-similarity",
                f"single purpose {sim:.0%} similar to `{other}` (duplicate-functionality policy)",
                sev,
            )

    if workspace is not None:
        problems = listing.image_problems(workspace, slug)
        if problems is None:
            add("store-images", "no store images — run `tabmill assets`")
        for problem in problems or []:
            add("store-images", problem)
        draft = listing.store_dir(workspace, slug) / listing.LISTING_FILE
        urls = (hub.privacy_url(slug), hub.SUPPORT_URL)
        if not draft.exists():
            add("hub-urls", "no listing.md — run `tabmill listing` (privacy + support URLs)")
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
                    code = _http_status(url)
                    if code != 200:
                        add("hub-urls", f"{url} not live (HTTP {code or 'unreachable'})")
        if draft.exists():
            for word, n in listing.keyword_repeats(draft.read_text()).items():
                add("keyword-repeat", f"`{word}` appears {n}× in listing.md (store limit: 5)")

    built = workspace / "extensions" / slug / ".output" / "chrome-mv3" if workspace else None
    if built is None or not (built / "manifest.json").exists():
        add("not-built", "no build to inspect — run `tabmill build` (bundle rules skipped)")
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
