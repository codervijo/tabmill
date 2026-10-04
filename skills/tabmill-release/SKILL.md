---
name: tabmill-release
description: Prepare a Tabmill extension release — version bump in the recipe, tests, release lint, store assets, listing draft, release zip — and STOP before publishing, writing `HUMAN: publish <slug>` to the workspace TODO.md. Use when the user says "release", "ship", "cut a version", "prepare for the store", "bump <slug>", or asks to publish an extension. Never publishes on its own.
---

# Tabmill release

Store-API facts: [reference.md](reference.md) (verified 2026-10-03). Commands run from the
tabmill repo; all Node work happens in the builder container.

**Hard rule: this skill never publishes.** It ends at "zip built + checks passing + listing
drafted". `tabmill publish` refuses without a terminal and asks for confirmation — only the
user runs it.

## Steps

1. **Clean trees.** `git status` in tabmill and the workspace — unrelated changes → ask.
2. **Version bump** in `recipes/<slug>/extension.yaml` (must exceed `registry.json`); add a
   `changelog:` entry `{version, date: YYYY-MM-DD, notes}` — it shows on the lamill.io hub.
3. **`uv run tabmill release <slug>`** — regenerate → typecheck → unit → smoke → assets →
   listing draft (kept if it exists) → release lint → zip → slot-cap warning → adds
   `HUMAN: publish <slug> <version>` to the workspace TODO.md → `tabmill hub`.
4. On `✗`: fix and re-run. Typical blockers: `‹FILL›` in the recipe or `listing.md` (finish
   the description with `tabmill-store-listing`), placeholder CTA (D-015), privacy/support pages
   not live on lamill.io (D-029), store image sizes, keyword repetition, bundle rules
   (`chrome-store-policy`).
5. **Manual check.** `uv run tabmill try <slug>` on real pages; look at `.output/store/`.
6. **Hub.** If `hub` wrote lamill.io's `src/content/extensions.json`, the human reviews,
   commits, and deploys lamill.io — tabmill never commits there.
7. Stop. Report what's ready and the HUMAN lines.

## The human's publish

- **New item (no `store_id`)**: `uv run tabmill publish <slug>` prints the dashboard steps —
  Add new item, paste listing + privacy answers, set visibility, then put the item ID in
  `registry.json`. New publishers can publish only two extensions until more are requested.
- **Existing item**: `uv run tabmill publish <slug> [--staged]` → release lint, confirm,
  upload, submit, status into `registry.json`. Later: `uv run tabmill publish <slug> --check`.
- Credentials: `uv run tabmill settings apikeys set <KEY>`; check with `uv run tabmill settings apikeys list`.

## Commit

Commit only when the user asks: tabmill (recipe bump) and workspace (regenerated files).
