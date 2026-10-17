"""v2.F: verdict (code score, bands, NO-GO on errors, evidence cap), write (recipe v2 +
idea.md, no clobber), portfolio item (--apply), approve (gates, freeze, slot), the freeze guard
in the build path, and `ideas list|show|compare`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tabmill import ai, cli, extension, generate, portfolio, registry, rules, schema
from tabmill.config import Config
from tabmill.idea import approve, engine
from tabmill.idea.stages import verdict, write

runner = CliRunner()
CFG = rules.VerdictConfig(
    weights={"reach": 35, "outrate": 25, "audience": 20, "risk": 10, "effort": 10},
    go=7.0, go_if=5.0,
)  # fmt: skip
STRONG: list[dict[str, Any]] = [
    {"claim": "monthly US searches: word counter", "value": 1000, "source": "https://k.example",
     "date": "", "kind": "external"},
    {"claim": "store competitor: X", "value": "{}", "source": "https://cws.example",
     "date": "", "kind": "external"},
]  # fmt: skip
WEAK: list[dict[str, Any]] = [
    {"claim": "monthly US searches: word counter", "value": 1000, "source": "brief", "date": "",
     "kind": "synthesis"},
    {"claim": "Chrome Web Store competition", "value": None, "source": "none", "date": "",
     "kind": "missing"},
]  # fmt: skip


def _all(n: int) -> dict[str, int]:
    return dict.fromkeys(verdict.DIMENSIONS, n)


# --- decide -------------------------------------------------------------------------------


def test_bands_and_boundaries() -> None:
    assert verdict.decide(_all(7), 0, STRONG, CFG)["verdict"] == "GO"
    assert verdict.decide(_all(5), 0, STRONG, CFG)["verdict"] == "GO-IF"
    assert verdict.decide(_all(4), 0, STRONG, CFG)["verdict"] == "NO-GO"
    just_under = {**_all(7), "effort": 6}  # 6.9
    got = verdict.decide(just_under, 0, STRONG, CFG)
    assert (got["weighted"], got["verdict"]) == (6.9, "GO-IF")


def test_check_error_forces_no_go() -> None:
    got = verdict.decide(_all(10), 1, STRONG, CFG)
    assert got["verdict"] == "NO-GO" and got["band"] == "GO"


def test_synthesis_only_is_capped_at_go_if() -> None:
    got = verdict.decide(_all(10), 0, WEAK, CFG)
    assert got["verdict"] == "GO-IF" and len(got["capped_by"]) == 2
    only_demand: list[dict[str, Any]] = [STRONG[0], WEAK[1]]
    assert verdict.decide(_all(10), 0, only_demand, CFG)["capped_by"] == [
        "store competition: sourced rows (brief or `tabmill evidence add`)"
    ]


# --- pipeline helpers ---------------------------------------------------------------------

DRAFT = {
    "name": "Word Counter",
    "slug": "word-counter",
    "version": "0.1.0",
    "summary": "Count words on any page.",
    "single_purpose": "Count the words on the current page.",
    "template": "popup",
    "trigger": "toolbar",
    "restricted_pages": "Shows a short message on chrome:// and store pages.",
    "permissions": [{"name": "activeTab", "justification": "Read the page after a click."}],
    "portfolio_site": "lamill.io",
    "target_keywords": ["word counter"],
    "cta_text": "More tools at lamill.io",
}


def _rec(tool_dir: Path, sid: str, stage: str, output: dict[str, Any]) -> None:
    kinds: dict[str, engine.StageKind] = {
        "clarify": "ai", "shape": "ai", "evidence": "data", "check": "rule"
    }  # fmt: skip
    kind = kinds[stage]
    engine.write_stage(tool_dir, sid, engine.StageRecord(
        stage=stage, kind=kind, input_hash=stage, created="t", output=output))  # fmt: skip


def _pipeline(
    tool_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    scores: int = 8,
    facts: list[dict[str, Any]] | None = None,
    errors: int = 0,
    draft: dict[str, Any] | None = None,
    text: str = "count words on any page",
) -> engine.Context:
    session = engine.create(tool_dir, text, non_interactive=True)
    sid = session.id
    d = {**DRAFT, **(draft or {})}
    qa = [{"id": "r1q1", "round": 1, "about": "trigger", "question": "How?", "choices": [],
           "answer": "toolbar"}]  # fmt: skip
    _rec(tool_dir, sid, "clarify", {"rounds": 1, "known": {}, "qa": qa, "open": [], "facts": []})
    _rec(tool_dir, sid, "shape", {"draft": d, "proposal": {"template_reason": "one action",
         "assumptions": ["top frame only"]}, "notes": [], "slug_rejected": []})  # fmt: skip
    _rec(
        tool_dir,
        sid,
        "evidence",
        {"providers": [], "facts": facts or STRONG, "kinds": {}, "keywords": d["target_keywords"]},
    )
    findings = [{"rule": "perm-broad-host", "severity": "error", "message": "x"}] * errors
    _rec(tool_dir, sid, "check", {"findings": findings, "errors": errors, "warnings": 0,
         "slots": {"limit": 2, "published": [], "reserved": [], "free": 2}})  # fmt: skip
    ctx = engine.Context(tool_dir, session, None, today="2026-10-16")
    fx = tool_dir / "fx"
    fx.mkdir(exist_ok=True)
    p = ai.load_prompt(tool_dir, "verdict", 1)
    reply = {"scores": {dim: {"score": scores, "reason": f"{dim} reason"}
                        for dim in verdict.DIMENSIONS},
             "risks": ["crowded"], "needs_evidence": ["store data"]}  # fmt: skip
    (fx / f"verdict_v1-{ai.input_hash(p, verdict.values(ctx))}.json").write_text(
        json.dumps({"model": "m", "replies": [json.dumps(reply)]})
    )
    monkeypatch.setenv(ai.ENV_AI, f"replay:{fx}")
    engine.run(ctx, [verdict.Verdict(), write.Write()])
    return ctx


def _out(ctx: engine.Context, stage: str) -> dict[str, Any]:
    rec = engine.read_stage(ctx.tool_dir, ctx.session.id, stage)
    assert rec is not None
    return rec.output


# --- verdict + write ----------------------------------------------------------------------


def test_sourced_reaches_go_and_synthesis_is_capped(
    tool_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    go = _pipeline(tool_dir, monkeypatch, scores=8, facts=STRONG)
    assert _out(go, "verdict")["verdict"] == "GO"
    capped = _pipeline(tool_dir, monkeypatch, scores=8, facts=WEAK, text="other idea",
                       draft={"slug": "word-counter-2"})  # fmt: skip
    v = _out(capped, "verdict")
    assert v["verdict"] == "GO-IF" and v["band"] == "GO" and v["capped_by"]


def test_write_produces_a_valid_v2_recipe_and_idea_md(
    tool_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _pipeline(tool_dir, monkeypatch)
    w = _out(ctx, "write")
    path = tool_dir / w["recipe"]
    ext = extension.load_file(path)
    assert schema.structure_errors(ext) == [] and extension.validate(ext, "word-counter") == []
    assert ext["schema_version"] == 2 and ext["idea_id"] == ctx.session.id
    assert w["fill"] == ["cta_url", "store_category"] and w["schema_errors"] == []
    text = path.read_text()
    assert 'cta_url: "‹FILL›"  # why:' in text and 'store_category: "‹FILL›"  # why:' in text
    assert [f["kind"] for f in ext["provenance"]] == ["external", "external"]
    md = (tool_dir / w["idea_md"]).read_text()
    for heading in (
        "## Idea",
        "## Questions and answers",
        "## Concept",
        "## Evidence",
        "## Check",
        "## Verdict: GO",
        "## Risks",
        "## Next",
    ):
        assert heading in md
    assert "| external | monthly US searches: word counter |" in md


def test_write_none_fits_leaves_template_to_the_operator(
    tool_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _pipeline(tool_dir, monkeypatch, draft={"template": "none-fits"})
    w = _out(ctx, "write")
    assert "template" in w["fill"] and w["schema_errors"]


def test_write_never_clobbers(tool_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = generate.recipe_dir(tool_dir, "word-counter")
    target.mkdir(parents=True)
    (target / "extension.yaml").write_text("idea_id: someone-else\n")
    with pytest.raises(engine.IdeaError, match="wasn't written by idea"):
        _pipeline(tool_dir, monkeypatch)
    (target / "extension.yaml").write_text("idea_id: x\n")
    data = portfolio.read(tool_dir)
    data.items["word-counter"] = portfolio.Item(approval="approved", idea_id="x")
    portfolio.write(tool_dir, data)
    with pytest.raises(engine.IdeaError, match="approved"):
        write.guard(tool_dir, "word-counter", "x")


# --- approve + freeze ---------------------------------------------------------------------


_MP: list[pytest.MonkeyPatch] = []


@pytest.fixture
def app_cfg(cfg: Config, monkeypatch: pytest.MonkeyPatch) -> Config:
    _MP[:] = [monkeypatch]  # _approve patches _tty through the test's own monkeypatch
    cfg.workspace.mkdir(parents=True)
    monkeypatch.setattr(cli, "_load", lambda *_: cfg)
    monkeypatch.setattr(cli, "_config_and_workspace", lambda: (cfg, cfg.workspace))
    return cfg


def _approve(cfg: Config, idea_id: str, *extra: str, tty: bool = True,
             answer: str = "y\n") -> Any:  # fmt: skip
    _MP[0].setattr(cli, "_tty", lambda: tty)
    return runner.invoke(cli.app, ["approve", idea_id, *extra], input=answer)


def test_approve_freezes_and_reserves(app_cfg: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_tty", lambda: True)
    ctx = _pipeline(app_cfg.tool_dir, monkeypatch)
    result = _approve(app_cfg, ctx.session.id)
    assert result.exit_code == 0, result.stdout
    assert "‹FILL›: cta_url" in result.stdout and "slot reserved" in result.stdout
    item = portfolio.read(app_cfg.tool_dir).items["word-counter"]
    assert (item.approval, item.slot, item.idea_id) == ("approved", "reserved", ctx.session.id)
    ext = extension.load_file(app_cfg.tool_dir / "recipes/word-counter/extension.yaml")
    assert item.frozen_sha256 == portfolio.frozen_sha256(ext)
    again = _approve(app_cfg, ctx.session.id)
    assert again.exit_code == 1 and "already approved" in again.stdout


def test_approve_refusals(app_cfg: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_tty", lambda: True)
    ctx = _pipeline(app_cfg.tool_dir, monkeypatch, errors=0, scores=2)  # NO-GO by score
    sid = ctx.session.id
    no_go = _approve(app_cfg, sid)
    assert no_go.exit_code == 1 and "--override" in no_go.stdout
    no_tty = _approve(app_cfg, sid, "--override", "I know the niche", tty=False)
    assert no_tty.exit_code == 1 and "human gate" in no_tty.stdout
    declined = _approve(app_cfg, sid, "--override", "I know the niche", answer="n\n")
    assert declined.exit_code == 1 and "word-counter" not in portfolio.read(app_cfg.tool_dir).items
    ok = _approve(app_cfg, sid, "--override", "I know the niche")
    assert ok.exit_code == 0, ok.stdout
    item = portfolio.read(app_cfg.tool_dir).items["word-counter"]
    assert item.approval == "override" and item.override_reason == "I know the niche"


def test_approve_needs_a_free_slot(app_cfg: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    for s in ("a", "b"):
        registry.upsert(app_cfg.workspace, s, {"published_state": "PUBLISHED"})
    ctx = _pipeline(app_cfg.tool_dir, monkeypatch)
    result = _approve(app_cfg, ctx.session.id)
    assert result.exit_code == 1 and "no free store slot" in result.stdout


def test_approve_refuses_rule_errors_in_the_edited_recipe(
    app_cfg: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _pipeline(app_cfg.tool_dir, monkeypatch)
    path = app_cfg.tool_dir / "recipes/word-counter/extension.yaml"
    path.write_text(
        path.read_text().replace(
            "optional_permissions: []",
            'optional_permissions:\n  - name: "<all_urls>"\n    justification: "x"',
        )
    )
    with pytest.raises(approve.ApproveError, match="perm-broad-host"):
        approve.prepare(app_cfg.tool_dir, app_cfg.workspace, ctx.session.id)


def test_build_path_gate_and_freeze_drift(app_cfg: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = _pipeline(app_cfg.tool_dir, monkeypatch)
    sid = ctx.session.id
    boot = runner.invoke(cli.app, ["bootstrap", "word-counter"])
    assert boot.exit_code == 1 and f"tabmill approve {sid}" in boot.stdout
    assert _approve(app_cfg, sid).exit_code == 0
    path = app_cfg.tool_dir / "recipes/word-counter/extension.yaml"
    text = path.read_text()
    # filling the ‹FILL› decisions after approve is fine (outside the freeze)
    path.write_text(text.replace('cta_url: "‹FILL›"', 'cta_url: "https://lamill.io/x"'))
    assert portfolio.drift(app_cfg.tool_dir, "word-counter", extension.load_file(path)) is None
    path.write_text(
        path.read_text().replace(
            "Count the words on the current page.", "Count words and characters."
        )
    )
    drift = runner.invoke(cli.app, ["bootstrap", "word-counter"])
    assert drift.exit_code == 1 and "bump recipe_revision to 2" in " ".join(drift.stdout.split())
    path.write_text(path.read_text().replace("recipe_revision: 1", "recipe_revision: 2"))
    ext = extension.load_file(path)
    assert "isn't approved" in str(portfolio.drift(app_cfg.tool_dir, "word-counter", ext))
    reapproved = _approve(app_cfg, sid)
    assert reapproved.exit_code == 0 and "re-approve" in reapproved.stdout
    assert portfolio.drift(app_cfg.tool_dir, "word-counter", ext) is None


def test_apply_writes_the_proposed_item(app_cfg: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    from tabmill.idea import stages as idea_stages

    ctx = _pipeline(app_cfg.tool_dir, monkeypatch)
    sid = ctx.session.id
    # upstream records are hand-written here; resume only the stages under test
    monkeypatch.setattr(idea_stages, "REGISTERED", (verdict.Verdict(), write.Write()))
    plain = runner.invoke(cli.app, ["new", "--resume", sid, "--non-interactive"])
    assert "+ word-counter" in plain.stdout and "add --apply" in plain.stdout
    assert "word-counter" not in portfolio.read(app_cfg.tool_dir).items
    applied = runner.invoke(cli.app, ["new", "--resume", sid, "--non-interactive", "--apply"])
    assert applied.exit_code == 0, applied.stdout
    assert portfolio.read(app_cfg.tool_dir).items["word-counter"].approval == "proposed"
    assert "next: fill cta_url, store_category" in " ".join(applied.stdout.split())


# --- ideas --------------------------------------------------------------------------------


def test_ideas_list_show_compare(app_cfg: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    a = _pipeline(app_cfg.tool_dir, monkeypatch, scores=8)
    b = _pipeline(app_cfg.tool_dir, monkeypatch, scores=5, text="measure page elements",
                  draft={"slug": "page-ruler", "name": "Page Ruler"})  # fmt: skip
    listed = runner.invoke(cli.app, ["ideas"])
    assert listed.exit_code == 0 and "GO-IF" in listed.stdout and "page-ruler" in listed.stdout
    shown = runner.invoke(cli.app, ["ideas", "show", a.session.id])
    assert "## Verdict: GO" in shown.stdout
    compared = runner.invoke(cli.app, ["ideas", "compare", a.session.id, b.session.id])
    assert compared.exit_code == 0 and "word-counter" in compared.stdout
    assert "8.0" in compared.stdout and "5.0" in compared.stdout
    assert runner.invoke(cli.app, ["ideas", "compare", a.session.id]).exit_code == 1


def test_status_points_an_unapproved_idea_recipe_at_approve(
    app_cfg: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _pipeline(app_cfg.tool_dir, monkeypatch)
    out = " ".join(runner.invoke(cli.app, ["status"]).stdout.split())
    assert f"tabmill approve {ctx.session.id}" in out and "verdict" in out
