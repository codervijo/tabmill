"""v2.C: Tabmill brief v1 — schema, section-tolerant parser, provenance kinds, `brief check`,
brief input (`--brief`, `-`, `--paste`, auto-detect), gap-only clarify."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tabmill import ai, brief, cli
from tabmill.config import TOOL_DIR, Config
from tabmill.idea.stages import clarify

runner = CliRunner()

FULL = """\
---
tabmill_brief: 1
idea: Word counter
author: claude.ai
created: 2026-10-16
---
## Idea
Count words and reading time on any page, or in the selected text.
## Answers
target_user: writers checking article length
core_action: count words on the page or selection
trigger: toolbar
pages_touched: any page, current tab only
done_looks_like: a popup with words, characters and reading time
## Proposal
single_purpose: Count the words on the current page or selection.
template: popup
permissions:
  - activeTab: read the page only after a click
  - scripting: count text in the tab
slug_candidates: [word-counter, page-word-count]
store_name: Word Counter: words & reading time
summary: Count words, characters and reading time for any page or selection.
keywords: [word counter, word count chrome]
portfolio_site: lamill.io
cta: More writing tools at lamill.io
## Evidence
### Demand
| keyword | monthly_us_searches | difficulty | source | date |
|---|---|---|---|---|
| word counter | 1,000,000 | high | https://example.com/kw | 2026-10-10 |
| word count chrome | 2.4k | low | | 2026-10-10 |
### Store competition
| extension | users | rating | ratings_count | last_updated | url |
|---|---|---|---|---|---|
| Word Counter Plus | 200,000 | 4.6 | 1,200 | 2025-01-02 | https://cws.example/x |
## Risks
- crowded category
## Open questions
- Count text inside iframes?
"""


def _without_open_questions(text: str) -> str:
    return text.replace("## Open questions\n- Count text inside iframes?\n", "")


def test_brief_schema_file_is_current() -> None:
    assert (TOOL_DIR / brief.SCHEMA_FILE).read_text() == brief.json_schema()


def test_full_brief_parses() -> None:
    parsed = brief.parse(FULL)
    b = parsed.brief
    assert parsed.problems == [] and brief.missing(parsed) == []
    assert b.meta is not None and b.meta.idea == "Word counter"
    assert b.answers.trigger == "toolbar"
    assert [p.name for p in b.proposal.permissions] == ["activeTab", "scripting"]
    assert b.proposal.store_name == "Word Counter: words & reading time"  # `: ` in a value
    assert [d.monthly_us_searches for d in b.demand] == [1_000_000, 2_400]
    assert b.competition[0].rating == 4.6 and b.competition[0].ratings_count == 1200
    assert b.open_questions == ["Count text inside iframes?"]


def test_provenance_kinds() -> None:
    facts = brief.facts(brief.parse(FULL))
    by_claim = {f.claim: f for f in facts}
    assert by_claim["monthly US searches: word counter"].kind == "external"
    assert by_claim["monthly US searches: word count chrome"].kind == "synthesis"
    assert by_claim["store competitor: Word Counter Plus"].kind == "external"
    assert by_claim["proposal.template"].kind == "external_suggestion"
    assert by_claim["target_user"].kind == "external_suggestion"
    assert brief.downgraded(brief.parse(FULL)) == ["Demand: word count chrome"]


def test_every_section_missing() -> None:
    parsed = brief.parse("---\ntabmill_brief: 1\nidea: x\n---\n")
    assert parsed.problems == []
    assert brief.missing(parsed) == [
        *(f"section ## {s}" for s in brief.SECTIONS),
        "table ### Demand",
        "table ### Store competition",
    ]


def test_template_placeholders_count_as_missing() -> None:
    text = (
        "---\ntabmill_brief: 1\nidea: x\n---\n## Answers\ntarget_user: …\n"
        "trigger: toolbar | shortcut | context_menu | side_panel\n## Proposal\npermissions:\n"
        "  - <name>: <why>\nslug_candidates: [ … ]\n"
    )
    parsed = brief.parse(text)
    assert parsed.problems == []
    assert parsed.brief.answers.trigger == "" and parsed.brief.proposal.permissions == []
    assert "Answers: target_user" in brief.missing(parsed)


def test_malformed_brief_reports_exact_line_and_keeps_the_rest() -> None:
    bad = FULL.replace(
        "| word count chrome | 2.4k | low | | 2026-10-10 |", "| word count chrome | lots |"
    )
    bad = bad.replace("trigger: toolbar", "trigger: hover")
    parsed = brief.parse(bad)
    lines = bad.splitlines()
    msgs = [str(p) for p in parsed.problems]
    demand_line = lines.index("| word count chrome | lots |") + 1
    trigger_line = lines.index("trigger: hover") + 1
    assert f"line {demand_line}, section ## Evidence › ### Demand: 2 cells, expected 5" in msgs
    assert any(m.startswith(f"line {trigger_line}, section ## Answers: trigger") for m in msgs)
    # everything else survived
    assert [d.keyword for d in parsed.brief.demand] == ["word counter"]
    assert parsed.brief.answers.target_user and parsed.brief.proposal.store_name
    assert parsed.brief.competition and parsed.brief.open_questions


def test_bad_number_and_bad_columns() -> None:
    bad = FULL.replace("| Word Counter Plus | 200,000 |", "| Word Counter Plus | many |")
    bad = bad.replace("| keyword | monthly_us_searches |", "| kw | monthly_us_searches |")
    msgs = [str(p) for p in brief.parse(bad).problems]
    assert any("Store competition" in m and "'many' is not a number" in m for m in msgs)
    assert any("Demand: columns must be" in m for m in msgs)


def test_detection() -> None:
    assert brief.is_brief(FULL) and brief.is_brief("\n\n" + FULL)
    assert not brief.is_brief("count words on any page")
    assert not brief.is_brief("---\ntitle: x\n---\n")


# --- CLI ----------------------------------------------------------------------------------


@pytest.fixture
def app_cfg(cfg: Config, monkeypatch: pytest.MonkeyPatch) -> Config:
    cfg.workspace.mkdir(parents=True)
    monkeypatch.setattr(cli, "_load", lambda *_: cfg)
    monkeypatch.setenv(ai.ENV_AI, f"replay:{cfg.tool_dir / 'fx'}")
    return cfg


def test_brief_check(tmp_path: Path) -> None:
    good = tmp_path / "good.md"
    good.write_text(FULL)
    ok = runner.invoke(cli.app, ["brief", "check", str(good)])
    assert ok.exit_code == 0 and "valid brief" in ok.stdout
    assert "word count chrome has no source URL — downgraded" in ok.stdout
    bad = tmp_path / "bad.md"
    bad.write_text(FULL.replace("trigger: toolbar", "trigger: hover"))
    result = runner.invoke(cli.app, ["brief", "check", str(bad)])
    assert result.exit_code == 1 and "✗ brief: line 12, section ## Answers" in result.stdout
    assert "missing Answers: trigger" in result.stdout
    plain = tmp_path / "plain.md"
    plain.write_text("just words")
    assert runner.invoke(cli.app, ["brief", "check", str(plain)]).exit_code == 1


def _session_files(cfg: Config) -> Path:
    (d,) = (cfg.tool_dir / "ideas").iterdir()
    return d


def test_new_brief_with_all_answers_asks_only_open_questions_without_ai(
    app_cfg: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    f = tmp_path / "b.md"
    f.write_text(FULL)
    monkeypatch.setattr(cli, "_tty", lambda: True)
    result = runner.invoke(cli.app, ["new", "--brief", str(f)], input="no, top frame only\n")
    assert result.exit_code == 0, result.stdout
    assert "AI: no calls" in result.stdout and "1 answered, 0 open" in result.stdout
    d = _session_files(app_cfg)
    assert d.name.endswith("-word-counter")
    assert (d / "brief.md").read_text() == FULL  # verbatim
    out = json.loads((d / "stages" / "01-clarify.json").read_text())["output"]
    assert out["known"]["pages"] == "any page, current tab only"
    assert out["qa"][0]["question"] == "Open question from the brief: Count text inside iframes?"
    kinds = {f["claim"]: f["kind"] for f in out["facts"]}
    assert kinds["trigger"] == "external_suggestion" and "user" in kinds.values()


def test_new_brief_gap_only_clarify_asks_ai_about_missing_fields(
    app_cfg: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = _without_open_questions(FULL).replace("trigger: toolbar\n", "")
    parsed_given = {
        "target_user": "writers checking article length",
        "core_action": "count words on the page or selection",
        "pages": "any page, current tab only",
        "done_looks_like": "a popup with words, characters and reading time",
    }
    p = ai.load_prompt(app_cfg.tool_dir, "clarify", 1)
    idea = "Count words and reading time on any page, or in the selected text."
    values = clarify.values(idea, [], 1, parsed_given)
    assert "(from the brief) → writers checking article length" in values["answers"]
    reply = json.dumps(
        {
            "known": {},
            "questions": [
                {
                    "about": "target_user",
                    "text": "Who is it for?",
                    "choices": [],
                },  # known → dropped
                {"about": "trigger", "text": "How does it start?", "choices": ["toolbar", "key"]},
            ],
        }
    )
    fx = app_cfg.tool_dir / "fx"
    fx.mkdir()
    (fx / f"clarify_v1-{ai.input_hash(p, values)}.json").write_text(
        json.dumps({"model": "m", "replies": [reply]})
    )
    result = runner.invoke(cli.app, ["new", "-", "--non-interactive"], input=text)
    assert result.exit_code == 0, result.stdout
    out = json.loads((_session_files(app_cfg) / "stages" / "01-clarify.json").read_text())
    assert [q["about"] for q in out["output"]["qa"]] == ["trigger"]
    assert out["output"]["known"]["target_user"] == "writers checking article length"


def test_new_paste_broken_section_becomes_a_question(
    app_cfg: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = _without_open_questions(FULL).replace(
        "| word count chrome | 2.4k | low | | 2026-10-10 |", "| word count chrome | lots |"
    )
    result = runner.invoke(cli.app, ["new", "--paste", "--non-interactive"], input=text + ".\n")
    assert result.exit_code == 0, result.stdout
    assert "✗ brief: line" in result.stdout and "kept as gaps" in result.stdout
    out = json.loads((_session_files(app_cfg) / "stages" / "01-clarify.json").read_text())
    (q,) = out["output"]["qa"]
    assert "## Evidence › ### Demand didn't parse" in q["question"]
    assert out["output"]["open"] == [q["id"]] and out["calls"] == []


def test_new_without_input_and_without_a_terminal(app_cfg: Config) -> None:
    result = runner.invoke(cli.app, ["new"])
    assert result.exit_code == 1 and "tabmill new -" in result.stdout


def test_new_rejects_two_inputs(app_cfg: Config, tmp_path: Path) -> None:
    f = tmp_path / "b.md"
    f.write_text(FULL)
    result = runner.invoke(cli.app, ["new", "some idea", "--brief", str(f)])
    assert result.exit_code == 1 and "one way" in result.stdout


def test_bare_new_on_a_terminal_reads_pasted_text(
    app_cfg: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "_tty", lambda: True)
    result = runner.invoke(cli.app, ["new", "--non-interactive"], input=FULL + ".\n")
    assert result.exit_code == 0, result.stdout
    assert "Paste a Tabmill brief" in result.stdout and "brief saved verbatim" in result.stdout
