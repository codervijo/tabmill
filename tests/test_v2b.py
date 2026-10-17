"""v2.B: AI runner (replay/record, validation, repair, raw on failure), stage engine (sessions,
resume, staleness), clarify_v1 (2-round cap, non-interactive opens, Q&A saved), `new "idea"`."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel
from typer.testing import CliRunner

from tabmill import ai, cli
from tabmill.config import TOOL_DIR, Config
from tabmill.idea import engine
from tabmill.idea import stages as idea_stages
from tabmill.idea.stages import clarify

runner = CliRunner()
GOLDEN = TOOL_DIR / "tests" / "fixtures" / "ai"


class Pair(BaseModel):
    a: int
    b: str


@pytest.fixture
def prompt(tool_dir: Path) -> ai.Prompt:
    p = tool_dir / "prompts" / "pair_v1.md"
    p.write_text(
        "---\npurpose: pair\nversion: 1\noutput_schema: Pair\n---\nGive {{x}}.\n{{schema}}"
    )
    return ai.load_prompt(tool_dir, "pair", 1)


def _fixture(fixtures: Path, prompt: ai.Prompt, values: dict[str, str], *replies: str) -> None:
    fixtures.mkdir(parents=True, exist_ok=True)
    path = ai.fixture_path(fixtures, prompt, ai.input_hash(prompt, values))
    path.write_text(json.dumps({"model": "fixture-model", "replies": list(replies)}))


def _replay(monkeypatch: pytest.MonkeyPatch, fixtures: Path) -> None:
    monkeypatch.setenv(ai.ENV_AI, f"replay:{fixtures}")


# --- ai.py --------------------------------------------------------------------------------


def test_replay_hit(prompt: ai.Prompt, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _fixture(tmp_path / "fx", prompt, {"x": "1"}, 'Sure:\n```json\n{"a": 1, "b": "x"}\n```')
    _replay(monkeypatch, tmp_path / "fx")
    result, call = ai.run(prompt, {"x": "1"}, Pair, tmp_path / "raw")
    assert result == Pair(a=1, b="x")
    assert (call.model, call.cost_usd, call.repaired) == ("fixture-model", None, False)


def test_replay_miss_names_the_fixture(
    prompt: ai.Prompt, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _replay(monkeypatch, tmp_path / "fx")
    with pytest.raises(ai.AIError, match="no AI fixture .*record:"):
        ai.run(prompt, {"x": "1"}, Pair, tmp_path / "raw")


def test_repair_success(prompt: ai.Prompt, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _fixture(tmp_path / "fx", prompt, {"x": "1"}, '{"a": "no"}', '{"a": 2, "b": "y"}')
    _replay(monkeypatch, tmp_path / "fx")
    result, call = ai.run(prompt, {"x": "1"}, Pair, tmp_path / "raw")
    assert result.a == 2 and call.repaired
    assert not (tmp_path / "raw").exists()


def test_repair_failure_saves_raw(
    prompt: ai.Prompt, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fixture(tmp_path / "fx", prompt, {"x": "1"}, "not json", '{"a": "still no"}')
    _replay(monkeypatch, tmp_path / "fx")
    with pytest.raises(ai.AIError, match="raw saved"):
        ai.run(prompt, {"x": "1"}, Pair, tmp_path / "raw")
    (raw,) = (tmp_path / "raw").iterdir()
    assert "not json" in raw.read_text() and "still no" in raw.read_text()


def test_repair_prompt_carries_the_errors(prompt: ai.Prompt, tmp_path: Path) -> None:
    seen: list[str] = []

    def ask(text: str) -> ai.Reply:
        seen.append(text)
        return ai.Reply('{"a": 1}' if len(seen) == 1 else '{"a": 1, "b": "z"}')

    ai.run(prompt, {"x": "1"}, Pair, tmp_path / "raw", ask=ask)
    assert "Give 1." in seen[0] and '"properties"' in seen[0]  # schema rendered in
    assert "failed validation" in seen[1] and "b" in seen[1]


def test_claude_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tabmill.ai.shutil.which", lambda _: None)
    with pytest.raises(ai.AIError, match="claude CLI not found"):
        ai.live_ask()("hi")


def test_timeout_is_transient(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tabmill.ai.shutil.which", lambda _: "/bin/claude")

    def slow(*_: Any, **__: Any) -> None:
        raise subprocess.TimeoutExpired("claude", 1)

    monkeypatch.setattr("tabmill.ai.subprocess.run", slow)
    with pytest.raises(ai.AITransient, match="re-run"):
        ai.live_ask(timeout_s=1)("hi")


def test_live_reads_the_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tabmill.ai.shutil.which", lambda _: "/bin/claude")
    calls: list[list[str]] = []

    def fake(cmd: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        env = {"result": "{}", "total_cost_usd": 0.01, "modelUsage": {"claude-x": {}}}
        return subprocess.CompletedProcess(cmd, 0, json.dumps(env), "")

    monkeypatch.setattr("tabmill.ai.subprocess.run", fake)
    reply = ai.live_ask()("hi")
    assert (reply.model, reply.cost_usd) == ("claude-x", 0.01)
    assert calls[0][calls[0].index("--allowedTools") + 1] == ""  # no tool use


def test_record_writes_a_replayable_fixture(
    prompt: ai.Prompt, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ai, "live_ask", lambda *_, **__: lambda _t: ai.Reply('{"a":3,"b":"r"}'))
    monkeypatch.setenv(ai.ENV_AI, f"record:{tmp_path / 'fx'}")
    ai.run(prompt, {"x": "1"}, Pair, tmp_path / "raw")
    _replay(monkeypatch, tmp_path / "fx")
    assert ai.run(prompt, {"x": "1"}, Pair, tmp_path / "raw")[0].a == 3


def test_prompt_front_matter_is_checked(tool_dir: Path) -> None:
    (tool_dir / "prompts" / "bad_v1.md").write_text("---\npurpose: other\nversion: 1\n---\nx")
    with pytest.raises(ai.AIError, match="front matter"):
        ai.load_prompt(tool_dir, "bad", 1)


def test_real_prompts_load() -> None:
    assert ai.load_prompt(TOOL_DIR, "clarify", 1).output_schema == "ClarifyReply"


# --- engine + clarify ---------------------------------------------------------------------

IDEA = "count words on any page"
Q_TRIGGER = {"about": "trigger", "text": "How do people start it?", "choices": ["toolbar", "key"]}
Q_PAGES = {"about": "pages", "text": "Which pages?", "choices": []}
Q_USER = {"about": "target_user", "text": "Who is it for?", "choices": ["writers", "students"]}
Q_DONE = {"about": "done_looks_like", "text": "What does done look like?", "choices": []}


def _reply(known: dict[str, str], *questions: dict[str, Any]) -> str:
    return json.dumps({"known": known, "questions": list(questions)})


def _clarify_fixture(fx: Path, tool_dir: Path, qa: list[clarify.QA], rnd: int, reply: str) -> None:
    p = ai.load_prompt(tool_dir, "clarify", 1)
    _fixture(fx, p, clarify.values(IDEA, qa, rnd), reply)


def _qa(*items: tuple[dict[str, Any], str, int, int]) -> list[clarify.QA]:
    return [
        clarify.QA(
            id=f"r{r}q{i}",
            round=r,
            about=q["about"],
            question=q["text"],
            choices=q["choices"],
            answer=a,
        )
        for q, a, r, i in items
    ]


def _ctx(tool_dir: Path, answers: list[str] | None) -> engine.Context:
    session = engine.create(tool_dir, IDEA)
    it = iter(answers or [])
    ask = (lambda _q: next(it)) if answers is not None else None
    return engine.Context(tool_dir, session, ask, today="2026-10-16")


def test_clarify_two_rounds_then_stops(tool_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fx = tool_dir / "fx"
    known = {"core_action": "count words"}
    _clarify_fixture(fx, tool_dir, [], 1, _reply(known, Q_TRIGGER, Q_PAGES))
    r1 = _qa((Q_TRIGGER, "toolbar", 1, 1), (Q_PAGES, "any page", 1, 2))
    _clarify_fixture(fx, tool_dir, r1, 2, _reply(known, Q_USER, Q_DONE))
    _replay(monkeypatch, fx)
    ctx = _ctx(tool_dir, ["toolbar", "any page", "writers", ""])
    (rec,) = engine.run(ctx, [clarify.Clarify()])
    out = rec.output
    assert out["rounds"] == 2 and len(rec.calls) == 2  # no third call, no third round
    assert [q["answer"] for q in out["qa"]] == ["toolbar", "any page", "writers", ""]
    assert out["open"] == ["r2q2"]
    assert {f["kind"] for f in out["facts"]} == {"user"} and len(out["facts"]) == 3
    saved = engine.read_stage(tool_dir, ctx.session.id, "clarify")
    assert saved is not None and saved.output == out
    assert engine.stage_file(tool_dir, ctx.session.id, "clarify").name == "01-clarify.json"


def test_clarify_drops_questions_about_known_fields(
    tool_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = tool_dir / "fx"
    known = {"trigger": "toolbar button"}
    _clarify_fixture(fx, tool_dir, [], 1, _reply(known, Q_TRIGGER))  # asks anyway
    _replay(monkeypatch, fx)
    (rec,) = engine.run(_ctx(tool_dir, []), [clarify.Clarify()])
    assert rec.output["qa"] == [] and rec.output["rounds"] == 0 and len(rec.calls) == 1


def test_clarify_non_interactive_records_open_questions(
    tool_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = tool_dir / "fx"
    _clarify_fixture(fx, tool_dir, [], 1, _reply({}, Q_TRIGGER, Q_PAGES))
    _replay(monkeypatch, fx)
    (rec,) = engine.run(_ctx(tool_dir, None), [clarify.Clarify()])
    assert rec.output["open"] == ["r1q1", "r1q2"] and rec.output["facts"] == []
    assert len(rec.calls) == 1


def test_engine_resume_replays_and_rerun_marks_downstream_stale(
    tool_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = tool_dir / "fx"
    _clarify_fixture(fx, tool_dir, [], 1, _reply({}))
    _replay(monkeypatch, fx)
    ctx = _ctx(tool_dir, None)
    steps: list[tuple[str, str]] = []
    engine.run(ctx, [clarify.Clarify()], on_step=lambda n, w: steps.append((n, w)))
    later = engine.StageRecord(stage="shape", kind="ai", input_hash="x", created="t", output={})
    engine.write_stage(tool_dir, ctx.session.id, later)
    engine.run(ctx, [clarify.Clarify()], on_step=lambda n, w: steps.append((n, w)))
    assert steps == [("clarify", "ran"), ("clarify", "recorded")]
    engine.run(ctx, [clarify.Clarify()], only="clarify", on_step=lambda n, w: steps.append((n, w)))
    assert steps[-1] == ("clarify", "ran · marked stale: shape")
    shape = engine.read_stage(tool_dir, ctx.session.id, "shape")
    assert shape is not None and shape.stale


def test_engine_rejects_an_unbuilt_stage(tool_dir: Path) -> None:
    with pytest.raises(engine.IdeaError, match="v2.F"):
        engine.run(_ctx(tool_dir, None), [clarify.Clarify()], only="verdict")


def test_ids_are_dated_and_unique(tool_dir: Path) -> None:
    a = engine.create(tool_dir, "Count words, on ANY page!")
    b = engine.create(tool_dir, "Count words, on ANY page!")
    assert a.id.endswith("-count-words-on-any") and b.id == a.id + "-2"
    assert engine.load(tool_dir, a.id).text == "Count words, on ANY page!"
    assert engine.latest(tool_dir) == b.id


# --- CLI ----------------------------------------------------------------------------------


@pytest.fixture
def app_cfg(cfg: Config, monkeypatch: pytest.MonkeyPatch) -> Config:
    cfg.workspace.mkdir(parents=True)
    monkeypatch.setattr(cli, "_load", lambda *_: cfg)
    # these tests cover clarify; shape/check (v2.D) have their own tests
    monkeypatch.setattr(idea_stages, "REGISTERED", (clarify.Clarify(),))
    return cfg


def test_cli_rough_idea_interactive(app_cfg: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    fx = app_cfg.tool_dir / "fx"
    _clarify_fixture(fx, app_cfg.tool_dir, [], 1, _reply({}, Q_TRIGGER))
    _clarify_fixture(fx, app_cfg.tool_dir, _qa((Q_TRIGGER, "toolbar", 1, 1)), 2, _reply({}))
    _replay(monkeypatch, fx)
    monkeypatch.setattr(cli, "_tty", lambda: True)
    result = runner.invoke(cli.app, ["new", *IDEA.split()], input="1\n")
    assert result.exit_code == 0, result.stdout
    assert "1 answered, 0 open" in result.stdout and "v2.F" in result.stdout
    (idea,) = (app_cfg.tool_dir / "ideas").iterdir()
    rec = json.loads((idea / "stages" / "01-clarify.json").read_text())
    assert rec["output"]["qa"][0]["answer"] == "toolbar"  # choice 1, saved verbatim


def test_cli_non_interactive_then_resume_and_rerun(
    app_cfg: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = app_cfg.tool_dir / "fx"
    _clarify_fixture(fx, app_cfg.tool_dir, [], 1, _reply({}, Q_TRIGGER))
    _replay(monkeypatch, fx)
    first = runner.invoke(cli.app, ["new", IDEA, "--non-interactive"])
    assert first.exit_code == 0 and "1 open" in first.stdout
    idea_id = engine.latest(app_cfg.tool_dir)
    again = runner.invoke(cli.app, ["new", "--resume", idea_id, "--non-interactive"])
    assert again.exit_code == 0 and "recorded, skipping" in again.stdout
    rerun = runner.invoke(cli.app, ["new", "clarify", "--non-interactive"])
    assert rerun.exit_code == 0 and "clarify: ran" in rerun.stdout


def test_cli_ai_failure_is_red(app_cfg: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    _replay(monkeypatch, app_cfg.tool_dir / "empty")
    result = runner.invoke(cli.app, ["new", IDEA, "--non-interactive"])
    assert result.exit_code == 1 and "✗ no AI fixture" in result.stdout


def test_cli_no_idea(app_cfg: Config) -> None:
    result = runner.invoke(cli.app, ["new"])
    assert result.exit_code == 1 and "describe the idea" in result.stdout


# --- golden: a recorded live run -----------------------------------------------------------


@pytest.mark.skipif(not GOLDEN.exists(), reason="no recorded golden fixtures yet")
def test_golden_rough_idea_replays(app_cfg: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    meta = json.loads((GOLDEN / "golden.json").read_text())
    _replay(monkeypatch, GOLDEN)
    result = runner.invoke(cli.app, ["new", meta["idea"], "--non-interactive"])
    assert result.exit_code == 0, result.stdout
    rec = json.loads(
        next((app_cfg.tool_dir / "ideas").glob("*/stages/01-clarify.json")).read_text()
    )
    assert len(rec["output"]["open"]) == meta["open"]


def test_cost_line_after_every_ai_command(app_cfg: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    fx = app_cfg.tool_dir / "fx"
    _clarify_fixture(fx, app_cfg.tool_dir, [], 1, _reply({}, Q_TRIGGER))
    _replay(monkeypatch, fx)
    first = runner.invoke(cli.app, ["new", IDEA, "--non-interactive"])
    assert "AI: 1 call(s) · cost unknown · fixture-model" in first.stdout
    again = runner.invoke(cli.app, ["new", "--resume", engine.latest(app_cfg.tool_dir)])
    assert "AI: no calls" in again.stdout
    failed = runner.invoke(cli.app, ["new", "other idea", "--non-interactive"])
    assert failed.exit_code == 1 and "AI: no calls" in failed.stdout


def test_spent_sums_known_costs() -> None:
    ai.LEDGER[:] = [ai.Reply("x", "m", 0.1), ai.Reply("y", "m", 0.2), ai.Reply("z", "m")]
    assert ai.spent() == "AI: 3 call(s) · $0.3000 + 1 call(s) cost unknown · m"
    ai.LEDGER.clear()
