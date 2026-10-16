# v2 plan — idea stage in front of the build pipeline

Status: **accepted** (2026-10-15; § 9 resolved). v2.A done 2026-10-16; v2.B in progress. Source: the
operator's v2 spec (2026-10-15), D-039. Phase status lives in `docs/prd.md` § 5.

v2 adds an idea stage: a rough idea or a pasted "Tabmill brief" goes through clarify → shape →
evidence → check → verdict → write, then an operator `approve`, before the existing build
pipeline (bootstrap → try → check → ship) runs. It borrows lamill `new`'s lessons (free-text
input, versioned prompts, `claude -p` with no tools, real data labelled apart from AI guesses).
It does not copy lamill's code.

Versions: tabmill phases are `v2.A … v2.Z`. Extensions keep their own numeric store versions
(`0.1.0`, `0.1.1`, …), which are unrelated to tabmill phases. A recipe's frozen revision is a
plain integer (`recipe_revision: 3`). That keeps it from being read as a store version or a
phase.

## 1. What exists today (read 2026-10-15)

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

## 2. Keep / change / migrate

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

## 3. CLI (as specified, with dispatch rules)

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

## 4. Architecture

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

**Recipe store.** Recipe schema v2 (§ 5) is the single source of truth. `approve` stores
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

## 5. Data shapes

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

## 6. Pipeline rules enforced in code

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

## 7. Phases

| Phase | Scope | Done = |
|---|---|---|
| v2.A | This plan. `publish` top level, `ship --publish` refused. Recipe schema v2 + v1→v2 migration (comment-preserving) + `portfolio.yaml` seeded. `status` (lifecycle column) · `slots` · `templates` · `doctor` (preflight + `--fix` migration). `new <slug>` → `bootstrap` + deprecated alias. Templates registry (drops devtools/context-menu, adds page-overlay stub entry) | 3 recipes migrated, diff only adds keys; old suite green; alias warns; `status` shows lifecycle |
| v2.B | `idea/engine.py` + session storage + `ai.py` (prompt registry, JSON validation, repair, record/replay) + `clarify_v1` for rough ideas; `new "idea"`, `--resume`, `--non-interactive` | rough idea → clarify Q&A saved; replay fixture test; repair-then-fail test saves raw output |
| v2.C | Brief input: `--paste`, `-`, `--brief`, auto-detect; parser + `schemas/brief_v1.schema.json`; `brief check`; gap-only clarify | malformed-brief test keeps parsed sections + exact line; brief with answers skips those questions |
| v2.D | `shape_v1` + rules engine (`rules/lamill.yaml`, shared with `check`/`lint`) + template-fit + overlap | `<all_urls>` unjustified fails at idea and in `check`; lint suite unchanged |
| v2.E | Evidence: lamill provider, evidence files, `evidence add`, provenance model, treg/store stubs; `new validate|trends` | facts carry kind/source/date; missing recorded as missing |
| v2.F | `verdict_v1` (rubric + code score + cap) + write (recipe v2, idea.md, portfolio diff, `--apply`) + `approve` + `ideas list/show/compare` | synthesis-only run capped at GO-IF; sourced brief can reach GO; approve freezes + reserves slot |
| v2.G | Target-adapter seam: `chrome_mv3` behind the interface; existing templates moved behind it unchanged; page-overlay stub | generator output byte-identical for the 3 recipes; suite green |
| v2.H | First real runs: operator's two briefs (word counter, page ruler) → compare verdicts → winner through approve → bootstrap → try → check → ship; retro; prompts tuned to `_v2` | "Done when" below |
| v2.I–v2.Z | Reserved for fixes found in v2.H; nothing pre-assigned. Work that doesn't fit v2 → v3.A | — |

Each phase stops for operator review. Commits only when asked. Subjects start with the phase
(`v2.B: stage engine + AI runner`).

## 8. Tests

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

## 9. Decisions (resolved 2026-10-15: "1a, 2a, 3a, 4 ok")

1. v2.A stays as specified — plan + schema v2 + migration + portfolio commands (explicit
   exception to "vN.A is planning only").
2. v3 = v2 follow-ups (and the alias removal); WordPress plugins → v4.
3. `ship` never uploads. The attended upload is top-level `tabmill publish <slug>` (moved from
   `advanced publish`, built in v2.A); `ship --publish` fails with `✗ use tabmill publish <slug>`.
4. `ideas/` is committed except `ideas/*/raw/` (gitignored).

## 10. Done when (end of v2.H)

- `tabmill new "rough idea"`, `new --paste`, `new -` and `new --brief` all work, both
  interactively and with `--non-interactive`.
- A pasted brief with sourced evidence can reach GO; the same brief with sources removed is
  capped at GO-IF.
- approve → bootstrap → try → check → ship works on an idea that went through the new flow.
- Existing recipes migrate to v2, and the old `new <slug>` path still works with a warning.
