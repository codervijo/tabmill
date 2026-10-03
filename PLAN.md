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

## v1.F — CLI `try`: test an extension by hand in Chromium (in progress)

Operator (2026-10-03): a command that starts Chrome inside docker so they can test the extension.

- `tabmill try <slug> [--url URL] [--dev]`: regenerate + build (or start the WXT dev server with
  `--dev`), then launch Playwright's Chromium **headed** in the `tabmill-ext` container with the
  unpacked build loaded; the window appears on the host desktop via the container's X11
  forwarding. Real toolbar button → real activeTab grant.
- Profile in the container only (`/root/.tabmill-try/<slug>`), reused across runs; never on host.
- Chromium installed in the container only (same as smoke). Ctrl-C closes the browser.
- `✗` with a fix when `$DISPLAY` / X11 isn't available.

Done = operator can open #1 and #2 via `tabmill try`, click the toolbar icon, and use them.

## v1.G — Assets, listing, publish, release CI

- CLI: `assets` (Playwright icons 16/32/48/128, screenshots 1280×800, promo tile 440×280),
  `listing`, `publish` (CWS API **v2**, updates `registry.json`). CI release zips on tag.
- Finalize `tabmill-release` and `tabmill-store-listing`.

Done = #1 fully prepared via CLI; operator does the first real publish (dashboard "Add new item").

## v1.H — Landing, status, analytics

- CLI: `landing` (via `lamill`), `status` (registry + CWS fetchStatus + CSV metrics import).
- `packages/analytics`: opt-in, privacy-safe events, consent UI. Finalize `tabmill-landing-page`.

Done = `tabmill status` shows #1 and #2 with real data.

## v1.I — Extensions #3–#5

pressure-wash-quote, local-schema-generator, jwt-inspector — each a recipe in tabmill. Request
the publisher cap raise first.

Done = each takes under a day; template/skill gaps fixed in tabmill.
