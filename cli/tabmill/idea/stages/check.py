"""check (kind rule, no AI; `docs/prd.md` § v2). Runs the shared rules engine on shape's draft
in the `idea` context — the same predicates `tabmill check` runs on a recipe — plus slots."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ... import catalog, portfolio, rules
from ..engine import Context, Result, StageKind


class Check:
    name = "check"
    kind: StageKind = "rule"
    needs: tuple[str, ...] = ("shape",)

    def inputs(self, ctx: Context) -> dict[str, Any]:
        # Outside state the rules read: rules file, other recipes, slots.
        view = portfolio.slots(ctx.tool_dir, ctx.workspace)
        return {
            "rules": rules.load(ctx.tool_dir).model_dump(),
            "recipes": catalog.recipe_slugs(ctx.tool_dir),
            "slots": [view.limit, view.published, view.reserved],
        }

    def run(self, ctx: Context) -> Result:
        draft = ctx.upstream("shape")["draft"]
        findings = rules.evaluate(
            rules.Subject(draft, str(draft["slug"]), ctx.tool_dir, ctx.workspace), "idea"
        )
        view = portfolio.slots(ctx.tool_dir, ctx.workspace)
        return Result(
            output={
                "findings": [asdict(f) for f in findings],
                "errors": sum(f.severity == "error" for f in findings),
                "warnings": sum(f.severity == "warn" for f in findings),
                "slots": {
                    "limit": view.limit,
                    "published": view.published,
                    "reserved": view.reserved,
                    "free": view.free,
                },
            },
            calls=[],
        )
