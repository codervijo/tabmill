# PLAN — tabmill

Per-phase scope and done criteria. Status lives in `docs/prd.md` § 5. Every phase's "done"
includes updated docs (prd row, PLAN, architecture, NOTES, DECISIONS, skills). When a phase
ships, its section moves to `docs/shipping-history.md`.

Core principle: **extract, don't design upfront.** #1 is built in the workspace with minimal
tooling; packages and CLI commands move into TOOL_DIR only when #2 needs them.

## v1.A — Kickoff / decisions lock (in progress)

- [x] Initialize from existing skills + Lamill conventions (D-001, D-004).
- [x] Spikes 1–8 → `NOTES.md`; decisions → `DECISIONS.md`.
- [x] README, PLAN, CLAUDE, TODO, tabmill-dev skill, drafts of the five workspace skills.
- [ ] Operator resolves open questions (`docs/prd.md` § 7) → accepted decisions get ADRs.

Done = decisions locked (framework, linking; CLI language + Node location locked as ADR-0002/0003) and ADRs written.

## v1.B — Init + extension #1 (save-page-pdf-md)

- CLI skeleton: `cli/` Python package (uv, typer, rich), `uv run tabmill …`; `uv run pytest` / `ruff` / `mypy`.
- Workspace `Makefile` including the builder + generated `Makefile.local` (WXT targets, parent-dir
  `VOLUME_MOUNT`) from a `templates/` source (ADR-0003, ADR-0005).
- `tabmill init <dir>`: create WORKSPACE_DIR skeleton (`extensions/`, `registry.json`,
  generated `CLAUDE.md`, `TODO.md`, `pnpm-workspace.yaml`, `.tabmill-ref`), install skills into
  `.claude/skills/`, install CI workflows into `.github/workflows/`, write `tabmill.config.json`.
- `tabmill skills sync`: re-copy `skills/*` into the workspace; never merge into edited copies —
  detect drift and refuse with a message.
- Build save-page-pdf-md (WXT, ADR-0004) in the workspace with shared pieces **inline** (brand,
  CTA, messaging); PDF rendered locally with MarkPDF-style print styling (D-013).
- Re-verify the v1.A WXT build checks inside docker.
- Playwright smoke test; zip.

Done = workspace initialized; #1 loads unpacked; works on 10 real test URLs (listed in NOTES.md
with results); smoke test passes; zip builds; time-to-first-build logged.

## v1.C — Extension #2 (local-seo-checker) + extraction

- Build #2 with the `tabmill-new-extension` skill.
- Extract into `packages/`: brand, funnel, messaging, policy — only what both use.
- Typed extension.yaml schema (pydantic, in the CLI), validated at build; CLI generates the manifest JSON the WXT build reads.
- CLI: `new`, `dev`, `test`, `build`, `zip`, `lint` (policy rules from `skills/chrome-store-policy/reference.md`;
  `lint --release` escalates release-severity rules such as `cta-placeholder`, D-015).
- local-seo-checker ships with the placeholder Rankmill CTA until the operator supplies the URL.
- Write `docs/creating-an-extension.md`; refine skills from what #2 exposed.

Done = #2 scaffolded via `tabmill new`; both build from YAML; typecheck + lint + tests pass (Python: pytest/ruff/mypy; extensions: via builder); no
tool code copied into the workspace; #2 time-to-first-build far below #1.

## v1.D — Assets, listing, publish, release CI

- CLI: `assets` (Playwright icons 16/32/48/128, screenshots 1280×800, promo tile 440×280),
  `listing`, `publish` (CWS API **v2**, updates `registry.json`).
- CI builds release zips on tag (workspace).
- Finalize `tabmill-release` and `tabmill-store-listing`.

Done = #1 fully prepared via CLI; operator does the first real publish (dashboard "Add new
item" — the API can't create items).

## v1.E — Landing, status, analytics

- CLI: `landing` (via `lamill`), `status` (registry + CWS fetchStatus + CSV metrics import).
- `packages/analytics`: opt-in, privacy-safe events, consent UI.
- Finalize `tabmill-landing-page`.

Done = `tabmill status` shows #1 and #2 with real data.

## v1.F — Extensions #3–#5

pressure-wash-quote, local-schema-generator, jwt-inspector — each from a Claude Code session
opened in WORKSPACE_DIR using only the installed skills. Request the publisher cap raise first.

Done = each takes under a day; gaps fixed in skill sources + synced.
