# Bugs

Tracked bugs for this project. Workflow + open + fixed.

## Workflow

When the operator reports a bug, Claude writes a structured entry in `## Open bugs` with:
**Date** (`YYYY-MM-DD`), **Title**, **Repro**, **Expected**, **Actual**, **Where**,
**Severity** (`blocker` | `major` | `minor` | `cosmetic`), **Notes**.

### Bug-pickup order between phases

1. Blockers first.
2. Bugs overlapping the just-shipped or next phase.
3. Everything else, oldest first.

### Moving to fixed

Move the entry to `## Fixed bugs` and append `**Fixed in** — <commit SHA> (<phase>)`.
Same commit moves the entry + fixes the bug. Never delete fixed entries.

## Open bugs

(none)

## Fixed bugs

(none)
