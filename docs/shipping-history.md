# Shipping history

Archived design rationale for shipped phases. Append-only, newest at top.

When a phase ships:
1. Move its design notes from `PLAN.md` / `docs/prd.md` to a new section here.
2. The PRD's phase row stays — only the design notes migrate.

Format per entry: `## vN.X — <title>` (shipped YYYY-MM-DD) with rationale, key decisions,
tradeoffs, and links to commits / ADRs.

---

## v1.E — Extension #2 + extraction (shipped 2026-10-03)

D-022 (shared code in `templates/extension/_shared/`), pydantic schema, side-panel template,
`lint`/`dev`/`test`/`zip`. #2 time-to-first-build 1 min 06 s. Hot reload in host Chrome unverified.

### v1.E plan: — Extension #2 recipe (local-seo-checker) + extraction

- Recipe for #2, started with `tabmill create` (CTA placeholder `https://rankmill.example/local-seo-audit`, D-015).
- Move code both use into `packages/` or templates; typed extension.yaml schema (pydantic).
- CLI: `dev`, `test`, `zip`, `lint` (`--release` severities, D-015); full `build`.
- Write `docs/creating-an-extension.md`; refine skills.

Done = both generated from recipes; typecheck + lint + tests pass; #2 time-to-first-build far below #1.


## v1.D — CLI `list` + `create` (shipped 2026-10-03)

D-021. Build of a `create`d recipe not re-run (same path as #1).

### v1.D plan (as executed)

Operator-felt gaps (2026-10-03): no way to see all extensions, no command to start one.

- `tabmill list [--json]`: one row per slug across `recipes/` and the workspace
  `registry.json` — slug, version, template, status (`recipe` → `generated` → `built`, built =
  `.output/chrome-mv3/manifest.json` exists), store ID, `↷` flags for placeholder fields
  (`‹FILL›`, reserved `.example` URLs). Read-only.
- `tabmill create <slug> [--template popup]`: writes a starter `recipes/<slug>/extension.yaml`
  (`activeTab` only, `analytics: false`, `‹FILL›` for name / summary / single purpose / CTA /
  keywords / category); validates the slug (lowercase kebab-case); refuses if the slug exists as a
  recipe or registry entry, or the template isn't implemented; prints the next step
  (`fill the ‹FILL› fields, then tabmill new <slug>`). Never touches the workspace.
- `new` keeps its name (operator, 2026-10-03). `new` / `build` refuse a recipe that still has
  `‹FILL›` in fields the manifest needs (name, summary, single_purpose).
- `tabmill-new-extension` skill: step 7 starts from `tabmill create`.

Done = `tabmill create demo && <fill fields> && tabmill new demo && tabmill build demo` works
end to end; `tabmill list` shows save-page-pdf-md (built) and demo; tests cover duplicate,
bad-slug, and placeholder refusals.


## v1.B — Tool + generator (shipped 2026-10-03)

Not committed at ship time (operator commits). Key decisions: D-017/ADR-0007 workspace =
`$TABMILL_WORKSPACE` (`~/.profile`), computed relative layout; D-018 tool build via builder
Makefile; D-019/ADR-0008 extensions generated from recipes; D-020 minimal `build` pulled in.
Lessons: generated Makefiles use `:=` for container vars (inherited `CONTAINER_NAME` sent a
build to the Python container); container-root file ownership handed back after each target;
pnpm store pinned inside the container; seed vs managed workspace files so template fixes
propagate. `tabmill-new-extension` moved to tool-repo skills (writes recipes).

### v1.B plan (as executed)

Reslotted 2026-10-03 (ADR-0008): tabmill generates extensions; this phase builds the generator.

- Tool build via a `Makefile` that includes the builder (Python stack) + `Makefile.local` (D-018). ✅
- `tabmill init`, `tabmill skills sync` (seed vs managed files, sha-manifest drift guard). ✅
- Workspace `Makefile` + generated `Makefile.local` → builder docker (ADR-0003/0005). ✅
- `tabmill build <slug>` (minimal): validate YAML, generate manifest fields, WXT build in docker. ✅
- `tabmill new <slug>`: render `templates/extension/<template>/` + `recipes/<slug>/` overlay + YAML
  values → `extensions/<slug>/` (managed); add `registry.json` row; `skills sync` regenerates.
- `templates/extension/popup/`: WXT config reading `manifest.gen.json`, popup shell with
  "Built by Lamill" mark + footer, UTM CTA, privacy line, typed messaging helper, generated
  README, Vitest + Playwright smoke test (bundled Chromium, in docker).
- `recipes/save-page-pdf-md/extension.yaml` only (no feature code yet).

Done = `tabmill new save-page-pdf-md && tabmill build save-page-pdf-md` produces an unpacked
extension that loads and passes the smoke test, with nothing hand-written in the workspace.


## v1.A — Kickoff / decisions lock (shipped 2026-10-03)

Commit `f75188b`. Initialized from the Lamill standard (project-init) and the kickoff brief;
ran 8 spikes verified against official docs (`NOTES.md` § v1.A spikes).

Decisions: ADR-0002 Python + uv CLI · ADR-0003 Node only via the builder docker ·
ADR-0004 WXT · ADR-0005 builder adapted via workspace `Makefile.local` · ADR-0006 cross-repo
pnpm workspace (private tabmill, `TABMILL_PAT` in CI) · D-013 local PDF rendering ·
D-015 placeholder-CTA lint (warn in dev, error at release) · D-016 no IndexNow.

Key facts that shaped the plan: CWS API v1 ends 2026-10-15 and v2 can't create items (first
upload is a dashboard step); new publishers capped at two published extensions; no metrics
API (CSV import); duplicate-functionality policy is the largest portfolio risk; Playwright
loads unpacked extensions only in bundled Chromium.

Original phase plan:

### v1.A plan (as executed)

- [x] Initialize from existing skills + Lamill conventions (D-001, D-004).
- [x] Spikes 1–8 → `NOTES.md`; decisions → `DECISIONS.md`.
- [x] README, PLAN, CLAUDE, TODO, tabmill-dev skill, drafts of the five workspace skills.
- [x] Operator resolves open questions (`docs/prd.md` § 7) → accepted decisions get ADRs.

Done = decisions locked (framework, linking; CLI language + Node location locked as ADR-0002/0003) and ADRs written.


