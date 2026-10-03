# Tabmill — kickoff (verbatim operator brief, 2026-10-03)

Archived source brief. Canonical, maintained versions of its content live in `docs/prd.md`,
`PLAN.md`, `CLAUDE.md`, and `docs/architecture.md`. Where they diverge, those win (record why
in `DECISIONS.md`). Known deviations at intake:

- Paths: `~/code/tabmill` → `~/work/projects/droyfun/tabmill`;
  `~/code/tabmill-extensions` → `~/work/projects/droyfun/tabmill-extensions` (D-002).
- "Phase 0…5" → `v1.A…v1.F` per the canonical versioning scheme (D-003); reslotted v1.A–v1.G (D-019).
- Workspace → `~/work/projects/plugins/chrome-extension-projects` via `$TABMILL_WORKSPACE` (D-017).
- Extensions are generated from recipes in tabmill, not hand-built in the workspace (ADR-0008).

---

## Directories (fixed — do not mix them)
- TOOL_DIR = ~/code/tabmill                 ← you are here. Tabmill itself lives here.
- WORKSPACE_DIR = ~/code/tabmill-extensions ← extensions live here. Tabmill manages it.

Tabmill code, templates, shared packages, and skill sources live ONLY in
TOOL_DIR. Extension source, extension.yaml files, registry.json, and build
output live ONLY in WORKSPACE_DIR. The CLI reads WORKSPACE_DIR from
`tabmill.config.json` (or `TABMILL_WORKSPACE` env var) — never hardcode it.

## What Tabmill is
A CLI + templates + Claude Code skills that create, publish, and manage a
portfolio of narrowly scoped Chrome extensions for Lamill (lamill.io). Each
extension solves one distinct problem, links back to a portfolio site, says
"Built by Lamill", and is paired with an SEO landing page on that site
(Google searches target the tool, e.g. "markdown to pdf", not "X chrome
extension").

Deliverables: the architecture, scaffold/tooling, documentation, and a clear
workflow such that creating extension #2 is dramatically easier than #1.

## Initialization and conventions (do first)
- List my existing custom skills (user-level and any in related Lamill
  projects) and use the relevant ones to initialize this project. Note in
  DECISIONS.md which you used and why.
- Inspect existing Lamill projects and the `lamill` CLI for conventions
  (repo layout, TypeScript config, lint/format, env handling, naming,
  CLAUDE.md/TODO.md style, deploy flow). Reuse them; only introduce a new
  convention when none exists, and record why in DECISIONS.md.
- A `lamill` CLI already deploys sites to Cloudflare Pages with GitHub
  integration, GSC verification, sitemap submission, and IndexNow.
  `tabmill landing` must reuse it. If you can't find it or other Lamill
  projects, ask me for their locations.

## Optimization targets (priority order when they conflict)
1. Chrome Web Store compliance, minimal permissions, privacy by default.
2. Very fast creation of each subsequent extension (measure
   time-to-first-build per extension in NOTES.md).
3. Minimal dependencies: justify every runtime dependency in DECISIONS.md;
   prefer platform APIs and small single-purpose libraries.
4. Manifest V3 only; manifest generated from typed extension.yaml.
5. Strong TypeScript: strict mode, typed extension.yaml schema (validated at
   build), typed chrome.* messaging between background/content/UI.
6. Shared Lamill branding via design tokens + optional components; each
   extension can have its own UI. Required everywhere: "Built by Lamill"
   mark + footer.
7. Easy local dev/testing: hot reload, `tabmill dev <slug>`, unit tests for
   logic, Playwright smoke test that loads each unpacked extension.
8. Automated packaging: build, zip, assets, listing in one command.
9. Optional analytics: off by default, opt-in per extension in YAML,
   privacy-safe events only (no URLs or page content), disclosed in the
   listing and privacy statement.
10. CI/release: GitHub Actions in WORKSPACE_DIR for typecheck, lint, tests,
    and building release zips on tag; publish stays a manual approval step.

## Skills are the backbone
Tabmill ships Claude Code custom skills. Source lives in
TOOL_DIR/skills/<name>/SKILL.md (frontmatter: name, description — the
description must say exactly when to trigger). `tabmill init <dir>` installs
them into WORKSPACE_DIR/.claude/skills/; `tabmill skills sync` updates them.
Never edit installed copies — edit the source in TOOL_DIR and sync.

Workspace skills (in TOOL_DIR/skills/):
1. **tabmill-new-extension** — idea → extension.yaml: single purpose,
   template, minimal permissions, funnel fields, analytics opt-in; then
   `tabmill new`. Refuses ideas that duplicate an extension in registry.json.
2. **chrome-store-policy** — current store rules (single purpose,
   spam/repetitive content, remote code, permission justification, privacy
   disclosures) as a checklist, plus how to read `tabmill lint` output.
3. **tabmill-store-listing** — listing title, short + long description,
   screenshot captions from extension.yaml + target keywords.
4. **tabmill-landing-page** — paired web-tool page for the portfolio site,
   deployed via the `lamill` CLI.
5. **tabmill-release** — version bump, typecheck, test, build, zip, lint,
   assets, listing draft; STOPS before publish and writes
   `HUMAN: publish <slug>` to WORKSPACE_DIR/TODO.md.

Tool-repo-only skill: TOOL_DIR/.claude/skills/tabmill-dev/SKILL.md —
conventions for working on Tabmill itself (the Rules section). Not installed
into the workspace.

Write skills from verified findings, not memory. Keep each SKILL.md under
~150 lines; put long reference material in files beside it and link to them.

## Core principle: EXTRACT, don't design upfront
Extension #1 is built in WORKSPACE_DIR with minimal tooling. Shared packages
and CLI commands move into TOOL_DIR only when extension #2 needs them.
Skills are refined each time an extension exposes a gap.

## Target layout
TOOL_DIR (tabmill/)
├── cli/            `tabmill` commands
├── packages/
│   ├── brand/      design tokens, "Built by Lamill" mark, footer
│   ├── funnel/     CTA component, UTM builder, "More from Lamill"
│   ├── messaging/  typed chrome.* messaging helpers
│   ├── analytics/  opt-in, privacy-safe event helper
│   └── policy/     permission + single-purpose lint rules
├── templates/      popup | side-panel | devtools | context-menu | maps-overlay
├── skills/         skill sources installed into the workspace
├── ci/             GitHub Actions templates installed into the workspace
├── docs/creating-an-extension.md
├── .claude/skills/tabmill-dev/
└── README.md  PLAN.md  CLAUDE.md  TODO.md  NOTES.md  DECISIONS.md

WORKSPACE_DIR (tabmill-extensions/)
├── .claude/skills/   installed by `tabmill init` — do not hand-edit
├── .github/workflows/ installed by `tabmill init`
├── extensions/<slug>/
│   ├── extension.yaml  single source of truth
│   ├── README.md       generated
│   └── src/
├── registry.json       version, store ID, status, metrics per extension
├── CLAUDE.md           generated: points to the skills
└── TODO.md             extension work queue + HUMAN: lines

Extensions consume TOOL_DIR packages via linking (decide the mechanism in
Phase 0). Extensions must build from WORKSPACE_DIR without copying tool code.

extension.yaml fields: name, slug, single_purpose, template, permissions
(+ justification for any host permission), portfolio_site,
landing_page_url, target_keywords, cta_text, cta_url, utm_campaign,
store_category, analytics (default false), theme overrides (optional).

CLI commands (built across phases): init, skills sync, new, dev, test,
build, zip, lint, assets, listing, landing, publish, status.

## The first five extensions (build order)
1. **save-page-pdf-md** — current page → clean Markdown or branded PDF via
   MarkPDF (markpdf.dev). Keywords: markdown to pdf, save webpage as pdf,
   webpage to pdf, html to markdown.
2. **local-seo-checker** — audits the business website behind a Google
   listing: service-area pages, NAP consistency, LocalBusiness schema,
   conversion elements. CTA → full audit on Rankmill. Keywords: local seo
   checker, local seo audit tool, nap consistency checker.
3. **pressure-wash-quote** — trace surfaces on Google Maps satellite view →
   square footage (optional roof-pitch adjustment) → WashCalc quote,
   exportable as PDF. Keywords: pressure washing estimate calculator,
   google maps area calculator.
4. **local-schema-generator** — reads current site, outputs missing
   LocalBusiness JSON-LD. Shares code with #2.
5. **jwt-inspector** — auto-detects JWTs in requests/storage, decodes
   locally. CTA → CalcEngine. Success = referrals, not installs.

## Phase 0 — Spikes + skill drafts (do now, then STOP)
Verify against official docs, not memory. Findings → NOTES.md, decisions
with reasoning → DECISIONS.md.

1. **Framework:** WXT vs Plasmo vs vanilla MV3 + Vite — dependency weight,
   TypeScript support, hot reload, fit for tool repo + separate workspace,
   side panel / devtools / context menu / content scripts on Google Maps.
2. **Cross-directory linking:** how WORKSPACE_DIR extensions consume TOOL_DIR
   packages and templates cleanly, locally and in CI.
3. **Chrome Web Store API:** current version, auth (OAuth refresh token vs
   service account), whether it can create NEW items or only update, upload,
   publish (incl. unlisted/private), review status.
4. **Metrics:** impressions/installs/weekly users — API vs dashboard-only;
   if dashboard-only, design a CSV import.
5. **Policy:** current store rules → concrete, testable lint rules,
   including analytics disclosure requirements.
6. **Testing:** loading unpacked MV3 extensions in Playwright, in CI.
7. **Landing integration:** what you need from the `lamill` CLI.
8. **Claude Code skills:** confirm the current SKILL.md format, frontmatter,
   and project-level skill location.

Then create in TOOL_DIR: README.md, PLAN.md, CLAUDE.md, TODO.md, the
tabmill-dev skill, and DRAFTS of the five workspace skills. Stop and give me
a short summary: conventions found, skills used, findings, recommended
framework + linking approach, dependency list, open questions, and exactly
what I must do by hand.

## Phases (for PLAN.md — each phase's "done" includes updated docs)
- **Phase 1:** Minimal `tabmill init` + `skills sync`. Initialize
  WORKSPACE_DIR (skills, CI, CLAUDE.md). Build save-page-pdf-md there,
  shared pieces inline. Done = workspace initialized, #1 loads unpacked,
  works on 10 real test URLs, smoke test passes, zip builds.
- **Phase 2:** Build local-seo-checker using the tabmill-new-extension skill;
  extract packages (brand, funnel, messaging, policy), typed extension.yaml
  schema; CLI: new, dev, test, build, zip, lint. Write
  docs/creating-an-extension.md. Refine skills from what #2 exposed.
  Done = #2 scaffolded via `tabmill new`, both build from YAML, typecheck +
  lint + tests pass, no tool code copied into the workspace,
  time-to-first-build for #2 recorded and far below #1.
- **Phase 3:** CLI: assets (Playwright icons + screenshots), listing,
  publish (store API, updates registry.json); CI builds release zips on tag.
  Finalize tabmill-release and tabmill-store-listing skills.
  Done = #1 fully prepared via CLI; I do the first real publish.
- **Phase 4:** CLI: landing, status; analytics package. Finalize
  tabmill-landing-page skill. Done = `tabmill status` shows #1 and #2 with
  real data.
- **Phase 5:** Extensions #3–#5, each built from a CC session opened in
  WORKSPACE_DIR using only the installed skills. Done = each takes under a
  day; gaps fixed in skill sources + synced.

## Rules (for TOOL_DIR/CLAUDE.md and the tabmill-dev skill)
- Never write extension code in TOOL_DIR; never write tool code in
  WORKSPACE_DIR. Templates, CI templates, and skill sources are tool code.
- extension.yaml is the source of truth; never hand-edit generated
  manifest.json.
- Manifest V3 only. TypeScript strict mode everywhere; no `any` without a
  comment explaining why.
- Every new runtime dependency needs a justification in DECISIONS.md.
- Permissions: activeTab + optional permissions by default. Any host
  permission needs a written justification in the YAML; lint fails without it.
- No remote code. Processing stays local unless the single purpose
  requires otherwise.
- Analytics are opt-in per extension, never include URLs or page content,
  and must be disclosed in the listing and privacy statement.
- Every extension ships with: single-purpose statement, UTM-tagged CTA,
  "Built by Lamill" mark + footer, privacy statement, generated README.
- `publish` NEVER runs unattended. In unattended sessions, stop at "zip
  built + checks passing + listing drafted" and add `HUMAN: publish <slug>`
  to WORKSPACE_DIR/TODO.md.
- Don't extract a shared package until two extensions need it.
- Plans before patches: for any change over ~20 lines, plan in TODO.md first.
- Git: TOOL_DIR and WORKSPACE_DIR are separate repos. Small commits per TODO
  item, never force-push, never commit .env or credentials.
- Continuation: when a TODO item is done, check it off, take the next. If
  blocked, write the blocker to NOTES.md, mark it BLOCKED, move on.

## Done by hand (me)
- Chrome Web Store developer account under my business entity
- Publisher domain verification (lamill.io)
- Google Cloud OAuth client for the store API (credentials in TOOL_DIR/.env)
Tell me exactly what credentials and settings you need after Spike 3.

Start with initialization, then Phase 0.
