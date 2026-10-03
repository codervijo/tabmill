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

## Steps (one `✓ ↷ ✗` line each; stop at the first `✗`)

1. **Clean trees.** `git status` in tabmill and the workspace — unrelated changes → ask.
2. **Version bump.** `version` in `recipes/<slug>/extension.yaml` (patch = fix, minor =
   feature); must exceed `registry.json`. Never edit generated files.
3. **Tests.** `uv run tabmill test <slug>` (typecheck, unit, build, smoke).
4. **Assets.** `uv run tabmill assets <slug>` → `.output/store/` (icon 128, promo 440×280,
   screenshots 1280×800). Look at them; replace `recipes/<slug>/assets/icon.svg` or add
   `screenshots:` in the recipe if they don't show the feature well.
5. **Listing.** `uv run tabmill listing <slug>` → `.output/store/listing.md`, then the
   `tabmill-store-listing` skill to finish the description (fill its `‹FILL›`).
6. **Zip.** `uv run tabmill zip <slug> --release` — builds, runs release lint (placeholders,
   store images, keyword repetition, bundle rules), zips. Any `✗` → fix with the
   `chrome-store-policy` skill.
7. **Manual check.** `uv run tabmill try <slug>` on real pages.
8. **Handoff.** Append to workspace `TODO.md`:
   `- [ ] HUMAN: publish <slug> <version> — zip: <path>; listing: <path>` and stop.

## The human's publish

- **New item (no `store_id`)**: `uv run tabmill publish <slug>` prints the dashboard steps —
  Add new item, paste listing + privacy answers, set visibility, then put the item ID in
  `registry.json`. New publishers can publish only two extensions until more are requested.
- **Existing item**: `uv run tabmill publish <slug> [--staged]` → release lint, confirm,
  upload, submit, status into `registry.json`. Later: `uv run tabmill publish <slug> --check`.
- Credentials: `tabmill/.env` (see `.env.example`).

## Commit

Commit only when the user asks: tabmill (recipe bump) and workspace (regenerated files).
