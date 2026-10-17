"""clarify_v1 (`docs/prd.md` § v2). The AI says what the idea already states and asks only
about what's missing; code drops questions about known fields, caps them per round, and stops
after 2 rounds. Answers are kept verbatim as `user` facts; unanswered questions stay open and
later stages carry them as assumptions."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ... import ai, brief
from ...provenance import Fact
from ..engine import Context, Question, Result, StageKind

PURPOSE, VERSION = "clarify", 1
MAX_ROUNDS = 2
MAX_QUESTIONS = 5
FIELDS = ("target_user", "core_action", "trigger", "pages", "done_looks_like")
About = Literal["target_user", "core_action", "trigger", "pages", "done_looks_like", "other"]


class Known(BaseModel):
    """What the idea (plus answers so far) already states; "" = not stated."""

    model_config = ConfigDict(extra="forbid")
    target_user: str = ""
    core_action: str = ""
    trigger: str = ""  # toolbar | shortcut | context_menu | side_panel, or words
    pages: str = ""  # which pages it works on / touches
    done_looks_like: str = ""


class AIQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    about: About
    text: str = Field(min_length=3)
    choices: list[str] = Field(default_factory=list, max_length=6)


class ClarifyReply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    known: Known
    questions: list[AIQuestion] = Field(default_factory=list, max_length=MAX_QUESTIONS)


class QA(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    round: int
    about: About
    question: str
    choices: list[str] = Field(default_factory=list)
    answer: str = ""  # verbatim; "" = open


def values(
    text: str, qa: list[QA], rnd: int, given: dict[str, str] | None = None
) -> dict[str, str]:
    """Prompt variables — also what the AI fixture key is hashed from."""
    lines = [f"- [{k}] (from the brief) → {v}" for k, v in (given or {}).items() if v]
    lines += [f"- [{q.about}] {q.question} → {q.answer or '(skipped)'}" for q in qa]
    return {
        "idea": text.strip(),
        "answers": "\n".join(lines) or "(none yet)",
        "round": str(rnd),
        "max_rounds": str(MAX_ROUNDS),
        "max_questions": str(MAX_QUESTIONS),
    }


def _keep(q: AIQuestion, known: Known, asked: set[str]) -> bool:
    if q.about != "other" and getattr(known, q.about):
        return False  # code decides: never ask about a field already stated
    return q.text.strip().lower() not in asked


class Clarify:
    name = PURPOSE
    kind: StageKind = "ai"
    needs: tuple[str, ...] = ()

    def inputs(self, ctx: Context) -> dict[str, Any]:
        return {"prompt": f"{PURPOSE}_v{VERSION}"}

    def run(self, ctx: Context) -> Result:
        prompt = ai.load_prompt(ctx.tool_dir, PURPOSE, VERSION)
        seed, idea_text, code_qs, seed_facts = _from_input(ctx)
        given = {k: v for k, v in seed.model_dump().items() if v}
        need_ai = any(not getattr(seed, f) for f in FIELDS)
        qa: list[QA] = []
        calls: list[ai.Call] = []
        known = seed
        rounds = 0
        for rnd in range(1, MAX_ROUNDS + 1):
            asked = {q.question.strip().lower() for q in qa}
            new: list[AIQuestion] = list(code_qs) if rnd == 1 else []
            if need_ai:
                reply, call = ai.run(
                    prompt,
                    values(idea_text, qa, rnd, given or None),
                    ClarifyReply,
                    ctx.raw_dir,
                    model=ctx.ai_model,
                )
                calls.append(call)
                # code decides: what the input already states wins over the AI's reading
                known = Known.model_validate(
                    {f: getattr(seed, f) or getattr(reply.known, f) for f in FIELDS}
                )
                new += [q for q in reply.questions if _keep(q, known, asked)][:MAX_QUESTIONS]
            if not new:
                break
            rounds = rnd
            batch = [
                QA(
                    id=f"r{rnd}q{i}",
                    round=rnd,
                    about=q.about,
                    question=q.text.strip(),
                    choices=q.choices,
                )
                for i, q in enumerate(new, 1)
            ]
            qa.extend(batch)
            if ctx.ask_user is None:
                break  # non-interactive: one round of questions, all open
            for item in batch:
                item.answer = ctx.ask_user(
                    Question(id=item.id, text=item.question, choices=item.choices)
                ).strip()
            if not need_ai:
                break  # only the brief's own questions; nothing for the AI to ask
        today = ctx.today or date.today().isoformat()
        facts = seed_facts + [
            Fact(
                claim=q.question,
                value=q.answer,
                source="operator (clarify)",
                date=today,
                kind="user",
            )
            for q in qa
            if q.answer
        ]
        return Result(
            output={
                "rounds": rounds,
                "known": known.model_dump(),
                "qa": [q.model_dump() for q in qa],
                "open": [q.id for q in qa if not q.answer],
                "facts": [f.model_dump() for f in facts],
            },
            calls=calls,
        )


def _from_input(ctx: Context) -> tuple[Known, str, list[AIQuestion], list[Fact]]:
    """Rough idea: nothing known yet. Brief: Answers pre-fill `known`; its Open questions and
    any section that failed to parse become questions (gap-only clarify, v2.C)."""
    if ctx.session.input_kind != "brief":
        return Known(), ctx.session.text, [], []
    parsed = brief.parse(ctx.session.text)
    b, a = parsed.brief, parsed.brief.answers
    seed = Known(
        target_user=a.target_user,
        core_action=a.core_action,
        trigger=a.trigger,
        pages=a.pages_touched,
        done_looks_like=a.done_looks_like,
    )
    text = b.idea or (b.meta.idea if b.meta else "") or ctx.session.text
    qs = [
        AIQuestion(about="other", text=f"Open question from the brief: {q}")
        for q in b.open_questions
    ]
    for sec in parsed.broken:
        first = next(p for p in parsed.problems if p.section == sec)
        qs.append(
            AIQuestion(
                about="other",
                text=f"The brief's {sec} didn't parse ({first}). "
                "What should it say? (Enter leaves it as a gap)",
            )
        )
    facts = [f for f in brief.facts(parsed) if f.claim in brief.ANSWER_FIELDS]
    return seed, text, qs, facts
