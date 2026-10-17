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
bootstrap → try → check → ship. Plan accepted 2026-10-15; design below the phase table.

#### Phases

| Phase | Status | Title |
|---|---|---|
| v2.A | ✅ done | v2 plan; `publish` top level (`ship` never uploads); recipe schema v2 + v1→v2 migration; `portfolio.yaml`; `status` · `slots` · `templates` · `doctor`; `new <slug>` → `bootstrap` (deprecated alias) |
| v2.B | ✅ done | Stage engine + session storage + AI runner (prompt registry, JSON validation, repair, record/replay) + clarify for rough ideas + AI cost shown after every command that calls AI + fix: `check` no longer runs apt on every smoke run |
| v2.C | 🔄 in progress | Brief input (`--paste`, stdin, `--brief`, auto-detect), parser + schema, `brief check`, gap-only clarify |
| v2.D | ⏳ planned | Shape + rules engine (shared with `check`) + template fit + overlap |
| v2.E | ⏳ planned | Evidence: lamill integration, evidence files, provenance model, `evidence add` |
| v2.F | ⏳ planned | Verdict (rubric + cap) + write (recipe v2, idea.md, slot diff) + `approve` + `ideas list/show/compare` |
| v2.G | ⏳ planned | Target-adapter seam: chrome-mv3 behind the interface, templates migrated, page-overlay stub |
| v2.H | ⏳ planned | First real runs (word counter, page ruler briefs) → winner through approve → ship; retro; prompts tuned to v2 |
| v2.I–v2.Z | — | Reserved for fixes found in v2.H; work that doesn't fit v2 moves to v3.A |

Versions: tabmill phases are `v2.A … v2.Z`. Extensions keep their own numeric store versions
(`0.1.0`, `0.1.1`, …), which are unrelated to tabmill phases. A recipe's frozen revision is a
plain integer (`recipe_revision: 3`). That keeps it from being read as a store version or a
phase.

#### Starting point (read 2026-10-15)

| Area | Today | Notes |
|---|---|---|
| CLI | `cli/tabmill/cli.py` (898 lines). Top level: `new` · `try` · `check` · `ship` · `status` · `settings` · `advanced` (D-038) | Build-stage logic lives inside `cli.py` (`_release`, `_publish`, `_tool_page`, …), so it is not thin |
| Recipe schema | `schema.py` pydantic `Recipe` (extra=forbid), plus checks in `extension.validate` (lengths 75/132, template permissions, justifications) | No `schema_version`. `Template` literal lists `devtools` and `context-menu`, which have never been built |
| Starter recipe | `templates/recipe/extension.yaml.tmpl`, `‹FILL›` everywhere | Written by `new <slug>` on its first run (`catalog.create`) |
| Lint | `lint.py`: 13 rules with dev and release severity (`perm-broad-host`, `fill-placeholder`, `cta-placeholder`, `privacy-coverage`, `portfolio-similarity`, bundle and live-URL rules) | Rules are code plus a severity table. No YAML |
| Portfolio state | Workspace `registry.json`: per-slug `store_id`, review/published state, `slots {used, limit}` (used = PUBLISHED). `lifecycle.next_step` | Store-side truth, written by `status --refresh` |
| Templates | `templates/extension/{_shared,popup,side-panel,maps-overlay}` → WXT, chrome-mv3 | |
| Recipes | `save-page-pdf-md` (published), `local-seo-checker` and `pressure-wash-quote` (built, not in the store) | Recipe YAML carries comments that hold decisions (D-035 notes), so migration must keep them |
| AI | None in tabmill | lamill runs `claude -p --output-format json --allowedTools "" --max-budget-usd …` (`fix_helpers.run_claude_text`) |
| lamill | Already a subprocess dependency (`lamill settings gsc submit-sitemap`) | `lamill new validate` returns SERP shape: top-10, PAA, AI Overview, features; `--synthesis-only` = AI guess, labelled. `lamill new trends` returns a relative 0–100 interest index. **Neither gives monthly search volume** |
| Tests | 122 passing, ruff + mypy strict clean | `conftest.py` copies `skills/`, `templates/`, `ci/`, `privacy-policy.yaml` into a tmp tool dir |

#### Keep / change / migrate

**Keep unchanged**
- Build-stage behaviour of `try`, `check`, `ship`, and every `advanced` and `settings` command.
- WXT templates and generator output, plus `registry.json` as the store-side record. Nothing
  under `WORKSPACE_DIR/extensions/` is hand-edited.
- Existing tests: they must pass at every phase. Only intended changes to the CLI surface may
  touch them: the `new` alias warning and new commands in the help.
- No new runtime dependency planned. JSON Schemas come from pydantic (`model_json_schema()`),
  and YAML uses pyyaml. If a phase needs a dependency, it gets a `DECISIONS.md` row first.

**Change**
- `new` becomes the idea-stage entry point. Today's `new <slug>` (generate) becomes `bootstrap
  <slug>`. `new <existing-slug>` is a deprecated alias for it through v2, prints a warning, and is
  removed in v3.A.
- Top level becomes: `new` · `brief` · `ideas` · `evidence` · `approve` · `bootstrap` · `try` ·
  `check` · `ship` · `publish` · `status` · `slots` · `templates` · `doctor` · `settings` · `advanced`.
  `doctor` runs today's `settings preflight` checks plus idea-stage checks (`claude` and `lamill`
  on PATH, prompts and rules load, recipes on schema v2). `settings preflight` keeps working and
  calls the same code.
- Recipe-level lint rules move into the shared rules engine (`rules/lamill.yaml` plus predicate
  code). The bundle and live-URL rules stay in `lint.py`, because they need a build or the network.
- The `Template` literal is driven by a templates registry: implemented `popup`, `side-panel`,
  `maps-overlay`; `page-overlay` as a stub (it can be named but not generated). `devtools` and
  `context-menu` come off the accepted list. No recipe uses them.

**Migrate**
- Recipes v1 → v2 by text insertion, not a YAML round-trip, so comments survive. New top-level
  keys go after the header comment; existing lines stay untouched. The loader also accepts v1 in
  memory with a `↷ schema v1 — run tabmill doctor --fix` hint.
- `portfolio.yaml` (new, tool repo) is seeded from the recipes plus `registry.json`: slot limit
  2, `save-page-pdf-md` published, and the other two bootstrapped. Their approval is marked
  `migrated`: grandfathered, with no retroactive verdict.

**CLI thinness.** All new idea-stage logic lives in modules, and `cli.py` only parses and
renders. Moving the existing build-stage helpers out of `cli.py` is logged as a tracked refactor
in `docs/architecture.md`. It is not done in v2, to keep the risk to the working ship path low.

#### CLI and `new` dispatch

```
IDEA STAGE (rough idea or brief → approved recipe)
  tabmill new ["rough idea" | --paste | - | --brief <file>]
        --evidence <file> (repeatable) · --non-interactive · --resume <idea-id> · --template <name>
  tabmill new clarify|shape|evidence|verdict [idea-id]   re-run one stage
  tabmill new validate|trends [keywords]                  demand research via lamill
  tabmill brief check <file>
  tabmill ideas [list | show <id> | compare <id> <id>…]
  tabmill evidence add <idea-id> <file>
  tabmill approve <idea-id>
BUILD STAGE
  tabmill bootstrap <slug> [-t template]    today's `new <slug>`
  tabmill try|check|ship <slug>             unchanged
PORTFOLIO
  tabmill status [slug] · slots · templates · doctor
```

How `new` reads its arguments, in order. Typer takes a variadic argument list and the dispatch
is code:
1. With no arguments and a TTY, it asks "Paste a Tabmill brief or describe the idea" and reads
   multi-line input until EOF or a blank `.` line. With no arguments and no TTY, it errors.
2. If the first token is exactly one of `clarify`, `shape`, `evidence`, `verdict`, `validate`,
   `trends`, the command runs that stage or research step. A quoted idea such as `"validate my
   json"` is a single token, so it stays an idea.
3. A single token that names an existing `recipes/<slug>/` runs the deprecated alias:
   `↷ tabmill new <slug> is deprecated — use tabmill bootstrap <slug> (removed in v3.A)`, then
   bootstrap. A single slug-shaped token with no recipe also takes the alias and writes the
   starter recipe (today's first-run behaviour; built in v2.A).
4. `-` reads stdin, `--paste` reads multi-line pasted input, `--brief <file>` reads a file.
5. Text whose first non-blank line is `---` and whose front matter holds `tabmill_brief:` is a
   brief. Anything else is a rough idea, with the tokens joined into one string.

Today's `create` (starter recipe from `‹FILL›`) stays available as `advanced create`.

#### Architecture

```
cli.py (parse + render)
  └─ idea/engine.py      stage engine: ordered stages, session state, staleness, resume
       ├─ idea/stages/clarify.py   kind=ai    prompts/clarify_v1.md
       ├─ idea/stages/shape.py     kind=ai    prompts/shape_v1.md
       ├─ idea/stages/evidence.py  kind=data  providers: lamill, files, brief, overlap
       ├─ idea/stages/check.py     kind=rule  rules engine (shared with `check`)
       ├─ idea/stages/verdict.py   kind=ai    prompts/verdict_v1.md + code-side score and cap
       └─ idea/stages/write.py     kind=gen   recipe v2 + idea.md + portfolio diff
  ├─ ai.py          claude -p runner: prompt registry, JSON validation, one repair, record/replay
  ├─ brief.py       Tabmill brief v1 parser (section-tolerant) + `brief check`
  ├─ provenance.py  Fact model + kind rules
  ├─ rules.py       loads rules/lamill.yaml; deterministic predicates; severity by context
  ├─ recipe_v2.py   schema v2, migration, freeze hash
  ├─ portfolio.py   portfolio.yaml: slots, items, lifecycle
  └─ targets/       Target adapter protocol; chrome_mv3 implementation
```

**Stage engine.** Every stage declares `name`, `kind` (`ai | data | rule | gen`), `needs`
(upstream stages) and `run(session) -> StageOutput`. Outputs are written to
`ideas/<id>/stages/NN-<stage>.json`, each with an input hash. Re-running a stage marks every
downstream stage stale. `--resume` continues from the first stage that is missing or stale. A
stage is idempotent: same inputs and the same prompt version give the same recorded output,
because outputs are replayed from the stage file unless the stage is re-run.

**AI runner** (`ai.py`)
- Runs `claude -p <prompt> --output-format json --allowedTools "" --max-budget-usd <cap>` with
  `--model` taken from config, so there is no tool use.
- The prompt comes from `prompts/<purpose>_v<N>.md`, which has front matter
  (`purpose, version, output_schema`) and a `{{var}}` body rendered with the existing
  `templates.render`.
- The model's reply must be one JSON object that validates against the stage's pydantic model.
  On failure it sends one repair call carrying the validation errors. If that also fails, the
  stage fails with `✗` and the raw output saved to `ideas/<id>/raw/<stage>-<ts>.txt`.
- Each call records `{prompt, prompt_version, model, started, finished, cost_usd?, input_hash}`
  in the stage file. The model and cost are read from the CLI's JSON envelope when present; if
  absent they are recorded as unknown, never guessed.
- Record/replay: `TABMILL_AI=replay:<dir>` serves responses from fixtures keyed by
  `<purpose>_v<N>-<input_hash>.json`, and `record:<dir>` writes them. CI and tests use replay
  only, with no live AI.
- If `claude` is missing, the command fails with `✗ claude CLI not found — install Claude Code`.
  A timeout gets yellow `↷` and a retry hint.

**Evidence providers** share one interface: `collect(idea) -> list[Fact]` plus a `status`.
- `LamillProvider` runs `lamill new validate <kw> --json --non-interactive` and
  `lamill new trends <kw> --json`. Facts are `real`, source `lamill new validate` with the date.
  `--synthesis-only` output is kind `synthesis`.
- `FileProvider` reads `--evidence` files and `evidence add` files.
- `BriefProvider` reads the brief's Evidence section.
- `OverlapProvider` compares against existing recipes, reusing `lint.similarity`.
- `TregProvider` and `StoreCompetitionProvider` are declared but report `not available`. They
  are not implemented in v2.
- Missing evidence is a recorded `missing` fact, never a filled-in number.

**Rules engine.** `rules/lamill.yaml` holds data: the permission allowlist (`activeTab`,
`scripting`, `storage`, `sidePanel`, `downloads`, `contextMenus`, `alarms`, `notifications`), the
broad-host patterns, length limits (75 and 132, from the target), brand-name denylist patterns
for store names, and a per-rule severity for each of `idea`, `dev` and `release`. Predicates are
Python, keyed by rule id. Both the idea-stage `check` and the build `check`/`lint` call
`rules.evaluate(recipe, context)`, so they cannot disagree. Only the severity column differs by
context. `<all_urls>` without a justification is an error in every context.

**Recipe store.** Recipe schema v2 (Data shapes below) is the single source of truth. `approve` stores
`sha256` of the recipe's frozen fields in `portfolio.yaml`. `bootstrap`/`check` fail when the
frozen fields changed and `recipe_revision` was not bumped and re-approved. Fields tabmill
itself rewrites during a release are outside the freeze: `version`, `changelog`,
`landing_page_url`. Otherwise every store update would need re-approval.

**Targets × templates.** A `Target` protocol covers `manifest(recipe)`, `limits`,
`package(slug)`, `listing_rules` and `templates`. Only `chrome_mv3` is implemented. It wraps
today's `extension.to_manifest`, `generate`, `listing` and `zip` paths unchanged. Data lives in
`targets/chrome_mv3/target.yaml` (limits, screenshot sizes, packaging) and the code in
`cli/tabmill/targets/chrome_mv3.py`. `page-overlay` gets a registry entry (`status: stub`, its
use case, the permissions it would need) so template-fit can name it. `bootstrap` refuses it
with `✗ template page-overlay isn't built yet`.

#### Data shapes

**Fact (provenance)** — `{claim, value, source, date, kind}`; kind ∈ `real` (tabmill-fetched
data, e.g. lamill) · `external` (a row with a source URL) · `external_suggestion` (the brief's
Proposal) · `user` (operator answers) · `synthesis` (AI guess, or a row without a source) ·
`missing`. Facts flow into `idea.md` and the recipe's `provenance:` list.

**Recipe v2**: all v1 fields, plus:
```yaml
schema_version: 2
target: chrome-mv3
recipe_revision: 1          # integer; bump to change frozen fields after approve
idea_id: 20261015-word-counter   # absent for migrated recipes
trigger: toolbar            # toolbar | shortcut | context_menu | side_panel
restricted_pages: …         # what happens on chrome:// / Web Store pages
provenance: [ {claim, value, source, date, kind} … ]
```
`‹FILL›` is used only for decisions a human must make, each with a one-line `# why` comment.

**portfolio.yaml** (tool repo):
```yaml
slots: {limit: 2}           # used = PUBLISHED in registry.json; reserved = approved, not yet published
items:
  save-page-pdf-md: {lifecycle: published, approval: migrated}
  word-counter: {lifecycle: approved, idea_id: …, recipe_revision: 1, frozen_sha256: …,
                 slot: reserved, approved_at: …, checked: {version, at}}
```
Lifecycle: idea → shaped → evidenced → verdict → approved → bootstrapped → checked → shipped →
published → maintained.
- Ideas before approval are read from `ideas/<id>/session.json`.
- `checked` is recorded when `check` passes.
- `shipped` means the release folder exists.
- `published` and `maintained` come from `registry.json`. `maintained` means a later version was
  published after the first.

**ideas/<id>/** layout: `session.json` · `brief.md` (verbatim) · `stages/NN-<stage>.json` ·
`raw/` (gitignored) · `evidence/` (copied files). The id is `<YYYYMMDD>-<slug-ish>`.

**Tabmill brief v1.** Format as specified. `schemas/brief_v1.schema.json` is generated from the
pydantic model, and a test checks the file is current. The parser works section by section:
- A broken section reports `line N, section ## Evidence › ### Demand: <problem>`, and every
  section that did parse is kept. The session records the bad section as a gap, so clarify asks
  about it and the operator never has to re-paste.
- An evidence row with a source URL becomes kind `external`. A row without one becomes
  `synthesis`, with a `↷ downgraded` line.
- Proposal fields become kind `external_suggestion`. They seed `shape`, which still runs and is
  still rule-checked.
- Evidence files use the same Demand and Store competition tables, under front matter
  `idea, collected`.

#### Pipeline rules enforced in code

1. **clarify_v1**: asks only about missing fields (target user, core action, trigger, pages
   touched, what done looks like), and for a brief also about its Open questions.
   - At most 2 rounds, which code enforces. Questions are multiple choice where possible.
   - Answers are saved verbatim as kind `user`.
   - With `--non-interactive`, the questions are recorded as open, and later stages carry them
     as listed assumptions.
2. **shape_v1**: AI proposes, code then checks the proposal.
   - It proposes the single-purpose sentence, template (or `none-fits` plus a reason), and
     permissions with a reason each. Template fit is never forced.
   - It also proposes restricted-page handling, slug candidates, store name, summary, keywords,
     portfolio site and CTA.
   - Code then validates slugs (`catalog.SLUG_RE`, unused), lengths (target limits) and
     permissions (rules).
3. **evidence**: the providers above. Each keyword gets demand facts, or a `missing` fact.
4. **check** (rule, no AI):
   - single purpose is present;
   - permissions are in the allowlist or justified, and broad hosts are justified;
   - name ≤ 75 and summary ≤ 132;
   - the store name has no third-party brand names;
   - the template is implemented, or the run says it isn't;
   - a slot is free (`portfolio.yaml`: limit − published − reserved).
5. **verdict_v1**: AI scores the five rubric dimensions 0–10, with reasons. **Code** computes the
   weighted score: reach in store 35%, out-rate incumbents 25%, lamill.io audience fit 20%,
   low risk/support 10%, build effort 10%. It then maps the score to GO / GO-IF / NO-GO.
   - Thresholds start at GO ≥ 7.0, GO-IF ≥ 5.0, NO-GO below that. These are my starting values,
     not derived from data; they are tuned in v2.H.
   - Any `check` error → NO-GO.
   - **Cap**: if every demand fact or every competition fact is `synthesis`/`missing`, the
     verdict is at most GO-IF, with `needs evidence: <list>`.
   - lamill gives SERP shape and trend index, not volume or store competition. So without a
     sourced brief or an evidence file, the competition side is always synthesis and caps the
     verdict. That is intended.
6. **write**:
   - `recipes/<slug>/extension.yaml` (v2) and `recipes/<slug>/idea.md`, which holds the idea,
     Q&A, shaped concept, an evidence table with kind and source, check results, verdict and
     reasons, risks, and the next command.
   - It prints the proposed `portfolio.yaml` item as a diff and writes it only with `--apply`.
     Extensions are not tabmill phases, so nothing is written to `docs/prd.md`.
7. **approve** (human gate 1): needs a written recipe with no rule errors and a free slot.
   - It shows the verdict and the `‹FILL›` items, and asks for confirmation (TTY only).
   - It freezes the recipe and reserves the slot.
   - It refuses a NO-GO unless `--override "<reason>"` is given; the reason is recorded.

#### Done per phase

- **v2.A**: 3 recipes migrated, diff only adds keys; old suite green; alias warns; `status` shows lifecycle
- **v2.B**: rough idea → clarify Q&A saved; cost line printed; replay fixture test; repair-then-fail test saves raw output
- **v2.C**: malformed-brief test keeps parsed sections + exact line; brief with answers skips those questions
- **v2.D**: `<all_urls>` unjustified fails at idea and in `check`; lint suite unchanged
- **v2.E**: facts carry kind/source/date; missing recorded as missing
- **v2.F**: synthesis-only run capped at GO-IF; sourced brief can reach GO; approve freezes + reserves slot
- **v2.G**: generator output byte-identical for the 3 recipes; suite green
- **v2.H**: "Done when" below

Each phase stops for operator review. Commits only when asked. Subjects start with the phase (`v2.B: stage engine + AI runner`).

#### Tests

- Schema tests for briefs (valid, every section missing, malformed rows) and recipe v2
  (migration golden files, from v1 test fixtures).
- Parser tests, including one malformed brief that checks the exact line and section and the
  sections that survived.
- Rules tests, including a deliberately bad permission set (`<all_urls>` without justification
  fails in both idea and dev contexts).
- Verdict tests: a synthesis-only run is capped at GO-IF. The same brief with sources reaches GO
  under a replayed high score. Threshold boundaries are covered.
- AI runner tests: replay hit, replay miss (a clear error), repair success, repair failure
  (raw saved), `claude` missing.
- Golden end-to-end runs (rough idea and brief) from recorded `claude -p` fixtures in
  `tests/fixtures/ai/`, with no live AI in CI.
- The existing 122 tests stay unchanged, apart from the intended help-surface edits in
  `test_lifecycle.py`, which are listed in that phase's diff.

#### Decisions (resolved 2026-10-15: "1a, 2a, 3a, 4 ok")

1. v2.A stays as specified — plan + schema v2 + migration + portfolio commands (explicit
   exception to "vN.A is planning only").
2. v3 = v2 follow-ups (and the alias removal); WordPress plugins → v4.
3. `ship` never uploads. The attended upload is top-level `tabmill publish <slug>` (moved from
   `advanced publish`, built in v2.A); `ship --publish` fails with `✗ use tabmill publish <slug>`.
4. `ideas/` is committed except `ideas/*/raw/` (gitignored).

#### Done when (end of v2.H)

- `tabmill new "rough idea"`, `new --paste`, `new -` and `new --brief` all work, both
  interactively and with `--non-interactive`.
- A pasted brief with sourced evidence can reach GO; the same brief with sources removed is
  capped at GO-IF.
- approve → bootstrap → try → check → ship works on an idea that went through the new flow.
- Existing recipes migrate to v2, and the old `new <slug>` path still works with a warning.

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
