"""`tabmill approve` — human gate 1 (D-040). Checks the written recipe (valid, no rule errors),
the verdict (NO-GO needs an override reason) and a free slot; then freezes the recipe (sha256
of its frozen fields) and reserves the slot in portfolio.yaml. The CLI asks for confirmation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .. import extension, generate, portfolio, rules
from . import engine


class ApproveError(Exception):
    """Can't approve; the message says what to do."""


@dataclass
class Plan:
    idea_id: str
    slug: str
    verdict: dict[str, Any]
    fill: list[str]
    warnings: list[str]
    item: portfolio.Item
    renewal: bool = False  # re-approval of a bumped revision
    notes: list[str] = field(default_factory=list)


def _record(tool_dir: Path, idea_id: str, stage: str) -> dict[str, Any]:
    rec = engine.read_stage(tool_dir, idea_id, stage)
    if rec is None or rec.stale:
        state = "hasn't run" if rec is None else "is stale"
        raise ApproveError(f"{stage} {state} for {idea_id} — `tabmill new --resume {idea_id}`")
    return rec.output


def prepare(tool_dir: Path, workspace: Path | None, idea_id: str, override: str = "") -> Plan:
    engine.load(tool_dir, idea_id)  # IdeaError if unknown
    written = _record(tool_dir, idea_id, "write")
    verdict = _record(tool_dir, idea_id, "verdict")
    slug = str(written["slug"])
    path = generate.recipe_dir(tool_dir, slug) / generate.RECIPE_FILE
    if not path.exists():
        raise ApproveError(f"{path} is gone — `tabmill new write {idea_id}` rewrites it")
    try:
        ext = extension.load_file(path)
    except extension.ExtensionError as e:
        raise ApproveError(str(e)) from e
    if ext.get("idea_id") != idea_id:
        raise ApproveError(f"recipes/{slug} belongs to idea {ext.get('idea_id') or '(none)'}")
    errors = extension.validate(ext, slug)
    if errors:
        raise ApproveError(f"recipes/{slug}/extension.yaml: " + "; ".join(errors))
    findings = rules.evaluate(rules.Subject(ext, slug, tool_dir, workspace), "idea")
    rule_errors = [f"{f.rule}: {f.message}" for f in findings if f.severity == "error"]
    if rule_errors:
        raise ApproveError("rule errors — " + "; ".join(rule_errors))
    if verdict["verdict"] == "NO-GO" and not override.strip():
        raise ApproveError(
            f'verdict is NO-GO — `tabmill approve {idea_id} --override "<reason>"` if you disagree'
        )
    data = portfolio.read(tool_dir)
    current = data.items.get(slug)
    revision = int(ext.get("recipe_revision", 1))
    sha = portfolio.frozen_sha256(ext)
    renewal = False
    if current is not None and current.approval in ("approved", "override"):
        if current.frozen_sha256 == sha and current.recipe_revision == revision:
            raise ApproveError(f"{slug} is already approved at recipe_revision {revision}")
        if revision <= current.recipe_revision:
            raise ApproveError(
                f"frozen fields changed — bump recipe_revision above "
                f"{current.recipe_revision} first"
            )
        renewal = True
    view = portfolio.slots(tool_dir, workspace)
    holds_slot = slug in view.published or slug in view.reserved
    if not holds_slot and view.free <= 0:
        raise ApproveError(
            f"no free store slot ({len(view.published)} published + "
            f"{len(view.reserved)} reserved of {view.limit})"
        )
    fill = [k for k, v in ext.items() if isinstance(v, str) and extension.FILL_MARKER in v]
    item = portfolio.Item(
        approval="override" if override.strip() else "approved",
        idea_id=idea_id,
        recipe_revision=revision,
        frozen_sha256=sha,
        approved_at=datetime.now(UTC).isoformat(timespec="seconds"),
        slot="none" if slug in view.published else "reserved",
        override_reason=override.strip(),
    )
    warnings = [f"{f.rule}: {f.message}" for f in findings if f.severity == "warn"]
    return Plan(idea_id, slug, verdict, fill, warnings, item, renewal)


def apply(tool_dir: Path, plan: Plan) -> None:
    data = portfolio.read(tool_dir)
    data.items[plan.slug] = plan.item
    portfolio.write(tool_dir, data)
