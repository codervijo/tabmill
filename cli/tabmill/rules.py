"""Shared rules engine (D-040). Data in `rules/lamill.yaml`; predicates here, keyed by rule id.
The idea stage's `check` and the build `check` / `advanced lint` call `evaluate()` on the same
recipe-shaped dict, so they can't disagree; only the severity per context differs.
Bundle and live-URL rules stay in `lint.py` (they need a build or the network)."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from . import catalog, extension, generate, portfolio, privacy, surfaces, targets

RULES_FILE = "rules/lamill.yaml"
Severity = Literal["error", "warn"]
Level = Literal["error", "warn", "skip"]
Context = Literal["idea", "dev", "release"]
SIMILARITY_WARN, SIMILARITY_ERROR = 0.6, 0.9
STOPWORDS = {
    "the", "a", "an", "of", "on", "for", "to", "and", "or", "as", "in", "you", "are", "page",
    "current", "web",
}  # fmt: skip


class RulesError(Exception):
    """rules/lamill.yaml missing or invalid; message names the fix."""


class Levels(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idea: Level
    dev: Level
    release: Level


class VerdictConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    weights: dict[str, int]
    go: float
    go_if: float


class RuleSet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int
    permission_allowlist: list[str]
    broad_hosts: list[str]
    brand_denylist: list[str]
    rules: dict[str, Levels]
    verdict: VerdictConfig


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: Severity
    message: str


@dataclass(frozen=True)
class Subject:
    """A recipe (from disk) or an idea-stage draft — both recipe-shaped dicts."""

    ext: dict[str, Any]
    slug: str
    tool_dir: Path
    workspace: Path | None = None


Hit = tuple[str, Severity | None]  # (message, severity override)
Predicate = Callable[[Subject, RuleSet], list[Hit]]


def load(tool_dir: Path) -> RuleSet:
    p = tool_dir / RULES_FILE
    if not p.exists():
        raise RulesError(f"{p} not found")
    try:
        rs = RuleSet.model_validate(yaml.safe_load(p.read_text()) or {})
    except (yaml.YAMLError, ValidationError) as e:
        raise RulesError(f"{p}: invalid ({e})") from e
    missing, unknown = set(PREDICATES) - set(rs.rules), set(rs.rules) - set(PREDICATES)
    if missing or unknown:
        raise RulesError(
            f"{p}: rules out of step with rules.py — missing {sorted(missing)}, "
            f"unknown {sorted(unknown)}"
        )
    return rs


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS}


def similarity(a: str, b: str) -> float:
    wa, wb = _words(a), _words(b)
    return len(wa & wb) / len(wa | wb) if wa | wb else 0.0


def _perms(ext: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    out = []
    for key in ("permissions", "optional_permissions", "host_permissions"):
        for p in ext.get(key) or []:
            if isinstance(p, dict) and p.get("name"):
                out.append((key, p))
    return out


# --- predicates ---------------------------------------------------------------------------


def _broad_host(s: Subject, rs: RuleSet) -> list[Hit]:
    return [
        (f"`{p['name']}` in {key} — prefer activeTab (longer review)", None)
        for key, p in _perms(s.ext)
        if p["name"] in rs.broad_hosts
    ]


def _fill(s: Subject, rs: RuleSet) -> list[Hit]:
    return [(f"`{f}` is still ‹FILL›", None) for f in catalog.fill_fields(s.ext)]


def _cta(s: Subject, rs: RuleSet) -> list[Hit]:
    fills = catalog.fill_fields(s.ext)
    return [
        (f"`{f}` = {s.ext.get(f)!r} is a placeholder URL", None)
        for f in extension.placeholder_fields(s.ext)
        if f not in fills
    ]


def _similarity(s: Subject, rs: RuleSet) -> list[Hit]:
    hits: list[Hit] = []
    for other in catalog.recipe_slugs(s.tool_dir):
        if other == s.slug:
            continue
        try:
            o = extension.load_file(generate.recipe_dir(s.tool_dir, other) / generate.RECIPE_FILE)
        except extension.ExtensionError:
            continue
        sim = similarity(str(s.ext.get("single_purpose", "")), str(o.get("single_purpose", "")))
        if sim >= SIMILARITY_WARN:
            hits.append(
                (
                    f"single purpose {sim:.0%} similar to `{other}` "
                    "(duplicate-functionality policy)",
                    "error" if sim >= SIMILARITY_ERROR else "warn",
                )
            )
    return hits


def _privacy(s: Subject, rs: RuleSet) -> list[Hit]:
    try:
        policy = privacy.load(s.tool_dir)
    except privacy.PolicyError as e:
        return [(str(e), "error")]
    return [
        (
            f"{gap} — the shared policy doesn't cover it: update {privacy.POLICY_FILE} "
            "(bump version), `tabmill ship`, deploy lamill.io (D-036)",
            None,
        )
        for gap in privacy.coverage(s.ext, policy)
    ]


def _justification(s: Subject, rs: RuleSet) -> list[Hit]:
    return [
        (f"`{key}.{p['name']}` has no justification", None)
        for key, p in _perms(s.ext)
        if not str(p.get("justification", "")).strip()
    ]


def _allowlist(s: Subject, rs: RuleSet) -> list[Hit]:
    allowed = set(rs.permission_allowlist) | set(rs.broad_hosts)  # broad hosts: own rule
    return [
        (f"`{p['name']}` isn't on the Lamill allowlist ({RULES_FILE}) — expect extra review", None)
        for key, p in _perms(s.ext)
        if key != "host_permissions" and p["name"] not in allowed
    ]


def _brand(s: Subject, rs: RuleSet) -> list[Hit]:
    name = str(s.ext.get("name", ""))
    found = [b for b in rs.brand_denylist if re.search(rf"\b{re.escape(b)}\b", name, re.I)]
    return (
        [
            (
                f"store name {name!r} uses brand name(s) {', '.join(found)} — impersonation policy",
                None,
            )
        ]
        if found
        else []
    )


def _name_length(s: Subject, rs: RuleSet) -> list[Hit]:
    n, limit = len(str(s.ext.get("name", ""))), targets.for_recipe(s.ext).limits.name
    return [(f"`name` is {n} chars (max {limit})", None)] if n > limit else []


def _summary_length(s: Subject, rs: RuleSet) -> list[Hit]:
    n = len(str(s.ext.get("summary", "")))
    limit = targets.for_recipe(s.ext).limits.summary
    return [(f"`summary` is {n} chars (max {limit})", None)] if n > limit else []


def _single_purpose(s: Subject, rs: RuleSet) -> list[Hit]:
    sp = str(s.ext.get("single_purpose", "")).strip()
    return [] if sp and extension.FILL_MARKER not in sp else [("no single-purpose sentence", None)]


def _template(s: Subject, rs: RuleSet) -> list[Hit]:
    t = str(s.ext.get("template", ""))
    surface = surfaces.SURFACES.get(t)
    if surface is None:
        return [
            (f"no template fits ({t or 'none proposed'}) — a new template is tabmill work", None)
        ]
    if surface.status != "implemented":
        return [(f"template {t} isn't built yet — bootstrap will refuse it", None)]
    return []


def _slot(s: Subject, rs: RuleSet) -> list[Hit]:
    view = portfolio.slots(s.tool_dir, s.workspace)
    if view.free > 0:
        return []
    return [
        (
            f"no free store slot ({len(view.published)} published + {len(view.reserved)} "
            f"reserved of {view.limit})",
            None,
        )
    ]


PREDICATES: dict[str, Predicate] = {
    "perm-broad-host": _broad_host,
    "fill-placeholder": _fill,
    "cta-placeholder": _cta,
    "portfolio-similarity": _similarity,
    "privacy-coverage": _privacy,
    "perm-justification": _justification,
    "perm-not-allowlisted": _allowlist,
    "store-name-brand": _brand,
    "name-length": _name_length,
    "summary-length": _summary_length,
    "single-purpose": _single_purpose,
    "template-implemented": _template,
    "slot-free": _slot,
}


def evaluate(subject: Subject, context: Context, ruleset: RuleSet | None = None) -> list[Finding]:
    rs = ruleset or load(subject.tool_dir)
    out: list[Finding] = []
    for rule_id, levels in rs.rules.items():
        level = getattr(levels, context)
        if level == "skip":
            continue
        for message, override in PREDICATES[rule_id](subject, rs):
            out.append(Finding(rule_id, override or level, message))
    return out
