---
name: tabmill-release
description: Prepare a Tabmill extension release — version bump, typecheck, test, build, zip, lint, store assets, listing draft — and STOP before publishing, writing `HUMAN: publish <slug>` to the workspace TODO.md. Use when the user says "release", "ship", "cut a version", "prepare for the store", "bump <slug>", or asks to publish an extension. Never publishes on its own.
---

# Tabmill release

> DRAFT (v1.A, 2026-10-03). Commands marked *(planned vN.X)* don't exist yet. Store-API
> facts verified 2026-10-03 against developer.chrome.com (see [reference.md](reference.md)).

**Hard rule: this skill never publishes.** It ends at "zip built + checks passing +
listing drafted". Publishing is a human step (`tabmill publish` only runs when the user
explicitly asks in an attended session).

## Steps

Run from the workspace root. Print one `✓` / `↷` / `✗` line per step; stop at the first `✗`.

1. **Clean tree.** `git status` in the workspace — uncommitted changes in other extensions → `✗`, ask.
2. **Version bump.** Edit `version` in `extensions/<slug>/extension.yaml` (semver: patch for
   fixes, minor for features). Never edit generated `manifest.json`. Must be greater than the
   version in `registry.json`.
3. **Typecheck.** via the builder (docker) — never run Node on the host.
4. **Unit tests.** `uv run tabmill test <slug>` *(planned v1.E)* — until then the workspace `make test`.
5. **Build.** `uv run tabmill build <slug>` (minimal today; full in v1.E).
6. **Lint.** `uv run tabmill lint <slug> --release` *(planned v1.E)* — release mode turns
   placeholder CTA/landing URLs into errors. Any `✗` blocks the release; use the
   `chrome-store-policy` skill to resolve.
7. **Smoke test.** Playwright loads the unpacked build (bundled Chromium, `channel: 'chromium'`).
8. **Zip.** `uv run tabmill zip <slug>` *(planned v1.E; today `make in-docker-zip EXT=<slug>`)* → `extensions/<slug>/.output/<slug>-<version>.zip`.
9. **Assets.** `uv run tabmill assets <slug>` *(planned v1.G)*: icons 16/32/48/128, 1–5 screenshots
   at 1280×800, small promo tile 440×280.
10. **Listing draft.** Use the `tabmill-store-listing` skill → `extensions/<slug>/listing.md`.
11. **Privacy check.** If analytics is on: privacy policy URL live, data categories + Limited
    Use certifications recorded in YAML.
12. **Handoff.** Append to workspace `TODO.md`:
    `- [ ] HUMAN: publish <slug> <version> — zip: <path>; listing: <path>; notes: <first-time? see below>`
    Then stop and report.

## First publish of a NEW extension (human, dashboard only)

The CWS API v2 **cannot create items**. For a slug with no `store_id` in `registry.json`, the
HUMAN line must say:
1. Developer Dashboard → **Add new item** → upload the zip.
2. Fill Store listing + Privacy practices tabs (paste from `listing.md`; justifications from YAML).
3. Set visibility (Public / Unlisted / Private) — the API can't change it.
4. Copy the item ID into `registry.json` → `store_id`.
5. New publishers are capped at **two published extensions** until more are requested in the dashboard.

## Updates to an existing item (attended only)

`uv run tabmill publish <slug>` *(planned v1.G)*: upload zip to the existing item, then publish
(`DEFAULT_PUBLISH`, or `STAGED_PUBLISH` to release manually after approval), then record
review state from `fetchStatus` in `registry.json`.

## Commit

One commit in the workspace repo, subject `<slug> <version>: release prep` — only when the
user asks to commit.
