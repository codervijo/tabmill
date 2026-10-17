"""v2.D: shared rules engine (rules/lamill.yaml ↔ rules.py, used by the idea `check` stage and
by lint), shape_v1 (slug pick, template fit, operator template), check stage, CLI flow."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tabmill import ai, cli, lint, portfolio, registry, rules
from tabmill.config import TOOL_DIR, Config
from tabmill.idea import engine
from tabmill.idea.stages import check, clarify, shape

runner = CliRunner()
IDEA = "count words on any page"


def _draft(**over: Any) -> dict[str, Any]:
    d: dict[str, Any] = {
        "name": "Word Counter",
        "slug": "word-counter",
        "version": "0.1.0",
        "summary": "Count words on any page.",
        "single_purpose": "Count the words on the current page.",
        "template": "popup",
        "permissions": [{"name": "activeTab", "justification": "read the page on click"}],
        "portfolio_site": "lamill.io",
        "target_keywords": ["word counter"],
        "cta_text": "More tools",
    }
    return {**d, **over}


def _ids(findings: list[rules.Finding]) -> dict[str, str]:
    return {f.rule: f.severity for f in findings}


def _eval(tool_dir: Path, ctx: rules.Context = "idea", **over: Any) -> list[rules.Finding]:
    return rules.evaluate(rules.Subject(_draft(**over), "word-counter", tool_dir), ctx)


# --- rules engine -------------------------------------------------------------------------


def test_rules_file_and_predicates_in_step() -> None:
    rs = rules.load(TOOL_DIR)
    assert set(rs.rules) == set(rules.PREDICATES)


def test_out_of_step_rules_file_fails(tool_dir: Path) -> None:
    p = tool_dir / rules.RULES_FILE
    p.write_text(p.read_text().replace("  slot-free:", "  slot-gone:"))
    with pytest.raises(rules.RulesError, match="out of step"):
        rules.load(tool_dir)


def test_clean_draft_passes(tool_dir: Path) -> None:
    assert _eval(tool_dir) == []


def test_all_urls_unjustified_fails_at_idea(tool_dir: Path) -> None:
    perms = [{"name": "activeTab", "justification": "x"}, {"name": "<all_urls>"}]
    ids = _ids(_eval(tool_dir, permissions=perms))
    assert ids["perm-broad-host"] == "error" and ids["perm-justification"] == "error"


def test_all_urls_unjustified_fails_in_check(cfg: Config) -> None:
    slug = "save-page-pdf-md"
    shutil.copytree(TOOL_DIR / "recipes" / slug, cfg.tool_dir / "recipes" / slug)
    path = cfg.tool_dir / "recipes" / slug / "extension.yaml"
    path.write_text(
        path.read_text().replace("host_permissions: []", "")
        + ("host_permissions:\n  - name: <all_urls>\n")
    )
    findings = lint.lint(cfg.tool_dir, None, slug, release=False)
    errors = {f.rule for f in findings if f.severity == "error"}
    assert {"perm-broad-host", "schema"} <= errors  # schema = no justification (validate)


def test_severity_by_context(tool_dir: Path) -> None:
    over = {"single_purpose": "‹FILL›", "name": "x" * 80}
    idea = _ids(_eval(tool_dir, "idea", **over))
    dev = _ids(_eval(tool_dir, "dev", **over))
    assert idea["single-purpose"] == "error" and idea["name-length"] == "error"
    assert "fill-placeholder" not in idea  # idea drafts keep ‹FILL› by design
    # length + purpose: extension.validate in dev; the draft has no cta_url yet
    assert dev == {"fill-placeholder": "warn", "cta-placeholder": "warn"}


def test_brand_allowlist_template_rules(tool_dir: Path) -> None:
    ids = _ids(
        _eval(
            tool_dir,
            name="YouTube Word Counter",
            template="page-overlay",
            permissions=[{"name": "tabs", "justification": "list tabs"}],
        )
    )
    assert ids == {
        "store-name-brand": "warn",
        "perm-not-allowlisted": "warn",
        "template-implemented": "warn",
        "privacy-coverage": "warn",  # `tabs` isn't in privacy-policy.yaml either
    }
    assert "no template fits" in _eval(tool_dir, template="none-fits")[0].message


def test_slot_free(tool_dir: Path, tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    for s in ("a", "b"):
        registry.upsert(ws, s, {"published_state": "PUBLISHED"})
    full = rules.evaluate(rules.Subject(_draft(), "word-counter", tool_dir, ws), "idea")
    assert _ids(full) == {"slot-free": "warn"}


# --- shape + check ------------------------------------------------------------------------

Q = {"about": "trigger", "text": "How does it start?", "choices": ["toolbar"]}


def _shape_reply(**over: Any) -> str:
    r = {
        "single_purpose": "Count the words on the current page or selection.",
        "template": "side-panel",
        "template_reason": "results stay visible while reading",
        "permissions": [{"name": "activeTab", "justification": "read the page after a click"}],
        "trigger": "toolbar",
        "restricted_pages": "shows 'can't count here' on chrome:// and store pages",
        "slug_candidates": ["Word Counter", "save-page-pdf-md", "word-counter"],
        "store_name": "Word Counter",
        "summary": "Count words, characters and reading time on any page.",
        "keywords": ["word counter"],
        "portfolio_site": "lamill.io",
        "cta_text": "More writing tools at lamill.io",
        "assumptions": ["works on the top frame only"],
    }
    return json.dumps({**r, **over})


def _write_fixture(
    fx: Path, tool_dir: Path, purpose: str, values: dict[str, str], reply: str
) -> None:
    p = ai.load_prompt(tool_dir, purpose, 1)
    fx.mkdir(parents=True, exist_ok=True)
    (fx / f"{p.id}-{ai.input_hash(p, values)}.json").write_text(
        json.dumps({"model": "m", "replies": [reply]})
    )


def _clarified(
    tool_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    template: str = "",
    workspace: Path | None = None,
) -> engine.Context:
    fx = tool_dir / "fx"
    monkeypatch.setenv(ai.ENV_AI, f"replay:{fx}")
    reply = json.dumps({"known": {"core_action": "count words"}, "questions": [Q]})
    _write_fixture(fx, tool_dir, "clarify", clarify.values(IDEA, [], 1), reply)
    session = engine.create(tool_dir, IDEA, template=template, non_interactive=True)
    ctx = engine.Context(tool_dir, session, None, today="2026-10-16", workspace=workspace)
    engine.run(ctx, [clarify.Clarify()])
    return ctx


def test_shape_picks_slug_adds_template_perms_and_check_runs(
    tool_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shutil.copytree(TOOL_DIR / "recipes", tool_dir / "recipes")
    ctx = _clarified(tool_dir, monkeypatch)
    values = shape.values(ctx)
    assert "save-page-pdf-md:" in values["existing"] and "How does it start?" in values["open"]
    _write_fixture(tool_dir / "fx", tool_dir, "shape", values, _shape_reply())
    recs = engine.run(ctx, [clarify.Clarify(), shape.Shape(), check.Check()])
    out = {r.stage: r.output for r in recs}
    d = out["shape"]["draft"]
    assert d["slug"] == "word-counter"
    assert out["shape"]["slug_rejected"] == [
        "Word Counter: not lowercase kebab-case ≤ 40 chars",
        "save-page-pdf-md: already used",
    ]
    assert [p["name"] for p in d["permissions"]] == ["activeTab", "sidePanel"]
    assert out["shape"]["notes"] == ["added `sidePanel`: template side-panel needs it"]
    assert out["check"]["errors"] == 0 and out["check"]["slots"]["limit"] == 2
    assert engine.stage_file(tool_dir, ctx.session.id, "check").name == "04-check.json"


def test_operator_template_wins_and_stub_is_flagged(
    tool_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _clarified(tool_dir, monkeypatch, template="page-overlay")
    _write_fixture(tool_dir / "fx", tool_dir, "shape", shape.values(ctx), _shape_reply())
    recs = engine.run(ctx, [clarify.Clarify(), shape.Shape(), check.Check()])
    out = {r.stage: r.output for r in recs}
    assert out["shape"]["draft"]["template"] == "page-overlay"
    assert "operator's --template" in out["shape"]["notes"][0]
    assert {f["rule"] for f in out["check"]["findings"]} == {"template-implemented"}


def test_unjustified_all_urls_from_shape_fails_check(
    tool_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _clarified(tool_dir, monkeypatch)
    reply = _shape_reply(
        template="popup", permissions=[{"name": "<all_urls>", "justification": "   "}]
    )
    _write_fixture(tool_dir / "fx", tool_dir, "shape", shape.values(ctx), reply)
    recs = engine.run(ctx, [clarify.Clarify(), shape.Shape(), check.Check()])
    chk = recs[-1].output
    assert {f["rule"] for f in chk["findings"] if f["severity"] == "error"} == {
        "perm-broad-host",
        "perm-justification",
    }


def test_pick_slug_fallback() -> None:
    slug, rejected = shape.pick_slug(["BAD"], {"word-counter"}, "Word Counter!")
    assert slug == "word-counter-2" and len(rejected) == 1


def test_check_reruns_when_slots_change(
    tool_dir: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    ctx = _clarified(tool_dir, monkeypatch, workspace=ws)
    _write_fixture(tool_dir / "fx", tool_dir, "shape", shape.values(ctx), _shape_reply())
    stages: list[engine.Stage] = [clarify.Clarify(), shape.Shape(), check.Check()]
    engine.run(ctx, stages)
    for s in ("a", "b"):
        registry.upsert(ws, s, {"published_state": "PUBLISHED"})
    steps: list[tuple[str, str]] = []
    engine.run(ctx, stages, on_step=lambda n, w: steps.append((n, w)))
    assert steps == [("clarify", "recorded"), ("shape", "recorded"), ("check", "ran")]
    assert portfolio.slots(tool_dir, ws).free == 0


# --- CLI ----------------------------------------------------------------------------------


def test_cli_resume_runs_shape_and_check(cfg: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg.workspace.mkdir(parents=True)
    monkeypatch.setattr(cli, "_load", lambda *_: cfg)
    monkeypatch.setattr("tabmill.idea.stages.evidence.default_providers", lambda: [])
    from tabmill.idea import stages as idea_stages

    monkeypatch.setattr(idea_stages, "REGISTERED", idea_stages.REGISTERED[:4])  # verdict: v2.F
    shutil.copytree(TOOL_DIR / "recipes", cfg.tool_dir / "recipes")
    ctx = _clarified(cfg.tool_dir, monkeypatch, workspace=cfg.workspace)
    _write_fixture(cfg.tool_dir / "fx", cfg.tool_dir, "shape", shape.values(ctx), _shape_reply())
    result = runner.invoke(cli.app, ["new", "--resume", ctx.session.id, "--non-interactive"])
    assert result.exit_code == 0, result.stdout
    out = " ".join(result.stdout.split())  # rich wraps at 80 columns
    assert "shape: word-counter · side-panel · 'Word Counter'" in out
    assert "check: 0 error(s)" in out
    assert "AI: 1 call(s)" in out
    rerun = runner.invoke(cli.app, ["new", "shape", ctx.session.id, "--non-interactive"])
    again = " ".join(rerun.stdout.split())
    assert rerun.exit_code == 0 and "shape: ran · marked stale: evidence, check" in again
    assert "stale: evidence, check — `tabmill new --resume" in again
    resumed = runner.invoke(cli.app, ["new", "--resume", ctx.session.id, "--non-interactive"])
    assert "check: ran" in " ".join(resumed.stdout.split())  # resume re-ran the stale stage
