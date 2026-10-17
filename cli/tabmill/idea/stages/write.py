"""write (kind gen; `docs/prd.md` § v2). Turns the idea into `recipes/<slug>/extension.yaml`
(schema v2, with provenance) and `recipes/<slug>/idea.md`. `‹FILL›` appears only for decisions
a human must make, each with a `# why` comment. Never overwrites a recipe another idea wrote,
or one that is approved (frozen)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from ... import extension, generate, portfolio, surfaces
from ..engine import Context, IdeaError, Result, StageKind

IDEA_FILE = "idea.md"
FILL = extension.FILL_MARKER


def _v(value: Any) -> str:
    """A YAML scalar / flow value. JSON is valid YAML and quotes everything safely."""
    return json.dumps(value, ensure_ascii=False)


def recipe_text(ctx: Context, draft: dict[str, Any], provenance: list[dict[str, Any]]) -> str:
    sid, slug = ctx.session.id, draft["slug"]
    template = draft["template"]
    lines = [
        f"# Recipe for {slug} — written by `tabmill new` from ideas/{sid}/ (D-040).",
        "# Source of truth for the generated extension (ADR-0008). Fill every ‹FILL›, then",
        f"# `tabmill approve {sid}`. The reasoning is in idea.md next to this file.",
        "schema_version: 2",
        "target: chrome-mv3",
        "recipe_revision: 1  # bump to change frozen fields after `tabmill approve`",
        f"idea_id: {_v(sid)}",
        f"trigger: {_v(draft['trigger'])}",
        f"restricted_pages: {_v(draft['restricted_pages'])}",
        f"name: {_v(draft['name'])}",
        f"slug: {_v(slug)}",
        "version: 0.1.0",
        f"summary: {_v(draft['summary'])}",
        f"single_purpose: {_v(draft['single_purpose'])}",
    ]
    if template in surfaces.NAMES:
        lines.append(f"template: {_v(template)}")
    else:
        lines.append(f"template: {_v(FILL)}  # why: no built template fits — see idea.md")
    lines.append("permissions:")
    for p in draft["permissions"]:
        lines += [f"  - name: {_v(p['name'])}", f"    justification: {_v(p['justification'])}"]
    lines += [
        "optional_permissions: []",
        "dependencies: {}        # runtime npm deps — each needs a DECISIONS.md row first",
        "dev_dependencies: {}",
        "remote_code: false",
        f"portfolio_site: {_v(draft['portfolio_site'])}",
        'landing_page_url: ""',
        f"target_keywords: {_v(draft['target_keywords'])}",
        f"cta_text: {_v(draft['cta_text'])}",
        f"cta_url: {_v(FILL)}  # why: the CTA destination is your call; no page yet → "
        "https://<name>.example/<path> (D-015)",
        f"utm_campaign: {_v(slug)}",
        f'store_category: {_v(FILL)}  # why: picked in the dashboard at "Add new item"; '
        "no official list",
        "analytics: false",
        "provenance:  # where each fact came from (kind: real · external · user · "
        "external_suggestion · synthesis · missing)",
    ]
    lines += [f"  - {_v(f)}" for f in provenance]
    return "\n".join(lines) + "\n"


def _md_table(facts: list[dict[str, Any]]) -> list[str]:
    out = ["| kind | claim | value | source | date |", "|---|---|---|---|---|"]
    for f in facts:
        cells = [
            f["kind"],
            f["claim"],
            "" if f["value"] is None else str(f["value"]),
            f["source"],
            f.get("date") or "",
        ]
        out.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
    return out


def idea_md(ctx: Context, out: dict[str, dict[str, Any]]) -> str:
    clar, shape, ev, chk, ver = (
        out[k] for k in ("clarify", "shape", "evidence", "check", "verdict")
    )
    d = shape["draft"]
    sid = ctx.session.id
    lines = [
        f"# {d['name']} — idea {sid}",
        "",
        f"Written by `tabmill new` on {ctx.today or date.today().isoformat()} (D-040). "
        "Evidence kinds: real (fetched by tabmill) · external (sourced row) · user (your "
        "answers) · external_suggestion (brief) · synthesis (AI guess / unsourced) · missing.",
        "",
        "## Idea",
        "",
        ctx.session.text.strip()
        if ctx.session.input_kind == "idea"
        else f"Tabmill brief — verbatim in `ideas/{sid}/brief.md`.",
        "",
        "## Questions and answers",
        "",
    ]
    for q in clar["qa"]:
        lines.append(f"- **{q['question']}** {q['answer'] or '_(open — assumed below)_'}")
    if not clar["qa"]:
        lines.append("- (none asked)")
    lines += [
        "",
        "## Concept",
        "",
        f"- Single purpose: {d['single_purpose']}",
        f"- Store name: {d['name']} · slug `{d['slug']}`",
        f"- Summary: {d['summary']}",
        f"- Template: {d['template']} — {shape['proposal'].get('template_reason', '')}",
        f"- Trigger: {d['trigger']} · restricted pages: {d['restricted_pages']}",
        "- Permissions: "
        + "; ".join(f"`{p['name']}` — {p['justification']}" for p in d["permissions"]),
        f"- Keywords: {', '.join(d['target_keywords'])}",
        f"- Site / CTA: {d['portfolio_site']} — {d['cta_text']}",
    ]
    for note in shape["notes"]:
        lines.append(f"- Code decided: {note}")
    assumptions = shape["proposal"].get("assumptions") or []
    if assumptions:
        lines += ["", "### Assumptions", ""] + [f"- {a}" for a in assumptions]
    lines += ["", "## Evidence", ""]
    lines += [
        f"- {p['name']}: {p['status']}" + (f" — {p['detail']}" if p["detail"] else "")
        for p in ev["providers"]
    ]
    lines += [""] + _md_table(ev["facts"])
    lines += ["", "## Check", ""]
    lines += [f"- {f['severity']}: {f['rule']} — {f['message']}" for f in chk["findings"]] or [
        "- no findings"
    ]
    s = chk["slots"]
    lines.append(f"- slots: {s['free']} free of {s['limit']}")
    lines += ["", f"## Verdict: {ver['verdict']} (score {ver['weighted']})", ""]
    lines += [f"- {w}" for w in ver["why"]]
    for dim, sc in ver["scores"].items():
        lines.append(f"- {dim}: {sc['score']}/10 — {sc['reason']}")
    if ver["needs_evidence"]:
        lines += ["", "### Evidence that would change this", ""]
        lines += [f"- {n}" for n in ver["needs_evidence"]]
    lines += ["", "## Risks", ""] + ([f"- {r}" for r in ver["risks"]] or ["- (none listed)"])
    nxt = (
        f"fill the ‹FILL› fields in recipes/{d['slug']}/extension.yaml, then "
        f"`tabmill approve {sid}`"
    )
    if ver["verdict"] == "NO-GO":
        nxt = f'`tabmill approve {sid} --override "<reason>"` only if you disagree'
    lines += ["", "## Next", "", f"- {nxt}", ""]
    return "\n".join(lines)


def provenance(out: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return list(out["clarify"].get("facts", [])) + list(out["evidence"].get("facts", []))


def guard(tool_dir: Path, slug: str, idea_id: str) -> None:
    path = generate.recipe_dir(tool_dir, slug) / generate.RECIPE_FILE
    if not path.exists():
        return
    try:
        existing = extension.load_file(path)
    except extension.ExtensionError:
        existing = {}
    if existing.get("idea_id") != idea_id:
        raise IdeaError(
            f"recipes/{slug}/ exists and wasn't written by idea {idea_id} — "
            f"re-run `tabmill new shape {idea_id}` for another slug"
        )
    if portfolio.is_approved(tool_dir, slug):
        raise IdeaError(
            f"recipes/{slug}/ is approved (frozen) — edit it by hand, bump "
            f"recipe_revision and re-run `tabmill approve {idea_id}`"
        )


class Write:
    name = "write"
    kind: StageKind = "gen"
    needs: tuple[str, ...] = ("clarify", "shape", "evidence", "check", "verdict")

    def inputs(self, ctx: Context) -> dict[str, Any]:
        return {"format": 1}

    def run(self, ctx: Context) -> Result:
        out = {k: ctx.upstream(k) for k in self.needs}
        draft = out["shape"]["draft"]
        slug = str(draft["slug"])
        guard(ctx.tool_dir, slug, ctx.session.id)
        text = recipe_text(ctx, draft, provenance(out))
        target = generate.recipe_dir(ctx.tool_dir, slug)
        target.mkdir(parents=True, exist_ok=True)
        (target / generate.RECIPE_FILE).write_text(text)
        (target / IDEA_FILE).write_text(idea_md(ctx, out))
        ext = extension.load_file(target / generate.RECIPE_FILE)
        errors = [e for e in extension.validate(ext, slug)]
        item = portfolio.Item(approval="proposed", idea_id=ctx.session.id)
        return Result(
            output={
                "slug": slug,
                "recipe": f"recipes/{slug}/{generate.RECIPE_FILE}",
                "idea_md": f"recipes/{slug}/{IDEA_FILE}",
                "schema_errors": errors,
                "fill": [k for k, v in ext.items() if isinstance(v, str) and FILL in v],
                "portfolio_item": item.model_dump(exclude_defaults=True),
            },
            calls=[],
        )
