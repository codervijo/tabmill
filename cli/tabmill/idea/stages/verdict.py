"""verdict_v1 (`docs/prd.md` § v2). AI proposes, code decides: the AI scores five dimensions
0–10 with reasons; code computes the weighted score, the band (thresholds in
`rules/lamill.yaml` § verdict), forces NO-GO on any check error, and caps the verdict at GO-IF
when every demand fact or every competition fact is synthesis or missing."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ... import ai, rules
from ..engine import Context, Result, StageKind
from .shape import existing_purposes

PURPOSE, VERSION = "verdict", 1
DIMENSIONS = ("reach", "outrate", "audience", "risk", "effort")
Band = Literal["GO", "GO-IF", "NO-GO"]
STRONG = ("real", "external")
DEMAND = ("monthly US searches", "Google Trends interest", "monthly searches", "demand ")
COMPETITION = ("store competitor", "Chrome Web Store competition")


class Score(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score: int = Field(ge=0, le=10)
    reason: str = Field(min_length=3)


class Scores(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reach: Score
    outrate: Score
    audience: Score
    risk: Score
    effort: Score


class VerdictReply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scores: Scores
    risks: list[str] = Field(default_factory=list)
    needs_evidence: list[str] = Field(default_factory=list)


def _evidence_table(facts: list[dict[str, Any]]) -> str:
    rows = []
    for f in facts:
        when = f", {f['date']}" if f.get("date") else ""
        rows.append(f"- [{f['kind']}] {f['claim']} = {f['value']} ({f['source']}{when})")
    return "\n".join(rows) or "(none)"


def values(ctx: Context) -> dict[str, str]:
    shape = ctx.upstream("shape")
    draft = shape["draft"]
    concept = {
        k: draft.get(k)
        for k in (
            "name",
            "single_purpose",
            "summary",
            "template",
            "trigger",
            "permissions",
            "restricted_pages",
            "target_keywords",
            "portfolio_site",
        )
    }
    facts = ctx.upstream("evidence")["facts"]
    findings = ctx.upstream("check")["findings"]
    return {
        "idea": ctx.session.text.strip(),
        "concept": json.dumps(concept, indent=1, ensure_ascii=False),
        "assumptions": "\n".join(f"- {a}" for a in shape["proposal"].get("assumptions", []))
        or "(none)",
        "evidence": _evidence_table(facts),
        "findings": "\n".join(f"- {f['severity']}: {f['rule']}: {f['message']}" for f in findings)
        or "(no findings)",
        "existing": existing_purposes(ctx),
    }


def weak(facts: list[dict[str, Any]], prefixes: tuple[str, ...]) -> bool:
    """True when no fact of this group is real or externally sourced."""
    group = [f for f in facts if str(f["claim"]).startswith(prefixes)]
    return not any(f["kind"] in STRONG for f in group)


def decide(
    scores: dict[str, int], errors: int, facts: list[dict[str, Any]], cfg: rules.VerdictConfig
) -> dict[str, Any]:
    """The code side of the verdict: weighted score, band, NO-GO on errors, evidence cap."""
    total = sum(cfg.weights.values())
    weighted = round(sum(cfg.weights[d] * scores[d] for d in DIMENSIONS) / total, 2)
    band: Band = "GO" if weighted >= cfg.go else "GO-IF" if weighted >= cfg.go_if else "NO-GO"
    verdict, why = (
        band,
        [f"weighted score {weighted} → {band} (GO ≥ {cfg.go}, GO-IF ≥ {cfg.go_if})"],
    )
    if errors:
        verdict = "NO-GO"
        why.append(f"{errors} check error(s) → NO-GO")
    needs = []
    if weak(facts, DEMAND):
        needs.append("demand: real or sourced search data")
    if weak(facts, COMPETITION):
        needs.append("store competition: sourced rows (brief or `tabmill evidence add`)")
    if needs and verdict == "GO":
        verdict = "GO-IF"
        why.append("capped at GO-IF: evidence is synthesis or missing — " + "; ".join(needs))
    return {"weighted": weighted, "band": band, "verdict": verdict, "why": why, "capped_by": needs}


class Verdict:
    name = PURPOSE
    kind: StageKind = "ai"
    needs: tuple[str, ...] = ("shape", "evidence", "check")

    def inputs(self, ctx: Context) -> dict[str, Any]:
        return {
            "prompt": f"{PURPOSE}_v{VERSION}",
            "verdict": rules.load(ctx.tool_dir).verdict.model_dump(),
        }

    def run(self, ctx: Context) -> Result:
        prompt = ai.load_prompt(ctx.tool_dir, PURPOSE, VERSION)
        reply, call = ai.run(prompt, values(ctx), VerdictReply, ctx.raw_dir, model=ctx.ai_model)
        scores = {d: getattr(reply.scores, d).score for d in DIMENSIONS}
        check = ctx.upstream("check")
        decided = decide(
            scores,
            int(check["errors"]),
            ctx.upstream("evidence")["facts"],
            rules.load(ctx.tool_dir).verdict,
        )
        return Result(
            output={
                **decided,
                "scores": reply.scores.model_dump(),
                "risks": reply.risks,
                "needs_evidence": reply.needs_evidence,
            },
            calls=[call],
        )
