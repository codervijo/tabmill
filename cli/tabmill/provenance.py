"""Every fact carries where it came from (D-040, principle 2). Facts flow from the idea stage
into the recipe's `provenance:` list and `idea.md`."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

# real: tabmill-fetched data (e.g. lamill) · external: a row with a source URL ·
# external_suggestion: a brief's Proposal · user: operator answers · synthesis: AI guess or an
# unsourced row · missing: looked for, not found (never filled in).
Kind = Literal["real", "external", "external_suggestion", "user", "synthesis", "missing"]
EVIDENCE_KINDS: tuple[Kind, ...] = ("real", "external")  # what counts for the verdict cap


class Fact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim: str
    value: str | int | float | bool | None = None
    source: str = ""
    date: str = ""  # YYYY-MM-DD when known
    kind: Kind
