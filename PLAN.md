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

## v1.D — Extension #2 recipe (local-seo-checker) + extraction

- Recipe for #2 (CTA placeholder `https://rankmill.example/local-seo-audit`, D-015).
- Move code both use into `packages/` or templates; typed extension.yaml schema (pydantic).
- CLI: `dev`, `test`, `zip`, `lint` (`--release` severities, D-015); full `build`.
- Write `docs/creating-an-extension.md`; refine skills.

Done = both generated from recipes; typecheck + lint + tests pass; #2 time-to-first-build far below #1.

## v1.E — Assets, listing, publish, release CI

- CLI: `assets` (Playwright icons 16/32/48/128, screenshots 1280×800, promo tile 440×280),
  `listing`, `publish` (CWS API **v2**, updates `registry.json`). CI release zips on tag.
- Finalize `tabmill-release` and `tabmill-store-listing`.

Done = #1 fully prepared via CLI; operator does the first real publish (dashboard "Add new item").

## v1.F — Landing, status, analytics

- CLI: `landing` (via `lamill`), `status` (registry + CWS fetchStatus + CSV metrics import).
- `packages/analytics`: opt-in, privacy-safe events, consent UI. Finalize `tabmill-landing-page`.

Done = `tabmill status` shows #1 and #2 with real data.

## v1.G — Extensions #3–#5

pressure-wash-quote, local-schema-generator, jwt-inspector — each a recipe in tabmill. Request
the publisher cap raise first.

Done = each takes under a day; template/skill gaps fixed in tabmill.
