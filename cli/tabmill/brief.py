"""Tabmill brief v1 (D-040, `docs/prd.md` § v2): the paste format a claude.ai research session
produces. Parsed section by section: a broken section is reported with its line and kept out,
everything else that parsed is kept, so the operator never re-pastes to fix one section.

Provenance: an evidence row with a source URL is `external`; without one it is downgraded to
`synthesis`. Proposal and Answers are `external_suggestion` — later stages still check them."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .provenance import Fact

SCHEMA_FILE = "schemas/brief_v1.schema.json"
SECTIONS = ("Idea", "Answers", "Proposal", "Evidence", "Risks", "Open questions")
EVIDENCE_TABLES = ("Demand", "Store competition")
ANSWER_FIELDS = ("target_user", "core_action", "trigger", "pages_touched", "done_looks_like")
TRIGGERS = ("toolbar", "shortcut", "context_menu", "side_panel")
_EMPTY = {"", "…", "...", "-", "—", "n/a", "na", "unknown", "?", "tbd"}


class Meta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tabmill_brief: Literal[1]
    idea: str
    author: str = ""
    created: str = ""


class Answers(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_user: str = ""
    core_action: str = ""
    trigger: Literal["", "toolbar", "shortcut", "context_menu", "side_panel"] = ""
    pages_touched: str = ""
    done_looks_like: str = ""


class Permission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    why: str = ""


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    single_purpose: str = ""
    template: str = ""  # popup | side-panel | maps-overlay | page-overlay | none-fits (reason)
    permissions: list[Permission] = Field(default_factory=list)
    slug_candidates: list[str] = Field(default_factory=list)
    store_name: str = ""
    summary: str = ""
    keywords: list[str] = Field(default_factory=list)
    portfolio_site: str = ""
    cta: str = ""


class DemandRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    keyword: str
    monthly_us_searches: int | None = None
    difficulty: str = ""
    source: str = ""
    date: str = ""


class CompetitionRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    extension: str
    users: int | None = None
    rating: float | None = None
    ratings_count: int | None = None
    last_updated: str = ""
    url: str = ""


class Brief(BaseModel):
    model_config = ConfigDict(extra="forbid")
    meta: Meta | None = None
    idea: str = ""
    answers: Answers = Answers()
    proposal: Proposal = Proposal()
    demand: list[DemandRow] = Field(default_factory=list)
    competition: list[CompetitionRow] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


@dataclass
class Problem:
    line: int  # 1-based, in the pasted text
    section: str  # "## Evidence › ### Demand"
    message: str

    def __str__(self) -> str:
        return f"line {self.line}, section {self.section}: {self.message}"


@dataclass
class Parsed:
    brief: Brief
    problems: list[Problem] = field(default_factory=list)
    present: list[str] = field(default_factory=list)  # sections found (incl. Evidence tables)

    @property
    def broken(self) -> list[str]:
        return sorted({p.section for p in self.problems})


def json_schema() -> str:
    return json.dumps(Brief.model_json_schema(), indent=2) + "\n"


def is_brief(text: str) -> bool:
    lines = [x for x in text.splitlines() if x.strip()]
    if not lines or lines[0].strip() != "---":
        return False
    for x in lines[1:]:
        if x.strip() == "---":
            return False
        if x.startswith("tabmill_brief:"):
            return True
    return False


def _blank(value: str) -> bool:
    v = value.strip().lower()
    return v in _EMPTY or bool(re.fullmatch(r"<[^>]*>", v))  # template placeholder like <why>


def _clean(value: str) -> str:
    return "" if _blank(value) else value.strip()


def _first_error(e: ValidationError) -> str:
    err = e.errors()[0]
    where = ".".join(str(x) for x in err["loc"])
    return f"{where}: {err['msg']}" if where else str(err["msg"])


# --- sections -----------------------------------------------------------------------------

Lines = list[tuple[int, str]]  # (1-based line number, text)


def _split(lines: Lines, prefix: str) -> tuple[Lines, list[tuple[str, int, Lines]]]:
    """Lines before the first heading, then (title, heading line, body) per heading."""
    head: Lines = []
    out: list[tuple[str, int, Lines]] = []
    for n, x in lines:
        if x.startswith(prefix) and not x.startswith(prefix + "#"):
            out.append((x[len(prefix) :].strip(), n, []))
        elif out:
            out[-1][2].append((n, x))
        else:
            head.append((n, x))
    return head, out


def _text(body: Lines) -> str:
    return "\n".join(x for _, x in body).strip()


def _bullets(body: Lines) -> list[str]:
    items = [x.strip()[2:].strip() for _, x in body if x.strip().startswith(("- ", "* "))]
    return [i for i in items if not _blank(i)]


def _answers(body: Lines, sec: str, problems: list[Problem]) -> Answers:
    data: dict[str, str] = {}
    for n, x in body:
        if not x.strip():
            continue
        key, sep, value = x.partition(":")
        key = key.strip().lstrip("-* ").strip()
        if not sep or key not in ANSWER_FIELDS:
            problems.append(Problem(n, sec, f"expected one of {', '.join(ANSWER_FIELDS)}: …"))
            continue
        v = _clean(value)
        if key == "trigger" and v and v not in TRIGGERS:
            if "|" in v:
                v = ""  # the template's option list left in place = not answered
            else:
                problems.append(Problem(n, sec, f"trigger must be one of {', '.join(TRIGGERS)}"))
                continue
        data[key] = v
    return Answers.model_validate(data)


_LISTS = ("permissions", "slug_candidates", "keywords")


def _unquote(v: str) -> str:
    v = v.strip()
    return v[1:-1] if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'" else v


def _items(v: str) -> list[str]:
    parts = v.strip().removeprefix("[").removesuffix("]").split(",")
    return [_unquote(x) for x in parts if not _blank(_unquote(x))]


def _proposal(body: Lines, sec: str, problems: list[Problem]) -> Proposal:
    """Line-based, not YAML: AI-written values often contain `: ` and would break a YAML load."""
    data: dict[str, Any] = {}
    current: str | None = None
    for n, x in body:
        if not x.strip():
            continue
        if not x.startswith((" ", "\t", "-")):
            key, sep, value = x.partition(":")
            key = key.strip()
            current = None
            if not sep or key not in Proposal.model_fields:
                problems.append(
                    Problem(
                        n,
                        sec,
                        f"unknown key {key!r} — expected one of {', '.join(Proposal.model_fields)}",
                    )
                )
                continue
            value = _unquote(value)
            if key in _LISTS:
                data[key] = [] if key == "permissions" else _items(value)
                current = key if not value.strip() or key == "permissions" else None
            else:
                data[key] = _clean(value)
            continue
        item = x.strip()
        if not item.startswith(("- ", "* ")) or current is None:
            problems.append(
                Problem(n, sec, "list item outside permissions / slug_candidates / keywords")
            )
            continue
        item = _unquote(item[2:])
        if current == "permissions":
            name, _, why = item.partition(":")
            if not _blank(name):
                data[current].append({"name": name.strip(), "why": _clean(why)})
        elif not _blank(item):
            data[current].append(item)
    return Proposal.model_validate(data)


def _number(cell: str, kind: type[int] | type[float]) -> int | float | None:
    v = cell.strip().lower().replace(",", "").replace("+", "")
    if _blank(v):
        return None
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([km]?)", v)
    if not m:
        raise ValueError(f"{cell.strip()!r} is not a number")
    n = float(m.group(1)) * {"": 1, "k": 1_000, "m": 1_000_000}[m.group(2)]
    return kind(n)


def _table(
    body: Lines, sec: str, model: type[DemandRow] | type[CompetitionRow], problems: list[Problem]
) -> list[Any]:
    rows = [(n, x.strip()) for n, x in body if x.strip().startswith("|")]
    if not rows:
        return []
    cols = [c.strip() for c in rows[0][1].strip("|").split("|")]
    want = list(model.model_fields)
    if cols != want:
        problems.append(Problem(rows[0][0], sec, f"columns must be: {' | '.join(want)}"))
        return []
    out = []
    for n, x in rows[1:]:
        cells = [c.strip() for c in x.strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", c) for c in cells):
            continue  # separator
        if all(_blank(c) for c in cells):
            continue  # the template's empty row
        if len(cells) != len(cols):
            problems.append(Problem(n, sec, f"{len(cells)} cells, expected {len(cols)}"))
            continue
        data: dict[str, Any] = {}
        try:
            for col, cell in zip(cols, cells, strict=True):
                ann = model.model_fields[col].annotation
                if ann == int | None:
                    data[col] = _number(cell, int)
                elif ann == float | None:
                    data[col] = _number(cell, float)
                else:
                    data[col] = _clean(cell)
            out.append(model.model_validate(data))
        except (ValueError, ValidationError) as e:
            msg = _first_error(e) if isinstance(e, ValidationError) else str(e)
            problems.append(Problem(n, sec, msg))
    return out


def parse(text: str) -> Parsed:
    lines: Lines = list(enumerate(text.splitlines(), 1))
    problems: list[Problem] = []
    present: list[str] = []
    brief = Brief()
    # front matter
    body_start = 0
    nonblank = [(n, x) for n, x in lines if x.strip()]
    if nonblank and nonblank[0][1].strip() == "---":
        first = nonblank[0][0]
        end = next((n for n, x in lines if n > first and x.strip() == "---"), None)
        if end is None:
            problems.append(Problem(first, "front matter", "no closing `---`"))
        else:
            body_start = end
            fm = "\n".join(x for n, x in lines if first < n < end)
            try:
                raw = yaml.safe_load(fm) or {}
                if not isinstance(raw, dict):
                    raise ValueError("expected `key: value` lines")
                # YAML reads `created: 2026-10-16` as a date; the schema keeps strings
                brief.meta = Meta.model_validate(
                    {k: v if k == "tabmill_brief" else str(v) for k, v in raw.items()}
                )
                present.append("front matter")
            except yaml.YAMLError as e:
                problems.append(Problem(first, "front matter", f"not valid YAML ({e})"))
            except ValidationError as e:
                problems.append(Problem(first, "front matter", _first_error(e)))
            except ValueError as e:
                problems.append(Problem(first, "front matter", str(e)))
    else:
        problems.append(Problem(1, "front matter", "a brief starts with `---` front matter"))
    _, sections = _split([(n, x) for n, x in lines if n > body_start], "## ")
    for title, at, body in sections:
        sec = f"## {title}"
        if title not in SECTIONS:
            problems.append(Problem(at, sec, f"unknown section (expected {', '.join(SECTIONS)})"))
            continue
        if title in present:
            problems.append(Problem(at, sec, "section appears twice; the first one is kept"))
            continue
        present.append(title)
        if title == "Idea":
            brief.idea = _text(body)
        elif title == "Answers":
            brief.answers = _answers(body, sec, problems)
        elif title == "Proposal":
            brief.proposal = _proposal(body, sec, problems)
        elif title == "Risks":
            brief.risks = _bullets(body)
        elif title == "Open questions":
            brief.open_questions = _bullets(body)
        else:  # Evidence
            _, tables = _split(body, "### ")
            for sub, sub_at, sub_body in tables:
                ssec = f"{sec} › ### {sub}"
                if sub == "Demand":
                    brief.demand = _table(sub_body, ssec, DemandRow, problems)
                elif sub == "Store competition":
                    brief.competition = _table(sub_body, ssec, CompetitionRow, problems)
                else:
                    problems.append(
                        Problem(sub_at, ssec, "expected ### Demand or ### Store competition")
                    )
                    continue
                present.append(f"Evidence › {sub}")
    return Parsed(brief, problems, present)


# --- provenance ---------------------------------------------------------------------------


def _sourced(url: str) -> bool:
    return url.startswith(("http://", "https://"))


def facts(parsed: Parsed) -> list[Fact]:
    b = parsed.brief
    author = b.meta.author if b.meta and b.meta.author else "brief"
    when = b.meta.created if b.meta else ""
    src = f"brief ({author})"
    out: list[Fact] = []
    for name in ANSWER_FIELDS:
        value = getattr(b.answers, name)
        if value:
            out.append(
                Fact(claim=name, value=value, source=src, date=when, kind="external_suggestion")
            )
    for name, value in b.proposal.model_dump().items():
        if value:
            shown = json.dumps(value) if isinstance(value, list) else value
            out.append(
                Fact(
                    claim=f"proposal.{name}",
                    value=shown,
                    source=src,
                    date=when,
                    kind="external_suggestion",
                )
            )
    for d in b.demand:
        out.append(
            Fact(
                claim=f"monthly US searches: {d.keyword}",
                value=d.monthly_us_searches,
                source=d.source or src,
                date=d.date or when,
                kind="external" if _sourced(d.source) else "synthesis",
            )
        )
    for c in b.competition:
        out.append(
            Fact(
                claim=f"store competitor: {c.extension}",
                value=json.dumps(
                    {
                        "users": c.users,
                        "rating": c.rating,
                        "ratings_count": c.ratings_count,
                        "last_updated": c.last_updated,
                    }
                ),
                source=c.url or src,
                date=when,
                kind="external" if _sourced(c.url) else "synthesis",
            )
        )
    return out


def downgraded(parsed: Parsed) -> list[str]:
    b = parsed.brief
    return [f"Demand: {d.keyword}" for d in b.demand if not _sourced(d.source)] + [
        f"Store competition: {c.extension}" for c in b.competition if not _sourced(c.url)
    ]


def missing(parsed: Parsed) -> list[str]:
    """What `brief check` lists as missing: sections, answer fields, proposal fields."""
    b = parsed.brief
    out = [
        f"section ## {s}"
        for s in SECTIONS
        if s not in parsed.present
        and not (s == "Evidence" and any(p.startswith("Evidence") for p in parsed.present))
    ]
    for t in EVIDENCE_TABLES:
        if f"Evidence › {t}" not in parsed.present:
            out.append(f"table ### {t}")
    if "Idea" in parsed.present and not b.idea:
        out.append("Idea: empty")
    if "Answers" in parsed.present:
        out += [f"Answers: {f}" for f in ANSWER_FIELDS if not getattr(b.answers, f)]
    if "Proposal" in parsed.present:
        out += [f"Proposal: {k}" for k, v in b.proposal.model_dump().items() if not v]
    if "Evidence › Demand" in parsed.present and not b.demand:
        out.append("Demand: no rows")
    if "Evidence › Store competition" in parsed.present and not b.competition:
        out.append("Store competition: no rows")
    return out
