"""v2.E: evidence providers (lamill validate/trends, files, brief, overlap, stubs), missing
facts, evidence stage + re-run on `evidence add`, CLI (`--evidence`, `evidence add`,
`new validate|trends`). lamill is faked: the real one spends SerpAPI quota and Claude cost."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tabmill import ai, brief, cli
from tabmill.config import TOOL_DIR, Config
from tabmill.idea import engine, evidence
from tabmill.idea.stages import evidence as evidence_stage

runner = CliRunner()

VALIDATE: dict[str, Any] = {
    "schema": "research-cluster-v2",
    "topic": "word counter",
    "fetched_at": "2026-10-16T10:00:00+00:00",
    "source": "serpapi",
    "from_cache": False,
    "per_query_results": [
        {
            "query": "word counter",
            "fetched_at": "2026-10-16T09:59:00+00:00",
            "organic_results": [{"domain": "wordcounter.net"}, {"domain": "wordcounter.io"}],
            "features": {"ai_overview": {"present": True}, "people_also_ask": ["Is it free?"]},
        }
    ],
    "fetch_errors": [],
    "gates": {"gate_1_market": {"raw": {"pollution_adjusted_volume": 12000}}},
    "costs": {"total_usd": 0.33},
}
TRENDS: dict[str, Any] = {
    "schema": "gtrends-v1",
    "topic": "word counter",
    "timeframe": "12m",
    "region": "",
    "fetched_at": "2026-10-16T10:01:00+00:00",
    "interest_over_time": [
        {"date": "2026-01-01", "value": 60},
        {"date": "2026-02-01", "value": 80},
    ],
    "related_top": [{"query": "word counter online", "value": 100}],
}
EVIDENCE_FILE = """\
---
idea: word counter
collected: 2026-10-15
---
Notes from a keyword tool.
### Demand
| keyword | monthly_us_searches | difficulty | source | date |
|---|---|---|---|---|
| word count chrome | 2,400 | low | https://kw.example/report | |
| count words on page | 300 | low | | |
### Store competition
| extension | users | rating | ratings_count | last_updated | url |
|---|---|---|---|---|---|
| Word Counter Plus | 200k | 4.6 | 1,200 | 2025-01-02 | https://cws.example/x |
"""


def fake_lamill(
    validate: dict[str, Any] | None = VALIDATE,
    trends: dict[str, Any] | None = TRENDS,
    calls: list[list[str]] | None = None,
) -> evidence.Run:
    def run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        if calls is not None:
            calls.append(cmd)
        data = validate if cmd[2] == "validate" else trends
        if data is None:
            return subprocess.CompletedProcess(cmd, 3, "", "rate limited")
        out = "Researching…\n" + json.dumps({**data, "topic": cmd[3]})
        return subprocess.CompletedProcess(cmd, 0, out, "")

    return run


def _by_claim(facts: list[Any]) -> dict[str, Any]:
    return {f.claim: f for f in facts}


# --- providers ----------------------------------------------------------------------------


def test_lamill_validate_kinds_sources_dates_and_cost() -> None:
    ai.LEDGER.clear()
    got = evidence.Lamill(fake_lamill()).validate("word counter")
    facts = _by_claim(got.facts)
    top = facts["SERP top-10 domains: word counter"]
    assert (top.kind, top.date) == ("real", "2026-10-16") and "SerpAPI" in top.source
    assert json.loads(str(top.value)) == ["wordcounter.net", "wordcounter.io"]
    assert facts["AI Overview on the SERP: word counter"].value is True
    vol = next(f for f in got.facts if f.claim.startswith("monthly searches"))
    assert vol.kind == "synthesis" and vol.value == 12000  # lamill's volume is an LLM estimate
    assert [r.cost_usd for r in ai.LEDGER] == [0.33]
    ai.LEDGER.clear()


def test_lamill_synthesis_only_and_cached_cost() -> None:
    ai.LEDGER.clear()
    synth = {**VALIDATE, "source": "synthesis", "from_cache": True}
    got = evidence.Lamill(fake_lamill(validate=synth)).validate("word counter")
    assert {f.kind for f in got.facts} == {"synthesis"}
    assert "NOT REAL SERP DATA" in got.facts[0].source
    assert ai.LEDGER == []  # cached: nothing spent this run


def test_lamill_trends_and_failure() -> None:
    got = evidence.Lamill(fake_lamill()).trends("word counter")
    avg = got.facts[0]
    assert avg.kind == "real" and avg.value == 70.0 and "not volume" in avg.claim
    failed = evidence.Lamill(fake_lamill(trends=None)).trends("word counter")
    assert failed.status == "failed" and failed.facts[0].kind == "missing"


def test_lamill_all_failing_is_a_failed_provider() -> None:
    got = evidence.Lamill(fake_lamill(validate=None, trends=None)).collect(["a", "b"])
    assert got.status == "failed" and "exit 3" in got.detail


def test_lamill_runs_validate_once_and_trends_for_three(tmp_path: Path) -> None:
    calls: list[list[str]] = []
    evidence.Lamill(fake_lamill(calls=calls)).collect(["a", "b", "c", "d"])
    assert [c[2:4] for c in calls] == [
        ["validate", "a"],
        ["trends", "a"],
        ["trends", "b"],
        ["trends", "c"],
    ]


def test_evidence_file_parse_and_facts() -> None:
    parsed, collected = brief.parse_evidence(EVIDENCE_FILE)
    assert parsed.problems == [] and collected == "2026-10-15"
    facts = _by_claim(brief.evidence_facts(parsed, collected, "evidence/kw.md"))
    sourced = facts["monthly US searches: word count chrome"]
    assert (sourced.kind, sourced.value, sourced.date) == ("external", 2400, "2026-10-15")
    assert facts["monthly US searches: count words on page"].kind == "synthesis"
    assert facts["store competitor: Word Counter Plus"].kind == "external"


def test_evidence_file_without_tables_is_a_problem() -> None:
    parsed, _ = brief.parse_evidence("---\nidea: x\n---\njust notes\n")
    assert not parsed.present and "no ## Demand" in str(parsed.problems[0])


def test_missing_facts_per_keyword_and_competition() -> None:
    have = evidence.Lamill(fake_lamill()).trends("word counter").facts
    out = evidence.missing(["word counter", "count words"], have)
    assert [f.claim for f in out] == [
        "demand (real or sourced): count words",
        "Chrome Web Store competition",
    ]
    assert {f.kind for f in out} == {"missing"}


# --- stage --------------------------------------------------------------------------------


def _shaped(tool_dir: Path, keywords: list[str]) -> engine.Context:
    session = engine.create(tool_dir, "count words on any page", non_interactive=True)
    ctx = engine.Context(tool_dir, session, None, today="2026-10-16")
    draft = {"single_purpose": "Count the words on the current page.", "target_keywords": keywords}
    engine.write_stage(
        tool_dir,
        session.id,
        engine.StageRecord(
            stage="shape", kind="ai", input_hash="h", created="t", output={"draft": draft}
        ),
    )
    return ctx


def test_evidence_stage_records_kinds_and_reruns_on_new_file(tool_dir: Path) -> None:
    shutil.copytree(TOOL_DIR / "recipes", tool_dir / "recipes")
    ctx = _shaped(tool_dir, ["word counter", "x", "y", "word count chrome"])  # trends: first 3
    stage = evidence_stage.Evidence(
        [
            evidence.Lamill(fake_lamill()),
            evidence.Files(),
            evidence.Brief(),
            evidence.Overlap(),
            evidence.NotAvailable("store competition", "not implemented in v2"),
        ]
    )
    (rec,) = engine.run(ctx, [stage])
    out = rec.output
    status = {p["name"]: p["status"] for p in out["providers"]}
    assert status == {
        "lamill": "ok",
        "files": "skipped",
        "brief": "skipped",
        "overlap": "ok",
        "store competition": "not available",
    }
    missing = [f["claim"] for f in out["facts"] if f["kind"] == "missing"]
    assert missing == [
        "demand (real or sourced): word count chrome",
        "Chrome Web Store competition",
    ]
    assert all(f["source"] for f in out["facts"])
    src = tool_dir / "kw.md"
    src.write_text(EVIDENCE_FILE)
    evidence.add_file(ctx.dir, src)
    steps: list[tuple[str, str]] = []
    (rec2,) = engine.run(ctx, [stage], on_step=lambda n, w: steps.append((n, w)))
    assert steps == [("evidence", "ran")]
    assert [f["claim"] for f in rec2.output["facts"] if f["kind"] == "missing"] == []


# --- CLI ----------------------------------------------------------------------------------


@pytest.fixture
def app_cfg(cfg: Config, monkeypatch: pytest.MonkeyPatch) -> Config:
    cfg.workspace.mkdir(parents=True)
    monkeypatch.setattr(cli, "_load", lambda *_: cfg)
    monkeypatch.setattr("tabmill.idea.evidence._run", fake_lamill())
    return cfg


def test_cli_new_validate_and_trends(app_cfg: Config) -> None:
    v = runner.invoke(cli.app, ["new", "validate", "word counter"])
    out = " ".join(v.stdout.split())
    assert v.exit_code == 0 and "[real] SERP top-10 domains: word counter" in out
    assert "AI: 1 call(s) · $0.3300 · lamill new validate" in out
    t = runner.invoke(cli.app, ["new", "trends", "word counter", "count words"])
    assert t.exit_code == 0 and t.stdout.count("Google Trends interest, average") == 2
    assert not (app_cfg.tool_dir / "ideas").exists()  # research only, no session


def test_cli_evidence_add(app_cfg: Config, tmp_path: Path) -> None:
    ctx = _shaped(app_cfg.tool_dir, ["word counter"])
    src = tmp_path / "kw.md"
    src.write_text(EVIDENCE_FILE)
    result = runner.invoke(cli.app, ["evidence", "add", ctx.session.id, str(src)])
    assert result.exit_code == 0 and "(3 rows)" in result.stdout
    assert (ctx.dir / "evidence" / "kw.md").read_text() == EVIDENCE_FILE
    bad = tmp_path / "bad.md"
    bad.write_text("no tables")
    assert runner.invoke(cli.app, ["evidence", "add", ctx.session.id, str(bad)]).exit_code == 1
    missing = runner.invoke(cli.app, ["evidence", "add", "nope", str(src)])
    assert missing.exit_code == 1 and "no idea nope" in missing.stdout


def test_cli_new_with_evidence_files_copies_them(
    app_cfg: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tabmill.idea import stages as idea_stages
    from tabmill.idea.stages import clarify

    monkeypatch.setattr(idea_stages, "REGISTERED", (clarify.Clarify(),))
    p = ai.load_prompt(app_cfg.tool_dir, "clarify", 1)
    vals = clarify.values("count words", [], 1)
    fx = tmp_path / "fx"
    fx.mkdir()
    (fx / f"clarify_v1-{ai.input_hash(p, vals)}.json").write_text(
        json.dumps({"model": "m", "replies": [json.dumps({"known": {}, "questions": []})]})
    )
    monkeypatch.setenv(ai.ENV_AI, f"replay:{fx}")
    src = tmp_path / "kw.md"
    src.write_text(EVIDENCE_FILE)
    result = runner.invoke(
        cli.app, ["new", "count", "words", "--evidence", str(src), "--non-interactive"]
    )
    assert result.exit_code == 0, result.stdout
    (d,) = (app_cfg.tool_dir / "ideas").iterdir()
    assert (d / "evidence" / "kw.md").exists()
