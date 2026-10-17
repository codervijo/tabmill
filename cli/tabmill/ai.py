"""AI runner for the idea stage (D-040, `docs/prd.md` § v2). `claude -p` with no tools; the
reply must be one JSON object that validates against the stage's pydantic model. One repair
call, then fail with the raw reply saved. AI proposes, code decides — callers check the result.

`TABMILL_AI=replay:<dir>` serves replies from fixtures (tests, CI — no live AI);
`record:<dir>` runs live and writes them."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from . import templates

PROMPTS_DIR = "prompts"
ENV_AI = "TABMILL_AI"
DEFAULT_BUDGET_USD = 0.50  # per call; a ceiling, not an estimate of cost
DEFAULT_TIMEOUT_S = 300
INSTALL_URL = "https://docs.claude.com/en/docs/claude-code/setup"

T = TypeVar("T", bound=BaseModel)


class AIError(Exception):
    """Permanent: operator action needed (✗)."""


class AITransient(AIError):
    """Retryable: timeout and the like (↷)."""


@dataclass(frozen=True)
class Prompt:
    purpose: str
    version: int
    output_schema: str  # name of the pydantic model the reply must validate against
    body: str

    @property
    def id(self) -> str:
        return f"{self.purpose}_v{self.version}"


class Call(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purpose: str
    prompt_version: int
    model: str  # "unknown" when the CLI envelope doesn't say
    started: str
    finished: str
    cost_usd: float | None = None  # None = unknown, never guessed
    input_hash: str
    repaired: bool = False


@dataclass(frozen=True)
class Reply:
    text: str
    model: str = "unknown"
    cost_usd: float | None = None


Ask = Callable[[str], Reply]

# Every reply this process received, failed runs included — the CLI prints the total.
LEDGER: list[Reply] = []


def spent() -> str:
    """One line for the end of a command: calls, cost, model. Unknown cost stays unknown."""
    if not LEDGER:
        return "AI: no calls"
    known = [r.cost_usd for r in LEDGER if r.cost_usd is not None]
    unknown = len(LEDGER) - len(known)
    cost = f"${sum(known):.4f}" if known else "cost unknown"
    if known and unknown:
        cost += f" + {unknown} call(s) cost unknown"
    models = ", ".join(sorted({r.model for r in LEDGER}))
    return f"AI: {len(LEDGER)} call(s) · {cost} · {models}"


def prompt_path(tool_dir: Path, purpose: str, version: int) -> Path:
    return tool_dir / PROMPTS_DIR / f"{purpose}_v{version}.md"


def load_prompt(tool_dir: Path, purpose: str, version: int) -> Prompt:
    p = prompt_path(tool_dir, purpose, version)
    if not p.exists():
        raise AIError(f"prompt {p} not found")
    text = p.read_text()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise AIError(f"{p}: missing front matter (purpose, version, output_schema)")
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        raise AIError(f"{p}: front matter is not YAML ({e})") from e
    want = {"purpose": purpose, "version": version}
    if any(meta.get(k) != v for k, v in want.items()) or not meta.get("output_schema"):
        raise AIError(
            f"{p}: front matter must say purpose: {purpose}, version: {version}, "
            "output_schema: <model>"
        )
    return Prompt(purpose, version, str(meta["output_schema"]), text[m.end() :])


def input_hash(prompt: Prompt, values: dict[str, str]) -> str:
    blob = json.dumps({"prompt": prompt.id, "values": values}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def extract_json(text: str) -> str:
    """The reply's JSON object: fences stripped, else the outermost {...}."""
    fenced = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.S)
    if fenced:
        return fenced.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if 0 <= start < end else text.strip()


# --- backends -----------------------------------------------------------------------------


def live_ask(
    model: str = "", budget_usd: float = DEFAULT_BUDGET_USD, timeout_s: int = DEFAULT_TIMEOUT_S
) -> Ask:
    def ask(prompt: str) -> Reply:
        if not shutil.which("claude"):
            raise AIError(f"claude CLI not found — install Claude Code: {INSTALL_URL}")
        cmd = [
            "claude",
            "-p",
            prompt,
            "--output-format",
            "json",
            "--allowedTools",
            "",
            "--max-budget-usd",
            str(budget_usd),
        ]
        if model:
            cmd += ["--model", model]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout_s, check=False
            )
        except subprocess.TimeoutExpired as e:
            raise AITransient(f"claude timed out after {timeout_s}s — re-run to retry") from e
        except OSError as e:
            raise AIError(f"claude failed to start ({e})") from e
        out = proc.stdout.strip()
        try:
            env: dict[str, Any] = json.loads(out) if out.startswith("{") else {}
        except json.JSONDecodeError:
            env = {}
        if not env:
            raise AIError(
                f"claude exited {proc.returncode}: {(proc.stderr or proc.stdout).strip()[:300]}"
            )
        cost = env.get("total_cost_usd")
        cost_usd = float(cost) if isinstance(cost, int | float) else None
        if env.get("is_error"):
            raise AIError(
                f"claude returned an error ({env.get('subtype') or 'is_error'}): "
                f"{str(env.get('result') or '')[:300]}"
            )
        usage = env.get("modelUsage")
        used = model or (next(iter(usage)) if isinstance(usage, dict) and usage else "unknown")
        text = str(env.get("result") or "")
        if not text:
            raise AIError("claude returned an empty result")
        return Reply(text, used, cost_usd)

    return ask


def fixture_path(fixtures: Path, prompt: Prompt, ihash: str) -> Path:
    return fixtures / f"{prompt.id}-{ihash}.json"


def replay_ask(fixtures: Path, prompt: Prompt, ihash: str) -> Ask:
    path = fixture_path(fixtures, prompt, ihash)
    if not path.exists():
        raise AIError(f"no AI fixture {path} — record it with {ENV_AI}=record:{fixtures}")
    data = json.loads(path.read_text())
    replies = list(data["replies"])

    def ask(_prompt: str) -> Reply:
        if not replies:
            raise AIError(f"AI fixture {path} has no reply left for this call")
        return Reply(str(replies.pop(0)), str(data.get("model", "replay")), None)

    return ask


def recording(inner: Ask, fixtures: Path, prompt: Prompt, ihash: str) -> Ask:
    path = fixture_path(fixtures, prompt, ihash)
    seen: list[str] = []
    models: list[str] = []

    def ask(text: str) -> Reply:
        reply = inner(text)
        seen.append(reply.text)
        models.append(reply.model)
        fixtures.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"model": models[0], "replies": seen}, indent=2) + "\n")
        return reply

    return ask


def backend(prompt: Prompt, ihash: str, *, model: str = "") -> Ask:
    mode = os.environ.get(ENV_AI, "")
    kind, _, where = mode.partition(":")
    if kind == "replay" and where:
        return replay_ask(Path(where), prompt, ihash)
    if kind == "record" and where:
        return recording(live_ask(model), Path(where), prompt, ihash)
    if mode:
        raise AIError(f"{ENV_AI}={mode!r} — use replay:<dir>, record:<dir>, or unset it")
    return live_ask(model)


# --- the runner ---------------------------------------------------------------------------


def _repair_prompt(original: str, reply: str, errors: str) -> str:
    return (
        f"{original}\n\n---\nYour previous reply:\n\n{reply}\n\n"
        f"It failed validation:\n\n{errors}\n\n"
        "Reply again with only the corrected JSON object — no prose, no code fences."
    )


def _validate(model_cls: type[T], text: str) -> T:
    return model_cls.model_validate_json(extract_json(text))


def run(
    prompt: Prompt,
    values: dict[str, str],
    model_cls: type[T],
    raw_dir: Path,
    *,
    model: str = "",
    ask: Ask | None = None,
) -> tuple[T, Call]:
    """Render, ask, validate; one repair; else raise AIError naming the saved raw reply."""
    if prompt.output_schema != model_cls.__name__:
        raise AIError(
            f"{prompt.id} declares output_schema {prompt.output_schema}, "
            f"caller expects {model_cls.__name__}"
        )
    ihash = input_hash(prompt, values)
    schema = json.dumps(model_cls.model_json_schema(), indent=1)
    text = templates.render(prompt.body, {**values, "schema": schema})
    ask = ask or backend(prompt, ihash, model=model)
    started = _now()
    first = ask(text)
    LEDGER.append(first)
    replies = [first]
    try:
        result, repaired = _validate(model_cls, first.text), False
    except ValidationError as e:
        second = ask(_repair_prompt(text, first.text, str(e)))
        LEDGER.append(second)
        replies.append(second)
        try:
            result, repaired = _validate(model_cls, second.text), True
        except ValidationError as e2:
            raw_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
            raw = raw_dir / f"{prompt.purpose}-{stamp}.txt"
            raw.write_text(
                "\n\n=== reply 1 ===\n"
                + first.text
                + "\n\n=== reply 2 (repair) ===\n"
                + second.text
                + "\n\n=== errors ===\n"
                + str(e2)
                + "\n"
            )
            raise AIError(
                f"{prompt.id}: reply failed validation twice — raw saved to {raw}"
            ) from e2
    costs = [r.cost_usd for r in replies]
    call = Call(
        purpose=prompt.purpose,
        prompt_version=prompt.version,
        model=replies[-1].model,
        started=started,
        finished=_now(),
        cost_usd=None if None in costs else sum(c for c in costs if c is not None),
        input_hash=ihash,
        repaired=repaired,
    )
    return result, call
