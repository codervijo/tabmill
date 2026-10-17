"""`tabmill` commands — see `tabmill --help` (README § Commands).

Top level (D-034, D-038, D-040): idea stage (`new`, v2.B on) → build stage (`bootstrap` → `try` →
`check` → `ship` → `publish`) → portfolio (`status`, `slots`, `templates`, `doctor`).
`settings` holds setup; `advanced` holds the single steps those commands run."""

from __future__ import annotations

import dataclasses
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import typer
from rich.markup import escape
from rich.table import Table

from . import (
    ai,
    apikeys,
    brief,
    catalog,
    config,
    cws,
    extension,
    generate,
    hub,
    landing,
    lifecycle,
    lint,
    listing,
    output,
    portfolio,
    preflight,
    privacy,
    recipe_v2,
    registry,
    rules,
    surfaces,
    sync,
    workspace,
)
from .constants import ENV_WORKSPACE
from .idea import approve as approve_mod
from .idea import engine, evidence
from .idea import stages as idea_stages

app = typer.Typer(
    help="Create, release, and track Lamill's Chrome MV3 extensions.",
    no_args_is_help=True,
    add_completion=False,
)
settings_app = typer.Typer(help="Setup: workspace, credentials, checks.", no_args_is_help=True)
skills_app = typer.Typer(help="Tabmill-managed workspace files.", no_args_is_help=True)
apikeys_app = typer.Typer(help="Credentials in tabmill/tabmill.env.", no_args_is_help=True)
settings_app.add_typer(skills_app, name="skills")
settings_app.add_typer(apikeys_app, name="apikeys")
advanced_app = typer.Typer(help="Single steps the commands above run.", no_args_is_help=True)
brief_app = typer.Typer(help="Tabmill briefs (the paste format, D-040).", no_args_is_help=True)
app.add_typer(brief_app, name="brief")
ideas_app = typer.Typer(help="Idea sessions: list, show, compare (D-040).")
app.add_typer(ideas_app, name="ideas")
evidence_app = typer.Typer(help="Evidence for an idea (D-040).", no_args_is_help=True)
app.add_typer(evidence_app, name="evidence")
app.add_typer(settings_app, name="settings")
app.add_typer(advanced_app, name="advanced")


def _preflight(kind: str) -> None:
    """Fail fast, before any work, when a prerequisite of this command is missing."""
    failed = False
    for c in preflight.run(preflight.NEEDS[kind]):
        if c.status == "fail":
            output.fail(f"preflight {c.name}: {c.detail}")
            failed = True
        elif c.status == "warn":
            output.skip(f"preflight {c.name}: {c.detail}")
    if failed:
        raise typer.Exit(1)


def _load(workspace_override: Path | None = None) -> config.Config:
    try:
        cfg = config.load(require_workspace=workspace_override is None)
    except config.ConfigError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    if workspace_override is not None:
        cfg = dataclasses.replace(cfg, workspace=workspace_override.expanduser().resolve())
    return cfg


def _sync(cfg: config.Config, force: bool) -> None:
    try:
        wanted = workspace.managed_files(cfg)
    except generate.RecipeError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    result = sync.sync(cfg.workspace, wanted, force=force)
    sync.report(result, force=force)
    if result.refused and not force:
        raise typer.Exit(1)


@settings_app.command()
def init(
    directory: Path | None = typer.Argument(  # noqa: B008 — typer's documented idiom
        None, help=f"Workspace dir (default: ${ENV_WORKSPACE} / tabmill.config.json)."
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite edited installed skills."),
) -> None:
    """Create or complete a workspace: skeleton, skills, CI, tool pin. Never overwrites files."""
    cfg = _load(directory)
    try:
        configured: Path | None = config.load().workspace
    except config.ConfigError:
        configured = None
    if configured is not None and configured != cfg.workspace:
        output.skip(f"${ENV_WORKSPACE} points to {configured}, not {cfg.workspace}")
    output.ok(f"workspace: {cfg.workspace}")
    if not workspace.scaffold(cfg):
        raise typer.Exit(1)
    _sync(cfg, force)


@skills_app.command("sync")
def skills_sync(
    force: bool = typer.Option(False, "--force", help="Discard edits to installed copies."),
) -> None:
    """Update tabmill-managed workspace files: skills, CLAUDE.md, Makefiles, pnpm workspace, CI."""
    cfg = _load()
    if not cfg.workspace.exists():
        output.fail(f"workspace {cfg.workspace} does not exist — run `tabmill settings init` first")
        raise typer.Exit(1)
    _sync(cfg, force)


def _recipe(cfg: config.Config, slug: str) -> dict[str, object]:
    try:
        ext = generate.load_recipe(cfg.tool_dir, slug)
    except generate.RecipeError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    output.ok(f"recipes/{slug}/extension.yaml: valid")
    _approval_gate(cfg, slug, ext)
    for field in extension.placeholder_fields(ext):
        output.skip(f"{field}: placeholder URL — fine for dev, blocks release (D-015)")
    return ext


STAGE_WORDS = ("clarify", "shape", "evidence", "check", "verdict", "write", "validate", "trends")


def _tty() -> bool:
    return sys.stdin.isatty()


def _ask_user(q: engine.Question) -> str:
    output.console.print(f"\n[bold]{escape(q.text)}[/bold]")
    for i, choice in enumerate(q.choices, 1):
        output.console.print(f"  {i}. {escape(choice)}")
    hint = "number or your own words" if q.choices else "your answer"
    raw: str = typer.prompt(f"  {hint} (Enter = skip)", default="", show_default=False)
    raw = raw.strip()
    if raw.isdigit() and 1 <= int(raw) <= len(q.choices):
        return q.choices[int(raw) - 1]
    return raw


def _run_idea(
    cfg: config.Config,
    session: engine.Session,
    *,
    only: str | None,
    non_interactive: bool,
    apply: bool = False,
) -> None:
    interactive = not non_interactive and _tty()
    if not non_interactive and not interactive:
        output.skip("no terminal to ask in — questions are recorded as open")
    ctx = engine.Context(
        cfg.tool_dir,
        session,
        _ask_user if interactive else None,
        ai_model=cfg.ai_model,
        workspace=cfg.workspace if cfg.workspace.exists() else None,
    )

    def step(name: str, what: str) -> None:
        if what == "recorded":
            output.ok(f"{name}: recorded, skipping (re-run: `tabmill new {name} {session.id}`)")
        else:
            output.ok(f"{name}: {what}")

    ai.LEDGER.clear()
    try:
        records = engine.run(ctx, idea_stages.REGISTERED, only=only, on_step=step)
    except ai.AITransient as e:
        output.skip(str(e))
        output.console.print(f"  {ai.spent()}")
        raise typer.Exit(1) from e
    except (ai.AIError, engine.IdeaError) as e:
        output.fail(str(e))
        output.console.print(f"  {ai.spent()}")
        raise typer.Exit(1) from e
    for rec in records:
        if only is None or rec.stage == only:
            _stage_summary(rec)
    stale = [r.stage for r in records if r.stale]
    if stale:
        output.skip(f"stale: {', '.join(stale)} — `tabmill new --resume {session.id}` re-runs them")
    output.console.print(f"  idea: {engine.IDEAS_DIR}/{session.id}/")
    written = next((r for r in records if r.stage == "write" and not r.stale), None)
    if written is not None:
        _portfolio_item(cfg, written.output, apply)
        _next_after_write(session.id, written.output, records)
    later = [n for n in engine.ORDER if n in engine.ARRIVES]
    if later:
        output.console.print(f"  next: {later[0]} arrives in {engine.ARRIVES[later[0]]}")
    output.console.print(f"  {ai.spent()}")  # always the last line (AI_AGENTS.md)


def _portfolio_item(cfg: config.Config, out: dict[str, Any], apply: bool) -> None:
    """Print the proposed portfolio.yaml item as a diff; write it only with --apply."""
    slug, item = out["slug"], out["portfolio_item"]
    data = _portfolio(cfg)
    if slug in data.items:
        output.ok(
            f"{portfolio.PORTFOLIO_FILE}: {slug} already listed ({data.items[slug].approval})"
        )
        return
    output.console.print(f"  {portfolio.PORTFOLIO_FILE}:")
    output.console.print(f"  [green]+ {escape(slug)}: {escape(json.dumps(item))}[/green]")
    if not apply:
        output.skip(f"{portfolio.PORTFOLIO_FILE}: not written — add --apply (or `tabmill approve`)")
        return
    data.items[slug] = portfolio.Item.model_validate(item)
    portfolio.write(cfg.tool_dir, data)
    output.ok(f"{portfolio.PORTFOLIO_FILE}: {slug} added (proposed)")


def _next_after_write(idea_id: str, out: dict[str, Any], records: list[engine.StageRecord]) -> None:
    verdict = next((r.output for r in records if r.stage == "verdict"), {})
    if out["schema_errors"]:
        for e in out["schema_errors"]:
            output.skip(f"write: {out['recipe']}: {e}")
    fill = ", ".join(out["fill"])
    if verdict.get("verdict") == "NO-GO":
        output.console.print(
            f'  next: NO-GO — `tabmill approve {idea_id} --override "<reason>"` '
            "only if you disagree"
        )
    elif fill:
        output.console.print(
            f"  next: fill {fill} in {out['recipe']}, then tabmill approve {idea_id}"
        )
    else:
        output.console.print(f"  next: tabmill approve {idea_id}")


def _research(kind: str, keywords: list[str]) -> None:
    """`new validate|trends <keywords>`: demand research via lamill, printed, not saved."""
    if not keywords:
        output.fail(f'give keywords: tabmill new {kind} "word counter" "count words"')
        raise typer.Exit(1)
    lamill = evidence.Lamill()
    ai.LEDGER.clear()
    runs = (
        [lamill.validate(" ".join(keywords))]
        if kind == "validate"
        else [lamill.trends(k) for k in keywords]
    )
    for r in runs:
        (output.ok if r.status == "ok" else output.skip)(f"{r.name}: {r.status} — {r.detail}")
        for f in r.facts:
            _fact_line(f.model_dump())
    output.console.print(f"  {ai.spent()}")
    if all(r.status == "failed" for r in runs):
        raise typer.Exit(1)


def _fact_line(f: dict[str, object]) -> None:
    mark = output.ok if f["kind"] in ("real", "external") else output.skip
    when = f" · {f['date']}" if f.get("date") else ""
    mark(f"[{f['kind']}] {f['claim']} = {f['value']} · {f['source']}{when}")


def _add_evidence(idea_path: Path, src: Path) -> Path:
    parsed, _ = brief.parse_evidence(src.read_text())
    for problem in parsed.problems:
        output.fail(f"{src.name}: {problem}")
    if not parsed.present:
        raise typer.Exit(1)
    dest = evidence.add_file(idea_path, src)
    rows = len(parsed.brief.demand) + len(parsed.brief.competition)
    output.ok(f"evidence: {src.name} → {dest.relative_to(idea_path.parent.parent)} ({rows} rows)")
    return dest


@evidence_app.command("add")
def evidence_add(
    idea_id: str = typer.Argument(..., help="Idea id (see ideas/)."),
    file: Path = typer.Argument(..., help="Evidence file: front matter + tables."),  # noqa: B008
) -> None:
    """Add an evidence file to an idea; the evidence stage re-runs on `new --resume`."""
    cfg = _load()
    try:
        engine.load(cfg.tool_dir, idea_id)
    except engine.IdeaError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    if not file.is_file():
        output.fail(f"{file}: no such file")
        raise typer.Exit(1)
    _add_evidence(engine.idea_dir(cfg.tool_dir, idea_id), file)
    output.console.print(f"  next: tabmill new --resume {idea_id}")


def _stage_summary(rec: engine.StageRecord) -> None:
    out = rec.output
    if rec.stage == "clarify":
        answered = len(out["qa"]) - len(out["open"])
        line = f"clarify: {answered} answered, {len(out['open'])} open"
        (output.skip if out["open"] else output.ok)(
            line + (" — carried as assumptions" if out["open"] else "")
        )
    elif rec.stage == "shape":
        d = out["draft"]
        perms = ", ".join(p["name"] for p in d["permissions"])
        output.ok(f"shape: {d['slug']} · {d['template']} · {d['name']!r} · {perms}")
        output.console.print(f"    {escape(d['single_purpose'])}")
        for note in out["notes"]:
            output.skip(f"shape: {note}")
        for r in out["slug_rejected"]:
            output.skip(f"shape: slug {r}")
    elif rec.stage == "evidence":
        for p in out["providers"]:
            mark = output.ok if p["status"] == "ok" else output.skip
            mark(
                f"evidence: {p['name']}: {p['status']}"
                + (f" — {p['detail']}" if p["detail"] else "")
            )
        kinds = ", ".join(f"{n} {k}" for k, n in sorted(out["kinds"].items()))
        output.ok(f"evidence: {len(out['facts'])} facts ({kinds})")
        gaps = [str(f["claim"]) for f in out["facts"] if f["kind"] == "missing"]
        demand = [c.split(": ", 1)[1] for c in gaps if c.startswith("demand (real or sourced): ")]
        if demand:
            output.skip(f"evidence: no real or sourced demand for {', '.join(demand)}")
        others = [c for c in gaps if not c.startswith(("demand (real", "Google Trends interest:"))]
        for c in others:
            output.skip(f"evidence: missing — {c}")
    elif rec.stage == "verdict":
        line = f"verdict: {out['verdict']} · score {out['weighted']}"
        {"GO": output.ok, "GO-IF": output.skip, "NO-GO": output.fail}[out["verdict"]](line)
        for dim, sc in out["scores"].items():
            output.console.print(f"    {dim} {sc['score']}/10 — {escape(sc['reason'])}")
        for w in out["why"][1:]:
            output.skip(f"verdict: {w}")
    elif rec.stage == "write":
        output.ok(f"write: {out['recipe']} + {out['idea_md']}")
    elif rec.stage == "check":
        for f in out["findings"]:
            (output.fail if f["severity"] == "error" else output.skip)(
                f"check: {f['rule']}: {f['message']}"
            )
        s = out["slots"]
        line = (
            f"check: {out['errors']} error(s), {out['warnings']} warning(s) · "
            f"slots {s['free']} free of {s['limit']}"
        )
        (output.fail if out["errors"] else output.ok)(line)


def _approval_gate(cfg: config.Config, slug: str, ext: dict[str, object]) -> None:
    """Human gate 1 (D-040): an idea-stage recipe builds only once approved, and only while
    its frozen fields match what was approved."""
    try:
        idea_id = str(ext.get("idea_id") or "")
        if idea_id and not portfolio.is_approved(cfg.tool_dir, slug):
            output.fail(
                f"recipes/{slug} came from idea {idea_id} and isn't approved — "
                f"`tabmill approve {idea_id}`"
            )
            raise typer.Exit(1)
        why = portfolio.drift(cfg.tool_dir, slug, ext)
    except portfolio.PortfolioError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    if why:
        output.fail(why)
        raise typer.Exit(1)


@app.command()
def new(
    idea: list[str] = typer.Argument(  # noqa: B008 — typer's documented idiom
        None,
        help='A rough idea in words, e.g. "count words on any page"; or a stage name '
        "(clarify) and an idea id to re-run it.",
    ),
    resume: str = typer.Option(
        "", "--resume", help="Continue an idea from its first missing or stale stage."
    ),
    non_interactive: bool = typer.Option(
        False, "--non-interactive", help="Ask nothing; questions are recorded as open."
    ),
    apply: bool = typer.Option(
        False, "--apply", help="Also add the proposed item to portfolio.yaml after write."
    ),
    template: str = typer.Option(
        "", "--template", "-t", help="Surface template hint (or for a new recipe: popup)."
    ),
    paste: bool = typer.Option(
        False, "--paste", help="Paste a Tabmill brief or idea; end with a line `.` or Ctrl-D."
    ),
    evidence_files: list[Path] = typer.Option(  # noqa: B008 — typer's documented idiom
        [], "--evidence", help="Evidence file (Demand / Store competition tables); repeatable."
    ),
    brief_file: Path | None = typer.Option(  # noqa: B008 — typer's documented idiom
        None, "--brief", help="Read a Tabmill brief (or idea) from a file."
    ),
    force: bool = typer.Option(False, "--force", help="Discard edits to managed files."),
) -> None:
    """Start from a rough idea or a Tabmill brief: clarify → … → approve (D-040).
    `-` reads stdin. `new <slug>` = deprecated alias for `bootstrap`."""
    words = idea or []
    cfg = _load()
    if words and words[0] in STAGE_WORDS:
        name, rest = words[0], words[1:]
        if name in ("validate", "trends"):
            _research(name, rest)
            return
        if name not in {s.name for s in idea_stages.REGISTERED}:
            output.skip(f"`new {name}` arrives in {engine.ARRIVES.get(name, 'v2.E')}")
            raise typer.Exit(1)
        try:
            session = engine.load(cfg.tool_dir, rest[0] if rest else engine.latest(cfg.tool_dir))
        except engine.IdeaError as e:
            output.fail(str(e))
            raise typer.Exit(1) from e
        _run_idea(cfg, session, only=name, non_interactive=non_interactive, apply=apply)
        return
    if resume:
        try:
            session = engine.load(cfg.tool_dir, resume)
        except engine.IdeaError as e:
            output.fail(str(e))
            raise typer.Exit(1) from e
        _run_idea(cfg, session, only=None, non_interactive=non_interactive, apply=apply)
        return
    text = _idea_input(words, paste, brief_file)
    if text is not None:
        _start_idea(cfg, text, non_interactive, template, evidence_files, apply)
        return
    if len(words) == 1 and catalog.SLUG_RE.match(words[0]):
        # Through v2 a single slug keeps today's path (D-040); removed in v3.A.
        output.skip(
            f"`tabmill new {words[0]}` is deprecated — use `tabmill bootstrap {words[0]}` "
            "(removed in v3.A)"
        )
        _bootstrap(words[0], template, force)
        return
    _start_idea(cfg, " ".join(words), non_interactive, template, evidence_files, apply)


def _read_pasted() -> str:
    """Multi-line input until EOF or a line that is just `.`."""
    lines = []
    for line in sys.stdin:
        if line.rstrip("\n") == ".":
            break
        lines.append(line)
    return "".join(lines)


def _idea_input(words: list[str], paste: bool, brief_file: Path | None) -> str | None:
    """Text from --brief / --paste / `-` / a bare `new` on a terminal; None = use the words."""
    sources = sum([paste, brief_file is not None, words == ["-"]])
    if sources > 1 or (sources and words and words != ["-"]):
        output.fail("give the idea one way: words, `-`, --paste, or --brief <file>")
        raise typer.Exit(1)
    if brief_file is not None:
        if not brief_file.is_file():
            output.fail(f"{brief_file}: no such file")
            raise typer.Exit(1)
        return brief_file.read_text()
    if words == ["-"]:
        return sys.stdin.read()
    if paste or not words:
        if not paste and not _tty():
            output.fail(
                'describe the idea: tabmill new "count words on any page" '
                "(or pipe a brief: tabmill new -)"
            )
            raise typer.Exit(1)
        if _tty():
            output.console.print(
                "Paste a Tabmill brief or describe the idea. End with a line `.` or Ctrl-D."
            )
        return _read_pasted()
    return None


def _report_brief(text: str) -> bool:
    """Print what parsed, what didn't and what was downgraded. True if any section failed."""
    parsed = brief.parse(text)
    for name in parsed.present:
        if not any(p.section.endswith(name.split(" › ")[-1]) for p in parsed.problems):
            output.ok(f"brief: {name}")
    for problem in parsed.problems:
        output.fail(f"brief: {problem}")
    for row in brief.downgraded(parsed):
        output.skip(f"brief: {row} has no source URL — downgraded to synthesis")
    for gap in brief.missing(parsed):
        output.skip(f"brief: missing {gap}")
    return bool(parsed.problems)


def _start_idea(
    cfg: config.Config,
    text: str,
    non_interactive: bool,
    template: str,
    evidence_files: list[Path] | None = None,
    apply: bool = False,
) -> None:
    for f in evidence_files or []:
        if not f.is_file():
            output.fail(f"{f}: no such file")
            raise typer.Exit(1)
    try:
        session = engine.create(
            cfg.tool_dir, text, non_interactive=non_interactive, template=template
        )
    except engine.IdeaError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    if session.input_kind == "brief":
        output.ok(
            f"idea {session.id}: brief saved verbatim to "
            f"{engine.IDEAS_DIR}/{session.id}/{engine.BRIEF_FILE}"
        )
        if _report_brief(text):
            output.skip("sections that failed are kept as gaps — clarify asks about them")
    else:
        output.ok(f"idea {session.id}: saved")
    for f in evidence_files or []:
        _add_evidence(engine.idea_dir(cfg.tool_dir, session.id), f)
    _run_idea(cfg, session, only=None, non_interactive=non_interactive, apply=apply)


@brief_app.command("check")
def brief_check(
    file: Path = typer.Argument(..., help="The brief (Markdown with tabmill_brief front matter)."),  # noqa: B008
) -> None:
    """Validate a Tabmill brief: what parsed, what's broken (with line), what's missing."""
    if not file.is_file():
        output.fail(f"{file}: no such file")
        raise typer.Exit(1)
    text = file.read_text()
    if not brief.is_brief(text):
        output.fail(
            f"{file}: not a Tabmill brief — it starts with `---` front matter holding "
            "`tabmill_brief: 1`"
        )
        raise typer.Exit(1)
    if _report_brief(text):
        raise typer.Exit(1)
    output.ok(f"{file}: valid brief")


@app.command()
def approve(
    idea_id: str = typer.Argument(..., help="Idea id (see `tabmill ideas`)."),
    override: str = typer.Option(
        "", "--override", help="Approve a NO-GO anyway; the reason is recorded."
    ),
) -> None:
    """Human gate 1: freeze the idea's recipe and reserve a store slot (terminal only)."""
    cfg = _load()
    ws = cfg.workspace if cfg.workspace.exists() else None
    try:
        plan = approve_mod.prepare(cfg.tool_dir, ws, idea_id, override)
    except (approve_mod.ApproveError, engine.IdeaError, portfolio.PortfolioError) as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    v = plan.verdict
    mark = {"GO": output.ok, "GO-IF": output.skip, "NO-GO": output.fail}[v["verdict"]]
    mark(f"verdict: {v['verdict']} · score {v['weighted']}")
    for w in v["why"][1:]:
        output.skip(w)
    for w in plan.warnings:
        output.skip(f"rule: {w}")
    for f in plan.fill:
        output.skip(f"‹FILL›: {f} — fill it before `tabmill ship`")
    if override:
        output.skip(f"override: {override}")
    what = "re-approve" if plan.renewal else "approve"
    output.console.print(
        f"  {what} recipes/{plan.slug} at recipe_revision {plan.item.recipe_revision}: "
        f"freeze it{' and reserve a store slot' if plan.item.slot == 'reserved' else ''}"
    )
    if not _tty():
        output.fail("approve is a human gate — run it in a terminal")
        raise typer.Exit(1)
    if not typer.confirm("  Approve?", default=False):
        output.skip("not approved")
        raise typer.Exit(1)
    approve_mod.apply(cfg.tool_dir, plan)
    output.ok(
        f"{portfolio.PORTFOLIO_FILE}: {plan.slug} {plan.item.approval}, frozen"
        + (", slot reserved" if plan.item.slot == "reserved" else "")
    )
    output.console.print(f"  next: tabmill bootstrap {plan.slug}")


@ideas_app.callback(invoke_without_command=True)
def ideas_default(ctx: typer.Context) -> None:
    """Idea sessions in ideas/: progress, verdict, evidence mix."""
    if ctx.invoked_subcommand is None:
        ideas_list()


@ideas_app.command("list")
def ideas_list() -> None:
    """Every idea: stage reached, slug, verdict and score."""
    cfg = _load()
    found = engine.ids(cfg.tool_dir)
    if not found:
        output.skip('no ideas yet — tabmill new "<idea>"')
        return
    table = Table(show_edge=False, pad_edge=False, box=None, header_style="bold")
    for col in ("idea", "input", "reached", "slug", "verdict", "score", "AI cost"):
        table.add_column(col, overflow="fold")
    for i in found:
        s = engine.summary(cfg.tool_dir, i)
        reached = s["done"][-1] if s["done"] else "—"
        if s["stale"]:
            reached += f" (stale: {', '.join(s['stale'])})"
        cost = "unknown" if s["cost_usd"] is None else f"${s['cost_usd']:.2f}"
        table.add_row(
            i,
            s["input"],
            reached,
            s["slug"] or "—",
            s["verdict"] or "—",
            "—" if s["score"] is None else str(s["score"]),
            cost,
        )
    output.console.print(table)


@ideas_app.command("show")
def ideas_show(idea_id: str = typer.Argument(..., help="Idea id.")) -> None:
    """The idea's idea.md (after write), else its stage summaries."""
    cfg = _load()
    try:
        engine.load(cfg.tool_dir, idea_id)
    except engine.IdeaError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    s = engine.summary(cfg.tool_dir, idea_id)
    md = generate.recipe_dir(cfg.tool_dir, s["slug"]) / "idea.md" if s["slug"] else None
    if md is not None and md.exists() and "write" in s["done"]:
        output.console.print(escape(md.read_text()))
        return
    for name in engine.ORDER:
        rec = engine.read_stage(cfg.tool_dir, idea_id, name)
        if rec is not None:
            _stage_summary(rec)


@ideas_app.command("compare")
def ideas_compare(
    idea_ids: list[str] = typer.Argument(..., help="Two or more idea ids."),  # noqa: B008
) -> None:
    """Side by side: verdict, score, the five rubric scores, evidence mix, check errors."""
    cfg = _load()
    if len(idea_ids) < 2:
        output.fail("compare needs two or more idea ids")
        raise typer.Exit(1)
    try:
        rows = [engine.summary(cfg.tool_dir, i) for i in idea_ids]
    except engine.IdeaError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    table = Table(show_edge=False, pad_edge=False, box=None, header_style="bold")
    table.add_column("")
    for r in rows:
        table.add_column(r["slug"] or r["id"], overflow="fold")

    def cell(r: dict[str, Any], key: str) -> str:
        v = r[key]
        return "—" if v in (None, "", {}) else str(v)

    table.add_row("idea", *[r["id"] for r in rows])
    table.add_row("verdict", *[cell(r, "verdict") for r in rows])
    table.add_row("score", *[cell(r, "score") for r in rows])
    for dim in ("reach", "outrate", "audience", "risk", "effort"):
        table.add_row(dim, *[str(r["scores"].get(dim, "—")) for r in rows])
    for kind in ("real", "external", "synthesis", "missing"):
        table.add_row(f"facts: {kind}", *[str(r["kinds"].get(kind, 0)) for r in rows])
    table.add_row("check errors", *[cell(r, "errors") for r in rows])
    output.console.print(table)


@app.command()
def bootstrap(
    slug: str = typer.Argument(..., help="Extension slug, e.g. jwt-inspector."),
    template: str = typer.Option(
        "", "--template", "-t", help="Surface template for a new recipe (default: popup)."
    ),
    force: bool = typer.Option(False, "--force", help="Discard edits to managed files."),
) -> None:
    """Generate the extension from its recipe (no recipe yet: write a starter recipe)."""
    _bootstrap(slug, template, force)


def _bootstrap(slug: str, template: str, force: bool) -> None:
    cfg, ws = _config_and_workspace()
    if not (generate.recipe_dir(cfg.tool_dir, slug) / generate.RECIPE_FILE).exists():
        _create(cfg, ws, slug, template or "popup")
        return
    if template:
        output.skip(f"recipes/{slug}/ exists — --template ignored (it's set in the recipe)")
    if ws is None:
        output.fail("no workspace to generate into — run `tabmill settings init` first")
        raise typer.Exit(1)
    ext = _recipe(cfg, slug)
    surface = surfaces.SURFACES[str(ext["template"])]
    if surface.status != "implemented":
        output.fail(f"template {surface.name} isn't built yet — pick another in the recipe")
        raise typer.Exit(1)
    changed = registry.upsert(
        cfg.workspace, slug, {"version": str(ext["version"]), "status": "generated"}
    )
    output.ok(f"registry.json: {slug} {'registered' if changed else 'already registered'}")
    _sync(cfg, force)
    output.console.print(f"  next: tabmill try {slug}")


@advanced_app.command()
def build(
    slug: str = typer.Argument(..., help="Extension slug."),
) -> None:
    """Regenerate managed files, then build with WXT in the builder docker (never on the host)."""
    cfg = _load()
    if slug not in registry.slugs(cfg.workspace):
        output.fail(f"{slug} is not in registry.json — run `tabmill bootstrap {slug}` first")
        raise typer.Exit(1)
    _recipe(cfg, slug)
    _sync(cfg, force=False)
    _preflight("docker")
    rc = subprocess.run(
        ["make", "--no-print-directory", "in-docker-build", f"EXT={slug}"], cwd=cfg.workspace
    ).returncode
    if rc != 0:
        output.fail(f"WXT build failed (exit {rc})")
        raise typer.Exit(rc)
    output.ok(f"built: extensions/{slug}/.output/chrome-mv3/")


def _config_and_workspace() -> tuple[config.Config, Path | None]:
    """list/create work from recipes alone; the workspace is optional for them."""
    try:
        cfg = config.load()
    except config.ConfigError:
        output.skip(f"no workspace configured (${ENV_WORKSPACE}) — recipes only")
        return config.load(require_workspace=False), None
    if not cfg.workspace.exists():
        output.skip(f"workspace {cfg.workspace} not found — recipes only")
        return cfg, None
    return cfg, cfg.workspace


STATUS_STYLE = {
    "built": "[green]✓ built[/green]",
    "generated": "[green]✓ generated[/green]",
    "recipe": "[yellow]↷ recipe only[/yellow]",
    "orphan": "[red]✗ orphan[/red]",
    "invalid": "[red]✗ invalid[/red]",
}


@advanced_app.command("list")
def list_(
    as_json: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """All extensions: recipes in tabmill + what's generated/built in the workspace."""
    cfg, ws = _config_and_workspace()
    rows = catalog.rows(cfg.tool_dir, ws)
    if as_json:
        typer.echo(json.dumps([r.to_dict() for r in rows], indent=2))
        return
    if not rows:
        output.skip("no extensions yet — start one with `tabmill bootstrap <slug>`")
        return
    table = Table(show_edge=False, pad_edge=False, box=None, header_style="bold")
    for col in ("slug", "status", "version", "template", "store id"):
        table.add_column(col, no_wrap=True)
    table.add_column("needs filling", overflow="fold")
    for r in rows:
        todo = r.error or " ".join(r.placeholders)
        table.add_row(
            r.slug,
            STATUS_STYLE[r.status],
            r.version,
            r.template,
            r.store_id or "—",
            f"[yellow]{todo}[/yellow]" if todo else "—",
        )
    output.console.print(table)


def _create(cfg: config.Config, ws: Path | None, slug: str, template: str) -> None:
    try:
        path = catalog.create(cfg.tool_dir, ws, slug, template)
    except catalog.CreateError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    output.ok(f"created {path.relative_to(cfg.tool_dir)}")
    output.console.print(
        f"  next: fill every ‹FILL› in it (feature code goes in recipes/{slug}/src/feature/), "
        f"then `tabmill bootstrap {slug}`"
    )


@advanced_app.command()
def create(
    slug: str = typer.Argument(..., help="New extension slug, e.g. jwt-inspector."),
    template: str = typer.Option("popup", "--template", "-t", help="Surface template."),
) -> None:
    """Write a starter recipe in tabmill/recipes/<slug>/."""
    cfg, ws = _config_and_workspace()
    _create(cfg, ws, slug, template)


def _registered(slug: str) -> config.Config:
    cfg = _load()
    if slug not in registry.slugs(cfg.workspace):
        output.fail(f"{slug} is not in registry.json — run `tabmill bootstrap {slug}` first")
        raise typer.Exit(1)
    return cfg


def _make(cfg: config.Config, target: str, slug: str, *extra: str) -> None:
    """Run a workspace make target in the builder container (ADR-0003)."""
    _preflight("try" if target == "try" else "docker")
    rc = subprocess.run(
        ["make", "--no-print-directory", f"in-docker-{target}", f"EXT={slug}", *extra],
        cwd=cfg.workspace,
    ).returncode
    if rc != 0:
        output.fail(f"{target} failed (exit {rc})")
        raise typer.Exit(rc)


def _lint(cfg: config.Config, slug: str, release: bool) -> bool:
    findings = lint.lint(cfg.tool_dir, cfg.workspace, slug, release=release)
    for f in findings:
        (output.fail if f.severity == "error" else output.skip)(f"{f.rule}: {f.message}")
    errors = sum(f.severity == "error" for f in findings)
    warns = len(findings) - errors
    mode = "release" if release else "dev"
    if errors:
        output.fail(f"lint {slug} ({mode}): {errors} error(s), {warns} warning(s)")
        return False
    output.ok(f"lint {slug} ({mode}): {warns} warning(s)")
    return True


@advanced_app.command("lint")
def lint_cmd(
    slug: str = typer.Argument(..., help="Extension slug."),
    release: bool = typer.Option(
        False, "--release", help="Release severities (placeholders block)."
    ),
) -> None:
    """Chrome Web Store policy checks on the recipe and the last build."""
    cfg, _ = _config_and_workspace()
    if not _lint(cfg, slug, release):
        raise typer.Exit(1)


def _test(cfg: config.Config, slug: str) -> None:
    for target in ("typecheck", "test", "smoke"):
        _make(cfg, target, slug)
    output.ok(f"{slug}: typecheck, unit, smoke passed")


@advanced_app.command()
def test(slug: str = typer.Argument(..., help="Extension slug.")) -> None:
    """Regenerate, then typecheck + unit tests + build + smoke test, in docker."""
    cfg = _registered(slug)
    _recipe(cfg, slug)
    _sync(cfg, force=False)
    _test(cfg, slug)


@advanced_app.command()
def zip(
    slug: str = typer.Argument(..., help="Extension slug."),
    release: bool = typer.Option(False, "--release", help="Block on release-severity lint."),
) -> None:
    """Regenerate, build, lint, and zip (`--release`: placeholders block)."""
    cfg = _registered(slug)
    _recipe(cfg, slug)
    _sync(cfg, force=False)
    _make(cfg, "build", slug)
    if not _lint(cfg, slug, release):
        raise typer.Exit(1)
    _make(cfg, "zip", slug)
    zips = sorted((cfg.workspace / "extensions" / slug / ".output").glob("*.zip"))
    output.ok(f"zip: {zips[-1].relative_to(cfg.workspace) if zips else '(not found)'}")


@advanced_app.command()
def dev(slug: str = typer.Argument(..., help="Extension slug.")) -> None:
    """WXT dev server with hot reload in docker; load the dev build in your own Chrome."""
    cfg = _registered(slug)
    _recipe(cfg, slug)
    _sync(cfg, force=False)
    dev_dir = cfg.workspace / "extensions" / slug / ".output" / "chrome-mv3-dev"
    output.console.print(
        f"  Chrome → chrome://extensions → Developer mode → Load unpacked → {dev_dir}\n"
        "  (once the server prints 'Started'; changes then reload automatically; Ctrl-C stops)"
    )
    _make(cfg, "dev", slug)


@app.command("try")
def try_(
    slug: str = typer.Argument(..., help="Extension slug."),
    url: str = typer.Option("", "--url", help="Page to open first (default: chrome://extensions)."),
    dev: bool = typer.Option(False, "--dev", help="Use the hot-reload dev build."),
) -> None:
    """Build it and open Chromium with the extension loaded."""
    cfg = _registered(slug)
    _recipe(cfg, slug)
    _sync(cfg, force=False)
    _make(cfg, "try", slug, f"URL={url}", f"DEV={'1' if dev else ''}")


@app.command()
def check(
    slug: str = typer.Argument("", help="Extension slug (default: every extension)."),
) -> None:
    """Tests + store-policy lint for one extension, or all of them."""
    cfg = _registered(slug) if slug else _load()
    slugs = [slug] if slug else registry.slugs(cfg.workspace)
    if not slugs:
        output.skip("no extensions generated yet — start one with `tabmill bootstrap <slug>`")
        return
    _sync(cfg, force=False)
    failed: list[str] = []
    for s in slugs:
        try:
            ext = _recipe(cfg, s)
            _test(cfg, s)
            if not _lint(cfg, s, release=False):
                raise typer.Exit(1)
        except typer.Exit:
            failed.append(s)
            continue
        if ext.get("version"):
            registry.upsert(cfg.workspace, s, {"checked_version": str(ext["version"])})
    if failed:
        output.fail(f"check: {len(failed)} of {len(slugs)} failed — {', '.join(failed)}")
        raise typer.Exit(1)
    output.ok(f"check: {len(slugs)} passed")


@advanced_app.command()
def assets(slug: str = typer.Argument(..., help="Extension slug.")) -> None:
    """Render icons, promo tile, and 1280×800 screenshots into .output/store/ (docker)."""
    cfg = _registered(slug)
    _recipe(cfg, slug)
    _sync(cfg, force=False)
    _make(cfg, "assets", slug)
    problems = listing.image_problems(cfg.workspace, slug) or []
    for p in problems:
        output.fail(p)
    if problems:
        raise typer.Exit(1)
    output.ok(f"store images: extensions/{slug}/{listing.STORE_DIR}/")


@advanced_app.command("listing")
def listing_cmd(
    slug: str = typer.Argument(..., help="Extension slug."),
    force: bool = typer.Option(False, "--force", help="Regenerate, discarding edits to the draft."),
) -> None:
    """Write the store listing draft (paste into the Developer Dashboard)."""
    cfg = _registered(slug)
    ext = _recipe(cfg, slug)
    path, written = listing.write_listing(cfg.workspace, slug, ext, force=force)
    rel = path.relative_to(cfg.workspace)
    if written:
        output.ok(f"listing draft: {rel}")
    else:
        output.ok(f"listing draft: {rel} exists, kept (--force to regenerate)")
    for word, n in listing.keyword_repeats(path.read_text()).items():
        output.skip(f"keyword-repeat: `{word}` appears {n}× (store limit: 5)")
    output.console.print("  refine the description with the tabmill-store-listing skill")


FIRST_PUBLISH = """  First publish of a new item is manual (the API can't create items):
  1. https://chrome.google.com/webstore/devconsole → Add new item → upload {zip}
  2. Fill Store listing + Privacy practices from {listing}
  3. Set visibility; submit
  4. Put the item ID in registry.json → extensions.{slug}.store_id
  5. tabmill status {slug} --refresh"""


def _store_call(fn: object) -> dict[str, object]:
    try:
        return fn()  # type: ignore[operator, no-any-return]  # thunk returning API JSON
    except cws.CwsError as e:
        (output.skip if e.transient else output.fail)(str(e))
        raise typer.Exit(1) from e


def _attended() -> None:
    if os.environ.get("CI") or not sys.stdin.isatty():
        output.fail("publish never runs unattended — run it yourself in a terminal")
        raise typer.Exit(1)


def _first_publish(cfg: config.Config, slug: str) -> None:
    zips = sorted((cfg.workspace / "extensions" / slug / ".output").glob("*.zip"))
    output.console.print(
        FIRST_PUBLISH.format(
            zip=zips[-1] if zips else f"(run `tabmill ship {slug}`)",
            listing=listing.store_dir(cfg.workspace, slug) / listing.LISTING_FILE,
            slug=slug,
        )
    )


def _publish(cfg: config.Config, slug: str, staged: bool, check: bool) -> None:
    row = registry.read(cfg.workspace)["extensions"][slug]
    store_id = row.get("store_id")
    if not check:
        _attended()
    if not store_id:
        output.fail(f"{slug} has no store_id yet")
        _first_publish(cfg, slug)
        raise typer.Exit(1)
    _preflight("publish")
    try:
        client = cws.connect(cfg.tool_dir)
    except cws.CwsError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    if not check:
        if not _lint(cfg, slug, release=True):
            raise typer.Exit(1)
        ext = _recipe(cfg, slug)
        zips = sorted(
            (cfg.workspace / "extensions" / slug / ".output").glob(f"*-{ext['version']}-*.zip")
        )
        if not zips:
            output.fail(f"no zip for {ext['version']} — run `tabmill ship {slug}`")
            raise typer.Exit(1)
        kind = "staged" if staged else "default"
        if not typer.confirm(f"Upload {zips[-1].name} to item {store_id} and submit ({kind})?"):
            output.skip("publish cancelled")
            raise typer.Exit(0)
        up = _store_call(lambda: client.upload(store_id, zips[-1]))
        state = str(up.get("uploadState"))
        if state == "IN_PROGRESS":
            state = client.wait_for_upload(store_id)
        if state != "SUCCEEDED":
            output.fail(f"upload {state.lower() or 'failed'} — check the Developer Dashboard")
            raise typer.Exit(1)
        output.ok(f"uploaded {zips[-1].name}")
        _store_call(lambda: client.publish(store_id, staged=staged))
        output.ok("submitted for review")
        registry.upsert(cfg.workspace, slug, {"submitted_version": str(ext["version"])})
    status = cws.summarize(_store_call(lambda: client.fetch_status(store_id)))
    registry.upsert(cfg.workspace, slug, status)
    output.ok(
        f"review: {status['review_state'] or '—'} · published: {status['published_state'] or '—'}"
    )
    if status["taken_down"] or status["warned"]:
        output.fail("item is taken down or warned for policy — check the Developer Dashboard")


def publish(
    slug: str = typer.Argument(..., help="Extension slug."),
    staged: bool = typer.Option(
        False, "--staged", help="After approval, wait for a manual release."
    ),
    check: bool = typer.Option(
        False, "--check", help="Only fetch review status into registry.json."
    ),
) -> None:
    """Upload the release zip and submit for review. Attended only — `ship` never uploads."""
    _publish(_registered(slug), slug, staged, check)


PROBE_STYLE = {
    "valid": "[green]✓ valid[/green]",
    "invalid": "[red]✗ invalid[/red]",
    "not-testable": "[yellow]↷ not testable[/yellow]",
    "missing": "—",
}


@apikeys_app.command("list")
def apikeys_list(
    no_probe: bool = typer.Option(False, "--no-probe", help="Skip the network probes."),
) -> None:
    """Known credentials: set / not set, masked value, and a live probe."""
    cfg, ws = _config_and_workspace()
    values = cws.load_env(cfg.tool_dir)
    store_id = None
    if ws is not None:
        store_id = next(
            (
                r.get("store_id")
                for r in registry.read(ws)["extensions"].values()
                if r.get("store_id")
            ),
            None,
        )
    probes = {} if no_probe else apikeys.probe_all(cfg.tool_dir, store_id)
    table = Table(show_edge=False, pad_edge=False, box=None, header_style="bold")
    for col in ("key", "value", "probe", "detail"):
        table.add_column(col, overflow="fold")
    for key in apikeys.KNOWN_KEYS:
        r = probes.get(key)
        table.add_row(
            key,
            apikeys.mask(key, values.get(key, "")) or "[dim]not set[/dim]",
            PROBE_STYLE[r.status] if r else "—",
            r.detail if r else "",
        )
    output.console.print(table)
    output.console.print(f"  file: {apikeys.env_path(cfg.tool_dir)} (gitignored, mode 600)")


@apikeys_app.command("set")
def apikeys_set(
    key: str = typer.Argument(..., help="Credential name, e.g. CWS_PUBLISHER_ID."),
    value: str = typer.Argument("", help="Value (omit to be prompted, hidden)."),
    force: bool = typer.Option(False, "--force", help="Allow a key name tabmill doesn't know."),
) -> None:
    """Set a credential in tabmill.env (prompted value stays out of shell history)."""
    if key not in apikeys.KNOWN_KEYS and not force:
        output.fail(
            f"unknown key {key} — known: {', '.join(apikeys.KNOWN_KEYS)} (--force to override)"
        )
        raise typer.Exit(1)
    if not value:
        value = typer.prompt(key, hide_input=key in apikeys.SECRET_KEYS)
    if key == "CWS_SA_KEY_FILE":
        path = Path(value).expanduser()
        if not path.exists():
            output.fail(f"{path} not found")
            raise typer.Exit(1)
        value = str(path.resolve())
    existed = apikeys.set_key(config.TOOL_DIR, key, value)
    output.ok(
        f"{key} {'updated' if existed else 'set'} — check with `tabmill settings apikeys list`"
    )


@apikeys_app.command("delete")
def apikeys_delete(
    key: str = typer.Argument(..., help="Credential name."),
    yes: bool = typer.Option(False, "--yes", help="Skip the confirmation."),
) -> None:
    """Remove a credential from tabmill.env."""
    if not yes and not typer.confirm(f"Delete {key} from tabmill.env?"):
        output.skip("not deleted")
        raise typer.Exit(0)
    if apikeys.delete_key(config.TOOL_DIR, key):
        output.ok(f"{key} deleted")
    else:
        output.skip(f"{key} was not set")


@settings_app.command("preflight")
def preflight_cmd() -> None:
    """Check everything tabmill depends on: workspace, builder, docker, X11, credentials."""
    checks = preflight.run()
    for c in checks:
        {"ok": output.ok, "warn": output.skip, "fail": output.fail}[c.status](
            f"{c.name}: {c.detail}"
        )
    if any(c.status == "fail" for c in checks):
        raise typer.Exit(1)


def _hub(cfg: config.Config) -> None:
    if not (cfg.hub_repo / ".git").exists():
        output.fail(f"hub repo {cfg.hub_repo} not found — set `hub_repo` in tabmill.config.json")
        raise typer.Exit(1)
    # The shared privacy policy goes first and always: its page must be live before any
    # extension's first store review, tool page or not (D-036).
    try:
        policy = privacy.load(cfg.tool_dir)
    except privacy.PolicyError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    ppath, pchanged = privacy.write(cfg.hub_repo, policy)
    note = "" if pchanged else " (unchanged)"
    output.ok(
        f"hub: privacy policy v{policy.version} → {cfg.hub_repo.name}/"
        f"{ppath.relative_to(cfg.hub_repo)}{note}"
    )
    export = hub.build(cfg.tool_dir, cfg.workspace)
    for slug, why in export.skipped.items():
        output.skip(f"hub: {slug} skipped — {why}")
    if not export.entries:
        output.skip(f"hub: no entries — {cfg.hub_repo.name}/{hub.HUB_FILE} left untouched")
        changed = False
    else:
        changed = _hub_entries(cfg, export)
    if changed or pchanged:
        output.console.print(
            f"  HUMAN: review + commit {cfg.hub_repo.name}, push to main (Vercel deploys); "
            "tabmill never commits there"
        )


def _hub_entries(cfg: config.Config, export: hub.Export) -> bool:
    path, changed = hub.write(cfg.hub_repo, export)
    rel = path.relative_to(cfg.hub_repo)
    n = len(export.entries)
    note = "" if changed else " (unchanged)"
    output.ok(f"hub: {n} entr{'y' if n == 1 else 'ies'} → {cfg.hub_repo.name}/{rel}{note}")
    published = [e["slug"] for e in export.entries if e["status"] == "published"]
    if changed and published:
        output.console.print(
            f"  HUMAN: add /extensions/<slug> to public/sitemap.xml for: {', '.join(published)}"
        )
    return changed


@advanced_app.command("hub")
def hub_cmd() -> None:
    """Export extensions to the lamill.io hub (src/content/extensions.json, its zod contract)."""
    _hub(_load())


def _release(cfg: config.Config, slug: str, ext: dict[str, object], tool_page: bool) -> None:
    """Everything up to (never including) the store upload. `tool_page` adds the landing step."""
    _sync(cfg, force=False)
    for target in ("typecheck", "test", "smoke", "assets"):
        _make(cfg, target, slug)
    path, written = listing.write_listing(cfg.workspace, slug, ext)
    output.ok(
        f"listing draft {'written' if written else 'kept'}: {path.relative_to(cfg.workspace)}"
    )
    if tool_page:
        _landing_brief(cfg, slug, ext)
    if not _lint(cfg, slug, release=True):
        output.fail(f"release blocked — fix the errors above, then re-run `tabmill ship {slug}`")
        raise typer.Exit(1)
    _make(cfg, "zip", slug)
    out = listing.collect_release(cfg.workspace, slug, str(ext["version"]))
    output.ok(f"upload folder: {out}")
    for item in sorted(out.iterdir()):
        output.console.print(f"  {item.name}")
    slots = registry.save_slots(cfg.workspace)
    row = registry.read(cfg.workspace)["extensions"][slug]
    if row.get("published_state") != "PUBLISHED" and slots["used"] >= slots["limit"]:
        output.skip(
            f"slots {slots['used']}/{slots['limit']} — publishing {slug} needs another slot "
            "(Developer Dashboard → request an increase)"
        )
    todo = cfg.workspace / "TODO.md"
    cmd = f"uv run tabmill publish {slug}"
    line = f"- [ ] HUMAN: publish {slug} {ext['version']} — `{cmd}`"
    if line not in todo.read_text():
        with todo.open("a") as f:
            f.write(f"\n{line}\n")
    output.ok(f"TODO.md: {line.removeprefix('- [ ] ')}")
    _hub(cfg)


@advanced_app.command()
def release(slug: str = typer.Argument(..., help="Extension slug.")) -> None:
    """Prepare a release: test, assets, listing, release zip, slot check, hub. Never publishes."""
    cfg = _registered(slug)
    _release(cfg, slug, _recipe(cfg, slug), tool_page=False)


def _landing_brief(cfg: config.Config, slug: str, ext: dict[str, object]) -> Path:
    store_id = registry.read(cfg.workspace)["extensions"][slug].get("store_id")
    draft = listing.store_dir(cfg.workspace, slug) / listing.LISTING_FILE
    text = landing.brief(ext, store_id, draft.read_text() if draft.exists() else None)
    path = landing.write_brief(cfg.workspace, slug, text)
    output.ok(f"tool-page brief: {path}")
    return path


@advanced_app.command("landing")
def landing_cmd(
    slug: str = typer.Argument(..., help="Extension slug."),
    check: bool = typer.Option(
        False, "--check", help="Page is live: record it + resubmit sitemap."
    ),
) -> None:
    """Brief for the tool page on the portfolio site; `--check` records it once live."""
    cfg = _registered(slug)
    ext = _recipe(cfg, slug)
    problems = landing.precheck(ext)
    for p in problems:
        output.fail(p)
    if problems:
        raise typer.Exit(1)
    url = landing.landing_url(ext)
    if not check:
        _landing_brief(cfg, slug, ext)
        output.console.print(
            f'  next: cd {landing.site_dir(ext)} && claude → "Write the page in this brief" '
            f"(attach the file); page goes at {url}\n"
            f"  then: uv run tabmill ship {slug}"
        )
        return
    code = landing.is_live(url)
    if code != 200:
        output.fail(f"{url} not live (HTTP {code or 'unreachable'}) — deploy the site first")
        raise typer.Exit(1)
    output.ok(f"{url} is live")
    _record_landing(cfg, slug, ext, url)
    output.console.print(f"  next: uv run tabmill ship {slug}")


def _record_landing(cfg: config.Config, slug: str, ext: dict[str, object], url: str) -> None:
    """The tool page is live: write its URL into the recipe, resubmit the sitemap (soft-fail)."""
    changed = landing.set_landing_url(cfg.tool_dir, slug, url)
    output.ok(f"recipe landing_page_url {'set' if changed else 'already set'}")
    site = str(ext["portfolio_site"])
    try:
        rc = subprocess.run(
            ["lamill", "settings", "gsc", "submit-sitemap", "--site", site, "--force"],
            capture_output=True,
            text=True,
            timeout=120,
        ).returncode
    except (OSError, subprocess.TimeoutExpired):
        rc = -1
    if rc == 0:
        output.ok(f"sitemap resubmitted to GSC for {site} (lamill)")
    else:
        output.skip(
            "sitemap resubmit failed — run "
            f"`lamill settings gsc submit-sitemap --site {site} --force`"
        )


def _tool_page(cfg: config.Config, slug: str, ext: dict[str, object]) -> dict[str, object]:
    """ship's tool-page step: already recorded → ✓; live → record it; else ↷ (brief follows)."""
    problems = landing.precheck(ext)
    for problem in problems:
        output.skip(f"tool page: {problem}")
    if problems:
        return ext
    url = landing.landing_url(ext)
    if ext.get("landing_page_url") == url:
        output.ok(f"tool page: {url}")
        return ext
    code = landing.is_live(url)
    if code != 200:
        output.skip(
            f"tool page: {url} not live (HTTP {code or 'unreachable'}) — write it from the "
            f"brief below in {landing.site_dir(ext)}, deploy, re-run `tabmill ship {slug}`"
        )
        return ext
    output.ok(f"tool page: {url} is live")
    _record_landing(cfg, slug, ext, url)
    return generate.load_recipe(cfg.tool_dir, slug)


@app.command()
def ship(
    slug: str = typer.Argument(..., help="Extension slug."),
    publish: bool = typer.Option(False, "--publish", hidden=True),
) -> None:
    """Prepare the store upload. Never uploads — that's `tabmill publish`. Safe to re-run."""
    if publish:
        output.fail(f"`ship` never uploads (D-040) — run `tabmill publish {slug}`")
        raise typer.Exit(1)
    cfg = _registered(slug)
    first = not registry.read(cfg.workspace)["extensions"][slug].get("store_id")
    ext = _tool_page(cfg, slug, _recipe(cfg, slug))
    _release(cfg, slug, ext, tool_page=True)
    if first:
        _first_publish(cfg, slug)
    else:
        output.console.print(f"  next: tabmill publish {slug}")


app.command()(publish)  # registered after `ship` so help reads in pipeline order


@app.command()
def status(
    slug: str = typer.Argument("", help="Extension slug (default: every extension)."),
    refresh: bool = typer.Option(False, "--refresh", help="Fetch review state from the store."),
    as_json: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Where each extension stands, and the next command to run for it."""
    cfg, ws = _config_and_workspace()
    reg = registry.read(ws)["extensions"] if ws else {}
    if slug and slug not in reg and slug not in catalog.recipe_slugs(cfg.tool_dir):
        output.fail(
            f"{slug}: no recipe and not registered — start it with `tabmill bootstrap {slug}`"
        )
        raise typer.Exit(1)
    if refresh and ws:
        _refresh(cfg, {k: v for k, v in reg.items() if not slug or k == slug})
        reg = registry.read(ws)["extensions"]
    rows = [r for r in catalog.rows(cfg.tool_dir, ws) if not slug or r.slug == slug]
    items = _portfolio(cfg).items

    def released(r: catalog.Row) -> bool:
        return bool(ws and (ws / listing.RELEASES_DIR / f"{r.slug}-{r.version}").is_dir())

    steps = {r.slug: lifecycle.next_step(r, reg.get(r.slug, {}), released(r)) for r in rows}
    stages = {
        r.slug: lifecycle.stage(
            r,
            reg.get(r.slug, {}),
            r.slug in items and items[r.slug].approval in portfolio.APPROVED,
            released(r),
        )
        for r in rows
    }
    for r in rows:  # idea-stage recipes wait for human gate 1 (D-040)
        idea_id = _idea_of(cfg, r.slug)
        if idea_id and stages[r.slug] == "shaped":
            stages[r.slug], steps[r.slug] = "verdict", f"tabmill approve {idea_id}"
    if as_json:
        typer.echo(
            json.dumps(
                [
                    {
                        **reg.get(r.slug, {}),
                        **r.to_dict(),
                        "lifecycle": stages[r.slug],
                        "next": steps[r.slug],
                    }
                    for r in rows
                ],
                indent=2,
            )
        )
        return
    if not rows:
        output.skip("no extensions yet — start one with `tabmill bootstrap <slug>`")
        return
    width = max(len(r.slug) for r in rows)
    for r in rows:
        # Two lines per extension: where it stands, then the next command — fits 80 columns.
        store = lifecycle.store_state(reg.get(r.slug, {}))
        stage = stages[r.slug]
        output.console.print(
            f"[bold]{r.slug.ljust(width)}[/bold]  {r.version or '—':<8}"
            f"{STAGE_STYLE.get(stage, stage)}"
            + ("" if stage in ("published", "maintained") else f" · {store}")
        )
        if r.error:
            output.fail(f"{r.slug}: {r.error}")
        if slug and r.store_id:
            output.console.print(f"  store id: {r.store_id}")
        output.console.print(f"  next: {steps[r.slug]}")
    if ws is None:
        return
    registry.save_slots(ws)
    _slots_line(portfolio.slots(cfg.tool_dir, ws))


STAGE_STYLE = {
    "invalid": "[red]✗ invalid[/red]",
    "orphan": "[red]✗ orphan[/red]",
    "shaped": "[yellow]↷ shaped[/yellow]",
    "approved": "[yellow]↷ approved[/yellow]",
    "bootstrapped": "[green]✓ bootstrapped[/green]",
    "checked": "[green]✓ checked[/green]",
    "shipped": "[green]✓ shipped[/green]",
    "published": "[green]✓ published[/green]",
    "maintained": "[green]✓ maintained[/green]",
}


def _idea_of(cfg: config.Config, slug: str) -> str:
    try:
        ext = extension.load_file(generate.recipe_dir(cfg.tool_dir, slug) / generate.RECIPE_FILE)
    except (extension.ExtensionError, OSError):
        return ""
    return str(ext.get("idea_id") or "")


def _portfolio(cfg: config.Config) -> portfolio.Portfolio:
    try:
        return portfolio.read(cfg.tool_dir)
    except portfolio.PortfolioError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e


def _slots_line(view: portfolio.SlotView) -> None:
    used = len(view.published) + len(view.reserved)
    line = f"slots: {len(view.published)} published + {len(view.reserved)} reserved of {view.limit}"
    if used >= view.limit:
        output.skip(f"{line} — at the cap: request more in the Developer Dashboard")
    else:
        output.ok(f"{line} — {view.free} free")


@app.command()
def slots() -> None:
    """Store slots: published, reserved by `approve`, and free (portfolio.yaml + registry)."""
    cfg, ws = _config_and_workspace()
    _portfolio(cfg)
    view = portfolio.slots(cfg.tool_dir, ws)
    for slug in view.published:
        output.ok(f"published: {slug}")
    for slug in view.reserved:
        output.skip(f"reserved: {slug} (approved, not yet published)")
    _slots_line(view)


@app.command("templates")
def templates_cmd() -> None:
    """Surface templates: what each is for, the permissions its code needs, built or not."""
    table = Table(show_edge=False, pad_edge=False, box=None, header_style="bold")
    for col in ("template", "status", "trigger", "needs", "use for"):
        table.add_column(col, overflow="fold")
    for s in surfaces.SURFACES.values():
        table.add_row(
            s.name,
            "[green]✓ built[/green]" if s.status == "implemented" else "[yellow]↷ stub[/yellow]",
            s.trigger,
            ", ".join(p for p, _ in s.permissions) or "—",
            s.use_for,
        )
    output.console.print(table)
    output.console.print(f"  target: {surfaces.TARGET} (the only one until v2.G)")


@app.command()
def doctor(
    fix: bool = typer.Option(
        False, "--fix", help="Migrate recipes to schema v2 and seed portfolio.yaml."
    ),
) -> None:
    """Everything `settings preflight` checks, plus recipes, portfolio.yaml, claude and lamill."""
    failed = False
    for c in preflight.run():
        {"ok": output.ok, "warn": output.skip, "fail": output.fail}[c.status](
            f"{c.name}: {c.detail}"
        )
        failed = failed or c.status == "fail"
    for tool, why in (("claude", "idea stage AI (v2.B)"), ("lamill", "demand data, sitemaps")):
        if shutil.which(tool):
            output.ok(f"{tool}: on PATH")
        else:
            output.skip(f"{tool}: not on PATH — needed for {why}")
    cfg, ws = _config_and_workspace()
    try:
        rs = rules.load(cfg.tool_dir)
        output.ok(f"{rules.RULES_FILE}: {len(rs.rules)} rules, in step with rules.py")
    except rules.RulesError as e:
        output.fail(str(e))
        failed = True
    for purpose, version in idea_stages.PROMPTS:
        try:
            ai.load_prompt(cfg.tool_dir, purpose, version)
            output.ok(f"prompts/{purpose}_v{version}.md: loads")
        except ai.AIError as e:
            output.fail(str(e))
            failed = True
    for slug in catalog.recipe_slugs(cfg.tool_dir):
        path = generate.recipe_dir(cfg.tool_dir, slug) / generate.RECIPE_FILE
        try:
            ext = extension.load_file(path)
        except extension.ExtensionError as e:
            output.fail(str(e))
            failed = True
            continue
        if recipe_v2.version_of(ext) >= 2:
            output.ok(f"recipes/{slug}: schema v2")
        elif fix:
            recipe_v2.migrate(cfg.tool_dir, slug)
            output.ok(f"recipes/{slug}: migrated to schema v2")
        else:
            output.skip(f"recipes/{slug}: schema v1 — `tabmill doctor --fix` migrates it")
    pf = portfolio.path(cfg.tool_dir)
    try:
        missing = [
            s
            for s in catalog.recipe_slugs(cfg.tool_dir)
            if s not in portfolio.read(cfg.tool_dir).items
        ]
    except portfolio.PortfolioError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    if fix and (missing or not pf.exists()):
        added = portfolio.seed(cfg.tool_dir, ws)
        output.ok(f"{portfolio.PORTFOLIO_FILE}: seeded ({', '.join(added) or 'slots only'})")
    elif missing or not pf.exists():
        output.skip(
            f"{portfolio.PORTFOLIO_FILE}: missing {', '.join(missing) or 'file'} — "
            "`tabmill doctor --fix` seeds it"
        )
    else:
        output.ok(f"{portfolio.PORTFOLIO_FILE}: every recipe listed")
    if failed:
        raise typer.Exit(1)


def _refresh(cfg: config.Config, rows: dict[str, dict[str, object]]) -> None:
    """Review + published state from the store into registry.json, for rows with a store_id."""
    wanted = {k: str(v["store_id"]) for k, v in rows.items() if v.get("store_id")}
    if not wanted:
        output.skip("refresh: nothing has a store_id yet")
        return
    _preflight("publish")
    try:
        client = cws.connect(cfg.tool_dir)
    except cws.CwsError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    for slug, store_id in wanted.items():
        state = cws.summarize(_store_call(lambda i=store_id: client.fetch_status(i)))
        registry.upsert(cfg.workspace, slug, state)
        if state["taken_down"] or state["warned"]:
            output.fail(f"{slug}: taken down or warned for policy — check the Developer Dashboard")
