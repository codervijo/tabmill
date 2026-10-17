"""shape_v1 (`docs/prd.md` § v2). The AI proposes the concept; code decides the slug (first
valid, unused candidate), honours the operator's `--template`, adds the permissions the
template's own code needs, and builds a recipe-shaped draft for the `check` stage."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ... import ai, brief, catalog, extension, generate, registry, rules, surfaces
from ...schema import Trigger
from ..engine import Context, Result, StageKind

PURPOSE, VERSION = "shape", 1
TemplateChoice = Literal["popup", "side-panel", "maps-overlay", "page-overlay", "none-fits"]


class ProposedPermission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    justification: str = Field(min_length=3)


class ShapeReply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    single_purpose: str = Field(min_length=10)
    template: TemplateChoice
    template_reason: str
    permissions: list[ProposedPermission] = Field(min_length=1)
    trigger: Trigger
    restricted_pages: str
    slug_candidates: list[str] = Field(min_length=1, max_length=5)
    store_name: str
    summary: str
    keywords: list[str] = Field(min_length=1, max_length=8)
    portfolio_site: str
    cta_text: str
    assumptions: list[str] = Field(default_factory=list)


def _templates() -> str:
    return "\n".join(
        f"- {s.name} ({s.status}): {s.use_for}; started from {s.trigger}"
        + (f"; its code needs {', '.join(p for p, _ in s.permissions)}" if s.permissions else "")
        for s in surfaces.SURFACES.values()
    )


def _existing(ctx: Context) -> str:
    lines = []
    for slug in catalog.recipe_slugs(ctx.tool_dir):
        try:
            ext = extension.load_file(
                generate.recipe_dir(ctx.tool_dir, slug) / generate.RECIPE_FILE
            )
        except extension.ExtensionError:
            continue
        lines.append(f"- {slug}: {ext.get('single_purpose', '')}")
    return "\n".join(lines) or "(none)"


def values(ctx: Context) -> dict[str, str]:
    clar = ctx.upstream("clarify")
    known = "\n".join(f"- {k}: {v or '(unknown)'}" for k, v in clar["known"].items())
    answered = [q for q in clar["qa"] if q["answer"]]
    open_qs = [q for q in clar["qa"] if not q["answer"]]
    idea = ctx.session.text
    proposal = "(none)"
    if ctx.session.input_kind == "brief":
        b = brief.parse(ctx.session.text).brief
        idea = b.idea or idea
        dumped = {k: v for k, v in b.proposal.model_dump().items() if v}
        proposal = json.dumps(dumped, indent=1) if dumped else "(none)"
    rs = rules.load(ctx.tool_dir)
    return {
        "idea": idea.strip(),
        "known": known,
        "answers": "\n".join(f"- {q['question']} → {q['answer']}" for q in answered) or "(none)",
        "open": "\n".join(f"- {q['question']}" for q in open_qs) or "(none)",
        "brief_proposal": proposal,
        "templates": _templates(),
        "allowlist": ", ".join(rs.permission_allowlist),
        "existing": _existing(ctx),
        "name_max": str(rs.limits.name),
        "summary_max": str(rs.limits.summary),
    }


def taken(ctx: Context) -> set[str]:
    used = set(catalog.recipe_slugs(ctx.tool_dir))
    if ctx.workspace is not None and ctx.workspace.exists():
        used |= set(registry.slugs(ctx.workspace))
    return used


def pick_slug(candidates: list[str], used: set[str], fallback: str) -> tuple[str, list[str]]:
    """First valid unused candidate; else one made from `fallback`. Returns (slug, rejected)."""
    rejected = []
    for c in candidates:
        if not catalog.SLUG_RE.match(c) or len(c) > catalog.SLUG_MAX:
            rejected.append(f"{c}: not lowercase kebab-case ≤ {catalog.SLUG_MAX} chars")
        elif c in used:
            rejected.append(f"{c}: already used")
        else:
            return c, rejected
    base = "-".join(re.findall(r"[a-z0-9]+", fallback.lower()))[: catalog.SLUG_MAX] or "idea"
    slug, n = base, 2
    while slug in used:
        slug, n = f"{base[: catalog.SLUG_MAX - 3]}-{n}", n + 1
    return slug, rejected


class Shape:
    name = PURPOSE
    kind: StageKind = "ai"
    needs: tuple[str, ...] = ("clarify",)

    def inputs(self, ctx: Context) -> dict[str, Any]:
        return {"prompt": f"{PURPOSE}_v{VERSION}", "template_hint": ctx.session.template}

    def run(self, ctx: Context) -> Result:
        prompt = ai.load_prompt(ctx.tool_dir, PURPOSE, VERSION)
        reply, call = ai.run(prompt, values(ctx), ShapeReply, ctx.raw_dir, model=ctx.ai_model)
        notes: list[str] = []
        template = str(reply.template)
        hint = ctx.session.template
        if hint and hint != template:
            notes.append(
                f"template {hint} (operator's --template) instead of the proposed {template}"
            )
            template = hint
        perms = [p.model_dump() for p in reply.permissions]
        names = {p["name"] for p in perms}
        if template in surfaces.SURFACES:
            for need in surfaces.needed_permissions(template):
                if need not in names:
                    perms.append(
                        {"name": need, "justification": surfaces.permission_reason(template, need)}
                    )
                    notes.append(f"added `{need}`: template {template} needs it")
        slug, rejected = pick_slug(reply.slug_candidates, taken(ctx), reply.store_name)
        draft = {
            "name": reply.store_name,
            "slug": slug,
            "version": "0.1.0",
            "summary": reply.summary,
            "single_purpose": reply.single_purpose,
            "template": template,
            "trigger": reply.trigger,
            "restricted_pages": reply.restricted_pages,
            "permissions": perms,
            "portfolio_site": reply.portfolio_site,
            "target_keywords": reply.keywords,
            "cta_text": reply.cta_text,
            "idea_id": ctx.session.id,
        }
        return Result(
            output={
                "proposal": reply.model_dump(),  # AI's words, kind synthesis
                "draft": draft,  # what code decided; `check` and `write` read this
                "slug_rejected": rejected,
                "notes": notes,
                "brief_proposal_used": ctx.session.input_kind == "brief",
            },
            calls=[call],
        )
