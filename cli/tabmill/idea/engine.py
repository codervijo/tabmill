"""Stage engine (`docs/prd.md` § v2). Stages run in a fixed order; each writes
`ideas/<id>/stages/NN-<stage>.json` with an input hash. A stage whose file is missing, marked
stale, or whose inputs changed runs again; anything else is replayed from its file. Re-running
a stage marks every later stage stale."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .. import ai

IDEAS_DIR = "ideas"
SESSION_FILE = "session.json"
ORDER = ("clarify", "shape", "evidence", "check", "verdict", "write")
ARRIVES = {"shape": "v2.D", "evidence": "v2.E", "check": "v2.D", "verdict": "v2.F", "write": "v2.F"}
_ID_WORDS = 4

StageKind = Literal["ai", "data", "rule", "gen"]
State = Literal["missing", "stale", "changed", "done"]


class IdeaError(Exception):
    """Idea session missing or invalid; message names the fix."""


class Session(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    created: str
    input_kind: Literal["idea", "brief"] = "idea"
    text: str  # verbatim, as the operator gave it
    non_interactive: bool = False
    template: str = ""  # operator's --template hint for shape


class StageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stage: str
    kind: StageKind
    input_hash: str
    created: str
    stale: bool = False
    calls: list[ai.Call] = Field(default_factory=list)
    output: dict[str, Any]


class Question(BaseModel):
    """What a stage asks the operator; `choices` empty = free text."""

    model_config = ConfigDict(extra="forbid")
    id: str
    text: str
    choices: list[str] = Field(default_factory=list)


AskUser = Callable[[Question], str]  # returns the answer ("" = skipped)


@dataclass
class Context:
    tool_dir: Path
    session: Session
    ask_user: AskUser | None  # None = non-interactive
    ai_model: str = ""
    today: str = ""

    @property
    def dir(self) -> Path:
        return idea_dir(self.tool_dir, self.session.id)

    @property
    def raw_dir(self) -> Path:
        return self.dir / "raw"

    def upstream(self, name: str) -> dict[str, Any]:
        rec = read_stage(self.tool_dir, self.session.id, name)
        if rec is None:
            raise IdeaError(f"stage {name} hasn't run for {self.session.id}")
        return rec.output


@dataclass
class Result:
    output: dict[str, Any]
    calls: list[ai.Call]


class Stage(Protocol):
    name: str
    kind: StageKind
    needs: tuple[str, ...]

    def inputs(self, ctx: Context) -> dict[str, Any]: ...

    def run(self, ctx: Context) -> Result: ...


# --- storage ------------------------------------------------------------------------------


def ideas_root(tool_dir: Path) -> Path:
    return tool_dir / IDEAS_DIR


def idea_dir(tool_dir: Path, idea_id: str) -> Path:
    return ideas_root(tool_dir) / idea_id


def _slugish(text: str) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())[:_ID_WORDS]
    return "-".join(words) or "idea"


def new_id(tool_dir: Path, text: str, today: date) -> str:
    base = f"{today:%Y%m%d}-{_slugish(text)}"
    n, candidate = 2, base
    while idea_dir(tool_dir, candidate).exists():
        candidate, n = f"{base}-{n}", n + 1
    return candidate


def create(
    tool_dir: Path,
    text: str,
    *,
    non_interactive: bool = False,
    template: str = "",
    today: date | None = None,
) -> Session:
    if not text.strip():
        raise IdeaError("the idea is empty — describe it in a sentence")
    when = today or date.today()
    session = Session(
        id=new_id(tool_dir, text, when),
        created=datetime.now(UTC).isoformat(timespec="seconds"),
        text=text,
        non_interactive=non_interactive,
        template=template,
    )
    save(tool_dir, session)
    return session


def save(tool_dir: Path, session: Session) -> None:
    d = idea_dir(tool_dir, session.id)
    (d / "stages").mkdir(parents=True, exist_ok=True)
    (d / SESSION_FILE).write_text(session.model_dump_json(indent=2) + "\n")


def load(tool_dir: Path, idea_id: str) -> Session:
    p = idea_dir(tool_dir, idea_id) / SESSION_FILE
    if not p.exists():
        raise IdeaError(f"no idea {idea_id} (looked for {p}) — see `ls {IDEAS_DIR}/`")
    try:
        return Session.model_validate_json(p.read_text())
    except ValidationError as e:
        raise IdeaError(f"{p}: invalid ({e})") from e


def latest(tool_dir: Path) -> str:
    """Most recently created idea id."""
    root = ideas_root(tool_dir)
    found = sorted(
        (p.parent for p in root.glob(f"*/{SESSION_FILE}")),
        key=lambda d: (d / SESSION_FILE).stat().st_mtime,
    )
    if not found:
        raise IdeaError('no ideas yet — start one with `tabmill new "<idea>"`')
    return found[-1].name


def stage_file(tool_dir: Path, idea_id: str, name: str) -> Path:
    return idea_dir(tool_dir, idea_id) / "stages" / f"{ORDER.index(name) + 1:02d}-{name}.json"


def read_stage(tool_dir: Path, idea_id: str, name: str) -> StageRecord | None:
    p = stage_file(tool_dir, idea_id, name)
    if not p.exists():
        return None
    try:
        return StageRecord.model_validate_json(p.read_text())
    except ValidationError as e:
        raise IdeaError(f"{p}: invalid ({e}) — re-run with `tabmill new {name} {idea_id}`") from e


def write_stage(tool_dir: Path, idea_id: str, rec: StageRecord) -> Path:
    p = stage_file(tool_dir, idea_id, rec.stage)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(rec.model_dump_json(indent=2) + "\n")
    return p


def mark_downstream_stale(tool_dir: Path, idea_id: str, name: str) -> list[str]:
    marked = []
    for later in ORDER[ORDER.index(name) + 1 :]:
        rec = read_stage(tool_dir, idea_id, later)
        if rec is not None and not rec.stale:
            rec.stale = True
            write_stage(tool_dir, idea_id, rec)
            marked.append(later)
    return marked


# --- running ------------------------------------------------------------------------------


def input_hash(stage: Stage, ctx: Context) -> str:
    ups = {}
    for up in stage.needs:
        rec = read_stage(ctx.tool_dir, ctx.session.id, up)
        ups[up] = rec.input_hash if rec else None
    blob = json.dumps(
        {
            "stage": stage.name,
            "session": ctx.session.text,
            "inputs": stage.inputs(ctx),
            "upstream": ups,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def state(stage: Stage, ctx: Context) -> State:
    rec = read_stage(ctx.tool_dir, ctx.session.id, stage.name)
    if rec is None:
        return "missing"
    if rec.stale:
        return "stale"
    return "done" if rec.input_hash == input_hash(stage, ctx) else "changed"


Step = Callable[[str, str], None]  # (stage, "recorded" | "ran" | "stale: …")


def run(
    ctx: Context, stages: Sequence[Stage], *, only: str | None = None, on_step: Step | None = None
) -> list[StageRecord]:
    """Run `only` (forced, then mark later stages stale), or resume: every stage that is
    missing / stale / changed, in order; the rest are replayed from their files."""
    order = {s.name: s for s in stages}
    unknown = [n for n in order if n not in ORDER]
    if unknown:
        raise IdeaError(f"unknown stage(s) {unknown}")
    if only is not None and only not in order:
        raise IdeaError(f"stage {only} isn't built yet (arrives in {ARRIVES.get(only, 'v2')})")
    out: list[StageRecord] = []
    for name in ORDER:
        stage = order.get(name)
        if stage is None:
            continue
        st = state(stage, ctx)
        forced = only == name
        if only is not None and not forced:
            rec = read_stage(ctx.tool_dir, ctx.session.id, name)
            if rec is not None:
                out.append(rec)
            continue
        if not forced and st == "done":
            rec = read_stage(ctx.tool_dir, ctx.session.id, name)
            assert rec is not None
            out.append(rec)
            if on_step:
                on_step(name, "recorded")
            continue
        ihash = input_hash(stage, ctx)
        result = stage.run(ctx)
        rec = StageRecord(
            stage=name,
            kind=stage.kind,
            input_hash=ihash,
            created=datetime.now(UTC).isoformat(timespec="seconds"),
            calls=result.calls,
            output=result.output,
        )
        write_stage(ctx.tool_dir, ctx.session.id, rec)
        marked = mark_downstream_stale(ctx.tool_dir, ctx.session.id, name)
        out.append(rec)
        if on_step:
            on_step(name, "ran" + (f" · marked stale: {', '.join(marked)}" if marked else ""))
    return out
