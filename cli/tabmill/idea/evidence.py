"""Evidence providers (`docs/prd.md` § v2). One interface: `collect(keywords, ctx)` returns a
status and facts, every fact with kind / source / date. A provider that fails soft-fails
(status `failed`, the stage goes on); missing evidence is recorded as a `missing` fact, never
filled in.

lamill gives SERP shape (top-10, AI Overview, People also ask) and a relative 0–100 trends
index — not monthly search volume and not store competition. Its volume figure is an LLM
estimate, so it is kept as `synthesis`."""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Literal, Protocol

from .. import ai, brief, catalog, extension, generate, rules
from ..provenance import Fact
from .engine import Context

Status = Literal["ok", "failed", "not available", "skipped"]
EVIDENCE_DIR = "evidence"
VALIDATE_TIMEOUT_S = 900
TRENDS_TIMEOUT_S = 120
TRENDS_KEYWORDS = 3
OVERLAP_MIN = 0.3  # report recipes at least this similar (lint warns at 0.6)

Run = Callable[[list[str], int], subprocess.CompletedProcess[str]]


def _run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


@dataclass
class Collected:
    name: str
    status: Status
    detail: str = ""
    facts: list[Fact] = field(default_factory=list)


class Provider(Protocol):
    name: str

    def collect(self, keywords: list[str], ctx: Context) -> Collected: ...


def _json(stdout: str) -> dict[str, Any]:
    start = stdout.find("{")
    if start < 0:
        raise ValueError("no JSON in output")
    data = json.loads(stdout[start:])
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object")
    return data


def _day(stamp: object) -> str:
    return str(stamp or "")[:10]


class Lamill:
    name = "lamill"

    def __init__(self, run: Run | None = None) -> None:
        self._given = run

    def run(self, cmd: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        return (self._given or _run)(cmd, timeout)  # module lookup at call time (tests patch it)

    def validate(self, keyword: str) -> Collected:
        src = "lamill new validate"
        try:
            proc = self.run(["lamill", "new", "validate", keyword, "--json"], VALIDATE_TIMEOUT_S)
            data = _json(proc.stdout)
        except subprocess.TimeoutExpired:
            return Collected(src, "failed", f"timed out after {VALIDATE_TIMEOUT_S}s")
        except (ValueError, json.JSONDecodeError) as e:
            tail = (proc.stderr or proc.stdout).strip()[-200:]
            return Collected(src, "failed", f"exit {proc.returncode}: {e}; {tail}")
        costs = data.get("costs") or {}
        if not data.get("from_cache") and isinstance(costs.get("total_usd"), int | float):
            ai.LEDGER.append(ai.Reply("", src, float(costs["total_usd"])))
        when = _day(data.get("fetched_at"))
        real = data.get("source") == "serpapi"
        kind: Literal["real", "synthesis"] = "real" if real else "synthesis"
        source = f"{src} ({'SerpAPI' if real else 'AI synthesis — NOT REAL SERP DATA'})"
        facts: list[Fact] = []
        for q in data.get("per_query_results") or []:
            query = str(q.get("query", ""))
            organic = q.get("organic_results") or []
            features = q.get("features") or {}
            facts.append(
                Fact(
                    claim=f"SERP top-10 domains: {query}",
                    value=json.dumps([r.get("domain") for r in organic[:10]]),
                    source=source,
                    date=_day(q.get("fetched_at")) or when,
                    kind=kind,
                )
            )
            aio = (features.get("ai_overview") or {}).get("present")
            if aio is not None:
                facts.append(
                    Fact(
                        claim=f"AI Overview on the SERP: {query}",
                        value=bool(aio),
                        source=source,
                        date=when,
                        kind=kind,
                    )
                )
            paa = features.get("people_also_ask")
            if isinstance(paa, list):
                facts.append(
                    Fact(
                        claim=f"People also ask: {query}",
                        value=json.dumps(paa[:8]),
                        source=source,
                        date=when,
                        kind=kind,
                    )
                )
        for err in data.get("fetch_errors") or []:
            facts.append(
                Fact(
                    claim="SERP query failed", value=str(err), source=src, date=when, kind="missing"
                )
            )
        raw = ((data.get("gates") or {}).get("gate_1_market") or {}).get("raw") or {}
        for key in ("pollution_adjusted_volume", "total_volume"):
            if isinstance(raw.get(key), int | float):
                facts.append(
                    Fact(
                        claim=f"monthly searches, {key} (lamill gate 1 LLM estimate): {keyword}",
                        value=raw[key],
                        source=src,
                        date=when,
                        kind="synthesis",
                    )
                )
        return Collected(src, "ok", f"{len(data.get('per_query_results') or [])} queries", facts)

    def trends(self, keyword: str) -> Collected:
        src = "lamill new trends"
        try:
            proc = self.run(["lamill", "new", "trends", keyword, "--json"], TRENDS_TIMEOUT_S)
            data = _json(proc.stdout)
        except subprocess.TimeoutExpired:
            return Collected(
                src,
                "failed",
                f"timed out after {TRENDS_TIMEOUT_S}s",
                [_missing_trend(keyword, "timeout")],
            )
        except (ValueError, json.JSONDecodeError) as e:
            return Collected(
                src,
                "failed",
                f"exit {proc.returncode}: {e}",
                [_missing_trend(keyword, f"exit {proc.returncode}")],
            )
        points = [
            p.get("value")
            for p in data.get("interest_over_time") or []
            if isinstance(p.get("value"), int | float)
        ]
        when = _day(data.get("fetched_at"))
        source = (
            f"Google Trends via {src} ({data.get('timeframe', '12m')}, "
            f"{data.get('region') or 'worldwide'})"
        )
        if not points:
            return Collected(src, "ok", "no data", [_missing_trend(keyword, "no data")])
        facts = [
            Fact(
                claim=f"Google Trends interest, average (relative 0–100, not volume): {keyword}",
                value=round(sum(points) / len(points), 1),
                source=source,
                date=when,
                kind="real",
            ),
            Fact(
                claim=f"Google Trends interest, latest (relative 0–100): {keyword}",
                value=points[-1],
                source=source,
                date=when,
                kind="real",
            ),
        ]
        related = [r.get("query") for r in data.get("related_top") or []][:5]
        if related:
            facts.append(
                Fact(
                    claim=f"Google Trends related queries: {keyword}",
                    value=json.dumps(related),
                    source=source,
                    date=when,
                    kind="real",
                )
            )
        return Collected(src, "ok", f"{len(points)} points", facts)

    def collect(self, keywords: list[str], ctx: Context | None = None) -> Collected:
        if self._given is None and not shutil.which("lamill"):
            return Collected(self.name, "failed", "lamill not on PATH")
        if not keywords:
            return Collected(self.name, "skipped", "no keywords")
        parts = [self.validate(keywords[0])] + [self.trends(k) for k in keywords[:TRENDS_KEYWORDS]]
        failed = [f"{p.name}: {p.detail}" for p in parts if p.status == "failed"]
        facts = [f for p in parts for f in p.facts]
        status: Status = "failed" if len(failed) == len(parts) else "ok"
        detail = "; ".join(failed) if failed else "; ".join(f"{p.name}: {p.detail}" for p in parts)
        return Collected(self.name, status, detail, facts)


def _missing_trend(keyword: str, why: str) -> Fact:
    return Fact(
        claim=f"Google Trends interest: {keyword}",
        value=None,
        source=f"lamill new trends ({why})",
        kind="missing",
    )


class Files:
    name = "files"

    def collect(self, keywords: list[str], ctx: Context) -> Collected:
        files = sorted((ctx.dir / EVIDENCE_DIR).glob("*.md"))
        if not files:
            return Collected(self.name, "skipped", "no evidence files")
        facts: list[Fact] = []
        problems: list[str] = []
        for f in files:
            parsed, collected = brief.parse_evidence(f.read_text())
            facts += brief.evidence_facts(parsed, collected, f"evidence/{f.name}")
            problems += [f"{f.name}: {p}" for p in parsed.problems]
        return Collected(self.name, "ok", "; ".join(problems) or f"{len(files)} file(s)", facts)


class Brief:
    name = "brief"

    def collect(self, keywords: list[str], ctx: Context) -> Collected:
        if ctx.session.input_kind != "brief":
            return Collected(self.name, "skipped", "not a brief")
        parsed = brief.parse(ctx.session.text)
        facts = [f for f in brief.facts(parsed) if f.kind in ("external", "synthesis")]
        return Collected(self.name, "ok", f"{len(facts)} row(s)", facts)


class Overlap:
    name = "overlap"

    def collect(self, keywords: list[str], ctx: Context) -> Collected:
        purpose = str(ctx.upstream("shape")["draft"].get("single_purpose", ""))
        facts = []
        for slug in catalog.recipe_slugs(ctx.tool_dir):
            try:
                ext = extension.load_file(
                    generate.recipe_dir(ctx.tool_dir, slug) / generate.RECIPE_FILE
                )
            except extension.ExtensionError:
                continue
            sim = rules.similarity(purpose, str(ext.get("single_purpose", "")))
            if sim >= OVERLAP_MIN:
                facts.append(
                    Fact(
                        claim=f"overlap with Lamill extension {slug}",
                        value=round(sim, 2),
                        source="tabmill (recipes/ single_purpose)",
                        date=ctx.today or date.today().isoformat(),
                        kind="real",
                    )
                )
        return Collected(self.name, "ok", f"{len(facts)} similar recipe(s)", facts)


class NotAvailable:
    """Declared for the interface; not implemented in v2."""

    def __init__(self, name: str, why: str) -> None:
        self.name, self.why = name, why

    def collect(self, keywords: list[str], ctx: Context) -> Collected:
        return Collected(self.name, "not available", self.why)


def default_providers() -> list[Provider]:
    return [
        Lamill(),
        Files(),
        Brief(),
        Overlap(),
        NotAvailable("treg", "not implemented in v2"),
        NotAvailable("store competition", "no Chrome Web Store search API; not implemented in v2"),
    ]


DEMAND_PREFIXES = ("monthly US searches: ", "Google Trends interest")


def missing(keywords: Sequence[str], facts: Sequence[Fact]) -> list[Fact]:
    """`missing` facts for every keyword without demand data and for absent competition."""
    out = []
    for kw in keywords:
        has = any(
            f.kind in ("real", "external")
            and f.claim.startswith(DEMAND_PREFIXES)
            and f.claim.endswith(f": {kw}")
            for f in facts
        )
        if not has:
            out.append(
                Fact(
                    claim=f"demand (real or sourced): {kw}",
                    value=None,
                    source="no provider returned it",
                    kind="missing",
                )
            )
    if not any(f.claim.startswith("store competitor: ") for f in facts):
        out.append(
            Fact(
                claim="Chrome Web Store competition",
                value=None,
                source="no provider returned it (add an evidence file)",
                kind="missing",
            )
        )
    return out


def file_hashes(ctx: Context) -> dict[str, str]:
    import hashlib

    return {
        f.name: hashlib.sha256(f.read_bytes()).hexdigest()[:16]
        for f in sorted((ctx.dir / EVIDENCE_DIR).glob("*.md"))
    }


def add_file(idea_dir: Path, src: Path) -> Path:
    dest_dir = idea_dir / EVIDENCE_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest, n = dest_dir / src.name, 2
    if dest.suffix != ".md":
        dest = dest.with_suffix(".md")
    while dest.exists() and dest.read_bytes() != src.read_bytes():
        dest, n = dest_dir / f"{src.stem}-{n}.md", n + 1
    dest.write_bytes(src.read_bytes())
    return dest
