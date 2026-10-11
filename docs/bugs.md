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

### 2026-10-11 — Landing brief repeats the summary and carries the listing's ‹FILL› how-to
- **Repro:** `tabmill landing save-page-pdf-md` after `tabmill listing` → brief § What the extension does.
- **Expected:** single purpose + summary once; no placeholders.
- **Actual:** summary twice, single purpose twice, `‹FILL› — how to use it` line.
- **Where:** `cli/tabmill/landing.py` `brief()` pasted the whole generated listing text.
- **Severity:** minor
- **Notes:** listing copy now included only for paragraphs not already in the brief and without ‹FILL›.
- **Fixed in** — the D-035 commit (v1.K)

### 2026-10-11 — Hub privacy page 404s until after store review
- **Repro:** `tabmill hub` for an extension not yet PUBLISHED → entry `status: draft` → lamill.io 404s `/extensions/<slug>/privacy`.
- **Expected:** privacy URL live before the first CWS submission (release lint probes it).
- **Actual:** chicken-and-egg — can't pass review without the page, page appears only after publish.
- **Where:** `cli/tabmill/hub.py` status mapping; lamill.io `status` enum.
- **Severity:** blocker
- **Notes:** D-035 `unlisted` status in both repos.
- **Fixed in** — the D-035 commit (v1.K)
