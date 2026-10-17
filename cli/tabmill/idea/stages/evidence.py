"""evidence (kind data; `docs/prd.md` § v2). Runs every provider on shape's keywords; each
keyword gets demand facts or a `missing` fact, and absent store competition is `missing` too.
Re-runs when the keywords or the evidence files change (`tabmill evidence add`)."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ..engine import Context, Result, StageKind
from ..evidence import Provider, default_providers, file_hashes, missing


class Evidence:
    name = "evidence"
    kind: StageKind = "data"
    needs: tuple[str, ...] = ("shape",)

    def __init__(self, providers: list[Provider] | None = None) -> None:
        self.providers = providers

    def inputs(self, ctx: Context) -> dict[str, Any]:
        return {"files": file_hashes(ctx)}

    def run(self, ctx: Context) -> Result:
        keywords = [str(k) for k in ctx.upstream("shape")["draft"].get("target_keywords", [])]
        runs = [p.collect(keywords, ctx) for p in (self.providers or default_providers())]
        facts = [f for r in runs for f in r.facts]
        facts += missing(keywords, facts)
        return Result(
            output={
                "keywords": keywords,
                "providers": [
                    {"name": r.name, "status": r.status, "detail": r.detail} for r in runs
                ],
                "facts": [f.model_dump() for f in facts],
                "kinds": dict(Counter(f.kind for f in facts)),
            },
            calls=[],
        )
