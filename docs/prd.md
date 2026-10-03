# PRD — tabmill

The canonical source of truth for purpose, scope, phases, and conformance. Code that
contradicts this doc is drift, not feature. Per-phase scope and done criteria: `PLAN.md`.
Original brief: `docs/kickoff.md`.

## 1. Purpose

Lamill wants a portfolio of narrowly scoped Chrome extensions, each solving one distinct
problem, each sending users to a Lamill portfolio site through an honest CTA and a paired SEO
landing page. Tabmill is the CLI + templates + Claude Code skills that make creating,
releasing, and tracking extension N+1 dramatically cheaper than extension N — without
tripping Chrome Web Store policy.

## 2. Non-goals

- Not a general extension framework for others — Lamill's portfolio only.
- No unattended publishing. `publish` always has a human approval step.
- No remote code, no server-side processing unless an extension's single purpose requires it.
- No firefox/safari targets (MV3 Chrome only) until operator signal.
- No upfront package design: shared packages are extracted only when a second extension needs them.
- Doesn't replace `lamill` for site deploy/indexing — it calls `lamill`.

## 3. Goals

In priority order (when they conflict, higher wins):
1. Chrome Web Store compliance, minimal permissions, privacy by default.
2. Fast creation of each subsequent extension (time-to-first-build logged in `NOTES.md`).
3. Minimal dependencies, each justified in `DECISIONS.md`.
4. MV3 only; manifest generated from typed extension.yaml.
5. Strong typing: Python CLI with typed schema validated at build (pydantic); strict TypeScript
   extension code with typed chrome.* messaging.
6. Shared Lamill branding (tokens + optional components); "Built by Lamill" mark + footer everywhere.
7. Easy dev/test: hot reload, `tabmill dev <slug>`, unit tests, Playwright smoke test.
8. One-command packaging: build, zip, assets, listing.
9. Optional analytics: off by default, opt-in per extension, privacy-safe, disclosed.
10. CI in the workspace: typecheck, lint, test, release zips on tag; publish manual.

## 4. Target user

The operator (single user), and Claude Code sessions opened in the workspace that use the
installed skills. End users of the extensions are not Tabmill users.

## 5. Versions / phases

Strict two-level versioning: `vN` tier, `vN.X` phase. Kickoff "Phase 0–5" = v1.A–v1.F (D-003).

### v1 — First extension portfolio

#### Phases

| Phase | Status | Title |
|---|---|---|
| v1.A | 🔄 in progress | Kickoff / decisions lock — 8 spikes, docs, skill drafts |
| v1.B | ⏳ planned | `tabmill init` + `skills sync`; workspace; extension #1 save-page-pdf-md |
| v1.C | ⏳ planned | Extension #2 local-seo-checker; extract packages + schema; CLI new/dev/test/build/zip/lint |
| v1.D | ⏳ planned | CLI assets/listing/publish; CI release zips on tag |
| v1.E | ⏳ planned | CLI landing/status; analytics package |
| v1.F | ⏳ planned | Extensions #3–#5 from installed skills only |

#### Design notes

See `PLAN.md` (per-phase scope + done criteria) and `NOTES.md` (v1.A spike findings).

## 6. Conformance rules

- Extension code only in WORKSPACE_DIR; tool code (CLI, packages, templates, CI templates,
  skill sources) only in TOOL_DIR. No tool code copied into the workspace.
- extension.yaml is the source of truth; generated `manifest.json` is never hand-edited.
- MV3 only. `strict: true`; no `any` without an explanatory comment.
- Every runtime dependency has a row in `DECISIONS.md` § Dependency register.
- Every host permission has a YAML justification (lint error otherwise).
- Every extension ships: single-purpose statement, UTM-tagged CTA, "Built by Lamill" mark +
  footer, privacy statement, generated README.
- CLI is Python + uv (ADR-0002). Node never on the host — only in the builder docker (ADR-0003).
- pnpm only for extensions (Lamill fleet rule); no other JS lockfiles.
- Installed skills in the workspace are never edited — edit `skills/` here and sync.
- SKILL.md ≤ ~150 lines; long material in sibling files.
- No placeholder CTA / landing URL ships: `tabmill lint --release` errors on them (D-015).

## 7. Open questions

1. ~~CLI language~~ — resolved 2026-10-03: Python + uv (ADR-0002).
2. ~~Where Node runs~~ — resolved 2026-10-03: builder docker only, never host (ADR-0003).
3. ~~Framework + linking~~ — resolved 2026-10-03: WXT (ADR-0004); cross-repo pnpm workspace (ADR-0006).
4. ~~Branded PDF via MarkPDF~~ — resolved 2026-10-03: generated locally (D-013).
5. **Rankmill CTA target** (2026-10-03): placeholder `https://rankmill.example/local-seo-audit`
   until the operator supplies the real URL; release lint blocks while it remains (D-015).
6. ~~IndexNow for existing sites~~ — resolved 2026-10-03: skipped (D-016).
7. ~~Repo visibility~~ — resolved 2026-10-03: tabmill is private; workspace CI uses `TABMILL_PAT` (ADR-0006).
8. **Publisher cap** (2026-10-03): new publishers get two published extensions; request more
   before #3 (v1.F).
9. ~~Builder changes~~ — resolved 2026-10-03: workspace `Makefile.local` overrides only (ADR-0005).

## 8. References

- Chrome Web Store program policies — https://developer.chrome.com/docs/webstore/program-policies/
- CWS API v2 — https://developer.chrome.com/docs/webstore/api/reference/rest
- WXT — https://wxt.dev
- Playwright extensions — https://playwright.dev/docs/chrome-extensions
- Claude Code skills — https://code.claude.com/docs/en/skills.md
- lamill CLI — `~/work/projects/sites/portfolio`

## Spec discipline

All canonical doc surfaces (this file, `PLAN.md`, `docs/architecture.md`,
`docs/shipping-history.md`, ADRs, `CLAUDE.md`, `docs/CLAUDE.md`) must match reality and code.
Drift is fixed in the same commit as the change that caused it.
