# Shipping history

Archived design rationale for shipped phases. Append-only, newest at top.

When a phase ships:
1. Move its design notes from `PLAN.md` / `docs/prd.md` to a new section here.
2. The PRD's phase row stays — only the design notes migrate.

Format per entry: `## vN.X — <title>` (shipped YYYY-MM-DD) with rationale, key decisions,
tradeoffs, and links to commits / ADRs.

---

## v2.F — Verdict, write, approve, ideas (shipped 2026-10-16, D-040)

verdict_v1 with code-side score, bands and evidence cap (config in `rules/lamill.yaml`); write
(recipe v2 + idea.md, no clobber); portfolio item diff + `--apply`; `approve` (terminal-only gate,
freeze hash, slot reservation, override reason); build path refuses unapproved idea recipes and
frozen-field drift; `ideas list/show/compare`. Live run: page-word-counter GO-IF 5.65, $0.69;
fixed `status` pointing at bootstrap before approve. `approve` not run in a real terminal. 228 tests.

## v2.E — Evidence (shipped 2026-10-16, D-040)

Providers with one interface (lamill validate/trends, evidence files, brief, overlap; treg and
store competition declared, not available); soft-fail; `missing` facts for keywords without
real/sourced demand and for absent store competition. lamill's volume kept as `synthesis` (LLM
estimate). `evidence add`, `new --evidence`, `new validate|trends`. Rich markup escaped in step
output; cost line always last. A test once ran real lamill (5 SerpAPI queries, $0.33) → conftest
blocks paid tools. Real lamill output parsed (cached run); full live idea run with evidence not
done. 213 tests.

## v2.D — Shape, rules engine (shipped 2026-10-16, D-040)

`rules/lamill.yaml` + `rules.py` shared by the idea `check` stage and lint (recipe-level lint
rules moved in unchanged); shape_v1 (code picks slug, honours --template, adds template
permissions); check stage. Live run: page-word-count · popup, 0 errors, $0.45. 201 tests.

## v2.C — Brief input (shipped 2026-10-16, D-040)

`brief.py`: Tabmill brief v1 models → `schemas/brief_v1.schema.json`; section-by-section,
line-based parser (AI-written values contain `: `, so no YAML for sections); problems carry line
and section, the rest is kept. Sourced evidence rows `external`, unsourced `synthesis`; Answers
and Proposal `external_suggestion`. `brief check`; `new --brief | - | --paste | bare new on a
TTY`; auto-detect; `ideas/<id>/brief.md` verbatim. Gap-only clarify: brief answers win, open
questions and broken sections asked by code, no AI call when all five answers are present.
Real brief from claude.ai not yet run. 187 tests.

## v2.B — Stage engine, AI runner, clarify (shipped 2026-10-16, D-040)

`ai.py` (`claude -p`, no tools, budget-capped; pydantic validation, one repair, raw saved on
failure; `TABMILL_AI=replay|record`), `idea/engine.py` (sessions in `ideas/<id>/`, stage files
with input hashes, resume, downstream staleness), clarify_v1 (≤ 2 rounds, answers as `user`
facts, open questions carried). `new "idea"`, `--resume`, `--non-interactive`, `new clarify`.
Cost line after every AI command (operator add). Fix: smoke/try no longer run apt every time
(silent hang when the container lost DNS). One live non-interactive run: 3 good questions,
$0.23 on the default model. Interactive loop not confirmed in real use. 172 tests.

## v2.A — Plan, recipe schema v2, portfolio.yaml, bootstrap (shipped 2026-10-16, D-040)

v2 plan accepted, now in `docs/prd.md` § v2 (exception to "vN.A is planning only"). Recipe schema v2 with a
comment-preserving text migration (3 recipes: 4 added lines each, nothing else); `portfolio.yaml`
(3 × `migrated`, limit 2); `surfaces.py` registry (page-overlay stub; devtools / context-menu
dropped); `bootstrap` + deprecated `new <slug>` alias; `publish` top level, `ship` never uploads;
`status` lifecycle stage, `slots`, `templates`, `doctor [--fix]`. Generated workspace output
byte-identical except the 3 README hints. 148 tests. Not verified in real use: `publish`, `ship`
end to end.

## v1 closed — v1.C, v1.G, v1.J, v1.K, v1.L (closed 2026-10-14, D-039)

#1 save-page-pdf-md approved and published (store id aknmbookdcobogmhhnppjofghdjepice); hub page
lamill.io/extensions/save-page-pdf-md and tool page markpdf.dev/save-webpage-as-pdf/ live and
linked. Operator closed v1 with leftovers carried into v2.A. Never verified in real use: the
CWS API upload/publish path (mocks only; fetchStatus is real), v1.L top-level commands end to end,
v1.C's 10-URL check, v1.J's real-Maps try. v1.K analytics package dropped; v1.M dropped (its two
extensions are v2 idea candidates).

### Plans at close (from PLAN.md)

#### v1.C — Extension #1 recipe (save-page-pdf-md) (in progress)

- Recipe feature code: article extraction (`@mozilla/readability`), HTML→Markdown (`turndown`),
  local branded PDF via a MarkPDF-style print page (D-013). Deps justified in DECISIONS.md first.
- Re-verify v1.A WXT spike checks in docker. Zip.

Done = #1 works on 10 real test URLs (listed in NOTES.md with results); smoke passes; zip builds;
time-to-first-build logged.

#### v1.G — Assets, listing, publish, release CI (in progress)

- CLI: `assets` (Playwright icons 16/32/48/128, screenshots 1280×800, promo tile 440×280),
  `listing`, `publish` (CWS API **v2**, updates `registry.json`). CI release zips on tag.
- Finalize `tabmill-release` and `tabmill-store-listing`.
- Shared privacy policy (D-036): `privacy-policy.yaml` → `hub` writes lamill.io
  `src/content/privacy.json` → one page `lamill.io/extensions/privacy`. Release lint
  `privacy-coverage` fails when a recipe does more than the policy covers; `hub-urls` checks
  the live page shows the current policy version.

Done = #1 fully prepared via CLI; operator does the first real publish (dashboard "Add new item").

#### v1.J — pressure-wash-quote (new #2 by publish order, D-027)

`maps-overlay` template; recipe: trace surfaces on Google Maps satellite → sq ft (optional
roof pitch) → WashCalc quote, PDF export.

#### v1.K — Landing, analytics (in progress)

CLI `landing` (via `lamill`); `packages/analytics` opt-in; finalize `tabmill-landing-page`.

#### v1.L — Lifecycle CLI (in progress; D-034, D-038)

Operator (2026-10-08): ~20 commands, hard to know which to use. One path per extension:
start → publish → track health over its store life. Shape amended 2026-10-12 (D-038).

| Command | Absorbs |
|---|---|
| `new <slug>` | `create` (first run writes the starter recipe), `new` (later runs regenerate) |
| `try <slug> [--dev]` | `build`, `dev`, `try` |
| `check [slug]` | `test`, `lint`; no slug = every extension |
| `ship <slug> [--publish]` | `assets`, `listing`, `landing`, `zip`, `release`, `hub`; `--publish` = attended upload |
| `status [slug]` | `list`, `status`, `publish --check` (`--refresh`); prints the next command per extension |
| `settings …` | `init`, `skills sync`, `preflight` join `apikeys` (no `setup` verb) |
| `advanced …` | every old single-step command, unchanged, one level down |

Built 2026-10-12: suite green. Still owed before this ships: operator runs the six commands on
a real extension (docker `check`, `ship`, a `--publish` update once #1 is approved).

Done = an extension goes recipe → store → health check using only the top-level commands;
skills, README, and `docs/creating-an-extension.md` lead with them.


## v1.I — Slots, status, release, hub, listing URLs (shipped 2026-10-03)

D-026, D-028–D-030. Hub export empty until store IDs + tool pages exist; lamill.io pages 404.

### v1.I plan: — Slots, status, release, hub, listing URLs

D-026, D-028, D-029. `registry.json` `slots {used, limit}`; `tabmill status` (registry +
fetchStatus + slots); `tabmill release <slug>` (release steps → `HUMAN: publish` line, warns at
the slot cap, then `hub`); `tabmill hub` writes lamill.io `src/content/extensions.json` per its
zod contract (`slug, name, pitch, store_url, tool_page_url, permissions[{name,reason}],
data_collected, analytics, changelog[{version,date,notes}], status`) and deploys via `lamill`;
recipe gains `changelog:`; listing gets privacy/support URLs; release lint checks them live.


## v1.H — API keys + preflight (shipped 2026-10-03)

D-025. Probe "valid" paths verified against mocks only (no real credentials yet).

### v1.H plan: — API keys + preflight

Mirror lamill (`settings apikeys`, `portfolio.env`, probes; command preflights) — D-025.

- `tabmill.env` (gitignored; replaces `.env`; template `tabmill.env.example`): atomic write
  (tmp + rename, mode 600), comments/order preserved.
- `tabmill settings apikeys list | set | delete`: known keys = `CWS_*`; `set` strict unless
  `--force`, value prompted hidden when omitted; `delete` confirms unless `--yes`; `list`
  masks values and probes: token exchange (SA / OAuth), SA key file parses, publisher access
  via read-only fetchStatus on the first registered `store_id`.
- `tabmill preflight`: workspace, builder, docker daemon, container image, X11, credentials.
  Commands run only the checks they need first (docker for build/test/zip/dev/assets/try,
  X11 for try, credentials for publish).

Done = `settings apikeys list` shows probe results; `preflight` reports ✓/↷/✗ with fixes;
`try` with no X11 / `build` with docker down fail fast with the fix.


## v1.F — CLI `try` (shipped 2026-10-03)

D-023. Operator confirmed the window opens on the desktop and the extension works.

### v1.F plan: — CLI `try`: test an extension by hand in Chromium

Operator (2026-10-03): a command that starts Chrome inside docker so they can test the extension.

- `tabmill try <slug> [--url URL] [--dev]`: regenerate + build (or start the WXT dev server with
  `--dev`), then launch Playwright's Chromium **headed** in the `tabmill-ext` container with the
  unpacked build loaded; the window appears on the host desktop via the container's X11
  forwarding. Real toolbar button → real activeTab grant.
- Profile in the container only (`/root/.tabmill-try/<slug>`), reused across runs; never on host.
- Chromium installed in the container only (same as smoke). Ctrl-C closes the browser.
- `✗` with a fix when `$DISPLAY` / X11 isn't available.

Done = operator can open #1 and #2 via `tabmill try`, click the toolbar icon, and use them.


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


