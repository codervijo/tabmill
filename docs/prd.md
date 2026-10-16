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

Strict two-level versioning: `vN` tier, `vN.X` phase. Kickoff "Phase 0–5" = v1.A–v1.F (D-003);
reslotted 2026-10-03 for generated extensions (ADR-0008) → v1.A–v1.G; `list`/`create` inserted
as v1.D (D-021) → v1.A–v1.H; `try` inserted as v1.F (D-023) → v1.A–v1.I; reslotted for D-025–D-029 → v1.A–v1.L; lifecycle CLI inserted as v1.L (D-034) → v1.A–v1.M.
WordPress plugin support slotted as tier v2 (D-037). v1 closed 2026-10-14 with leftovers carried into
v2.A; v1.M dropped; new v2 = idea stage (D-040); WordPress renumbered v2 → v3 (D-039) → v4 (D-040).

### v1 — First extension portfolio

#### Phases

| Phase | Status | Title |
|---|---|---|
| v1.A | ✅ done | Kickoff / decisions lock — 8 spikes, docs, skill drafts |
| v1.B | ✅ done | Tool Makefile; `init` + `skills sync`; `build`; `new` (template + recipe → generated extension); popup template |
| v1.C | ✅ done | Extension #1 save-page-pdf-md recipe (feature code); smoke; zip — published 2026-10-14; 10-URL check not run (D-039) |
| v1.D | ✅ done | CLI `list` (all extensions + state) and `create` (starter recipe) |
| v1.E | ✅ done | Extension #2 local-seo-checker recipe; shared packages; typed schema; CLI dev/test/zip/lint |
| v1.F | ✅ done | CLI `try`: interactive Chromium in docker with the extension loaded |
| v1.G | ✅ done | CLI assets/listing/publish; CI release zips on tag; one shared privacy policy + `privacy-coverage` lint (D-036) — first real API publish carried to v2.A |
| v1.H | ✅ done | CLI `settings apikeys` (tabmill.env, probes) + `preflight` |
| v1.I | ✅ done | Publisher slots; CLI `status`, `release`, `hub` (lamill.io extensions.json); listing-URL lint |
| v1.J | ✅ done | Extension pressure-wash-quote recipe (+ `maps-overlay` template) — built, not shipping now (D-039) |
| v1.K | ✅ done | CLI `landing`; analytics package dropped until an extension needs it (D-039) |
| v1.L | ✅ done | Lifecycle CLI: `new` · `try` · `check` · `ship` · `status` · `settings`; old commands under `advanced` (D-038) — real-use validation carried to v2.A |
| v1.M | dropped | Extensions local-schema-generator, jwt-inspector as recipes — now v2 idea candidates (D-039) |

#### Design notes

See `PLAN.md` (per-phase scope + done criteria) and `NOTES.md` (v1.A spike findings).

### v2 — Idea stage

An idea stage in front of the build pipeline (D-039, D-040): a rough idea or a pasted Tabmill
brief → clarify → shape → evidence → check → verdict → write → operator `approve`, then
bootstrap → try → check → ship. Plan: `docs/v2-plan.md` (accepted 2026-10-15).

#### Phases

| Phase | Status | Title |
|---|---|---|
| v2.A | ✅ done | `docs/v2-plan.md`; `publish` top level (`ship` never uploads); recipe schema v2 + v1→v2 migration; `portfolio.yaml`; `status` · `slots` · `templates` · `doctor`; `new <slug>` → `bootstrap` (deprecated alias) |
| v2.B | 🔄 in progress | Stage engine + session storage + AI runner (prompt registry, JSON validation, repair, record/replay) + clarify for rough ideas |
| v2.C | ⏳ planned | Brief input (`--paste`, stdin, `--brief`, auto-detect), parser + schema, `brief check`, gap-only clarify |
| v2.D | ⏳ planned | Shape + rules engine (shared with `check`) + template fit + overlap |
| v2.E | ⏳ planned | Evidence: lamill integration, evidence files, provenance model, `evidence add` |
| v2.F | ⏳ planned | Verdict (rubric + cap) + write (recipe v2, idea.md, slot diff) + `approve` + `ideas list/show/compare` |
| v2.G | ⏳ planned | Target-adapter seam: chrome-mv3 behind the interface, templates migrated, page-overlay stub |
| v2.H | ⏳ planned | First real runs (word counter, page ruler briefs) → winner through approve → ship; retro; prompts tuned to v2 |
| v2.I–v2.Z | — | Reserved for fixes found in v2.H; work that doesn't fit v2 moves to v3.A |

### v3 — v2 follow-ups

Work that doesn't fit in v2; v3.A removes the deprecated `new <slug>` alias (D-040). Phases
slotted when v2.H's retro lands.

### v4 — WordPress plugins

Same funnel in a second channel (D-037): single-purpose free WordPress plugins generated from
recipes, each with "Built by Lamill" and a CTA to a portfolio site, tracked in the same
registry / hub / landing flow. Distribution: the wordpress.org plugin directory. §§ 1–3 and 6 are Chrome-only until v4.A rewrites them. Renumbered v2 → v3 (D-039) → v4 (D-040).

#### Phases

| Phase | Status | Title |
|---|---|---|
| v4.A | ⏳ planned | Planning / decisions lock — spikes: wordpress.org plugin rules + submission, PHP build/test in docker, how recipes carry a platform |
| v4.B | ⏳ planned | Platform field in the recipe schema; first WordPress template; generate + build a plugin zip |
| v4.C | ⏳ planned | First plugin recipe (plugin not chosen yet); tried in a WordPress container |
| v4.D | ⏳ planned | WordPress lint rules; release folder with `readme.txt` + assets; manual first submission to wordpress.org |
| v4.E | ⏳ planned | Registry, `status`, `hub`, `landing`, privacy policy cover plugins |

## 6. Conformance rules

- Extensions are generated (ADR-0008): their source (recipes: extension.yaml + feature code),
  templates, packages, CLI, CI templates, and skill sources live only in TOOL_DIR;
  `WORKSPACE_DIR/extensions/` is tabmill output and is never hand-edited.
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
3. ~~Framework + linking~~ — resolved 2026-10-03: WXT (ADR-0004); cross-repo pnpm workspace (ADR-0006, layout superseded by ADR-0007).
4. ~~Branded PDF via MarkPDF~~ — resolved 2026-10-03: generated locally (D-013).
5. ~~Rankmill CTA target~~ — resolved 2026-10-12: Rankmill is an internal tool, not a product;
   local-seo-checker's CTA points to `https://lamill.io/extensions` (`portfolio_site: lamill.io`).
6. ~~IndexNow for existing sites~~ — resolved 2026-10-03: skipped (D-016).
7. ~~Repo visibility~~ — resolved 2026-10-03: tabmill is private; workspace CI uses `TABMILL_PAT` (ADR-0007).
8. **Publisher cap** (2026-10-03): new publishers get two published extensions; request more
   before the third publish (order D-027).
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
