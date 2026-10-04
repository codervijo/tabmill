# PLAN — tabmill

Per-phase scope and done criteria. Status lives in `docs/prd.md` § 5. Every phase's "done"
includes updated docs (prd row, PLAN, architecture, NOTES, DECISIONS, skills). When a phase
ships, its section moves to `docs/shipping-history.md`.

Core principle: **extract, don't design upfront.** #1 is built in the workspace with minimal
tooling; packages and CLI commands move into TOOL_DIR only when #2 needs them.

## v1.C — Extension #1 recipe (save-page-pdf-md) (in progress)

- Recipe feature code: article extraction (`@mozilla/readability`), HTML→Markdown (`turndown`),
  local branded PDF via a MarkPDF-style print page (D-013). Deps justified in DECISIONS.md first.
- Re-verify v1.A WXT spike checks in docker. Zip.

Done = #1 works on 10 real test URLs (listed in NOTES.md with results); smoke passes; zip builds;
time-to-first-build logged.

## v1.G — Assets, listing, publish, release CI (in progress)

- CLI: `assets` (Playwright icons 16/32/48/128, screenshots 1280×800, promo tile 440×280),
  `listing`, `publish` (CWS API **v2**, updates `registry.json`). CI release zips on tag.
- Finalize `tabmill-release` and `tabmill-store-listing`.

Done = #1 fully prepared via CLI; operator does the first real publish (dashboard "Add new item").

## v1.J — pressure-wash-quote (new #2 by publish order, D-027)

`maps-overlay` template; recipe: trace surfaces on Google Maps satellite → sq ft (optional
roof pitch) → WashCalc quote, PDF export.

## v1.K — Landing, analytics

CLI `landing` (via `lamill`); `packages/analytics` opt-in; finalize `tabmill-landing-page`.

## v1.L — local-schema-generator, jwt-inspector

Recipes; jwt-inspector never takes an early slot.
