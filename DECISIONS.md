# DECISIONS — tabmill

Running decision log. Every runtime dependency is justified here. Status: **Accepted**
(operator agreed or routine convention-reuse), **Proposed** (awaiting operator — not built on
yet), **Open** (needs operator input). Accepted load-bearing entries graduate to an ADR in
`docs/decisions/` and link to it.

## D-001 — Skills used to initialize (Accepted, 2026-10-03)

User-level skills found in `~/.claude/skills/`: feature-table, latest-screenshot,
project-context, project-status, write-lamill-seo-page; plus plugin skills project-init,
project-check, project-adopt. No project-level skills in other Lamill repos.

- **project-init** — used: created the standard Lamill doc structure (`AI_AGENTS.md`,
  `docs/{prd,architecture,CLAUDE,bugs,shipping-history,Prompts}.md`, `docs/decisions/`, `.gitignore`).
- **write-lamill-seo-page** — not run now, but `tabmill-landing-page` delegates page content to
  it instead of restating SEO rules.
- **feature-table** — not run; `docs/prd.md` § 5 is written in its expected shape so it works.
- project-context / project-status — not used: they load or report on existing projects, and this one was empty.
  Conventions were read directly from `sites/portfolio` (lamill CLI), `builder/`, and sites.
- latest-screenshot, project-check, project-adopt — not relevant to an empty repo.

## D-002 — Directory paths (Accepted 2026-10-03; workspace part superseded by D-017)

Kickoff named `~/code/tabmill` / `~/code/tabmill-extensions`; `~/code` doesn't exist and the
session opened in `~/work/projects/droyfun/tabmill`. TOOL_DIR = `~/work/projects/droyfun/tabmill`;
WORKSPACE_DIR = `~/work/projects/droyfun/tabmill-extensions` (sibling — the linking decision
D-006 requires the sibling layout). Only `tabmill.config.json` / `TABMILL_WORKSPACE` carry it.

## D-003 — Versioning: kickoff "Phase 0–5" → v1.A–v1.F (Accepted, 2026-10-03)

Canonical scheme (`sites/portfolio/AI_AGENTS.md` § Versioning): two levels, `.A` = planning.
Phase 0 → v1.A (spikes, decisions lock), Phase 1 → v1.B … Phase 5 → v1.F. One tier for now;
retier when real friction says so.

## D-004 — Doc structure: kickoff files + Lamill standard (Accepted, 2026-10-03)

Both sets exist; each fact has one home:
- `docs/prd.md` — purpose, non-goals, phase **status table**, conformance rules, open questions.
- ~~`PLAN.md` — per-phase scope + done criteria~~ → retired by D-042: in `docs/prd.md`.
- `CLAUDE.md` (root, auto-loaded by Claude Code) — the operative Rules.
  `docs/CLAUDE.md` — Lamill-standard ADR workflow, heading hygiene, code-shape rules.
- `DECISIONS.md` (this) — log; ADRs for accepted load-bearing decisions.
- `NOTES.md` — spike findings, blockers, time-to-first-build.
- ~~`TODO.md` — work queue~~ → retired by D-041: the work queue lives in `docs/prd.md`.

## D-005 — Framework: WXT (Accepted, 2026-10-03) → ADR-0004

**Recommend WXT 0.21.x** (runs only in the docker builder, D-007). Function-valued manifest
(verified by build from YAML; under D-008 `wxt.config.ts` instead reads the CLI-generated manifest JSON);
all five template surfaces; per-part hot reload; built-in zip; daily maintenance; clean prod
output (no dev permission leak, verified). Cost: ~176 lockfile entries (dev-only — nothing
ships in the bundle beyond a tiny browser shim). Pre-1.0: pin minor.
Alternatives: crxjs 3 (lighter, but zip/dev wiring/entrypoints are ours to build; fallback);
Plasmo (unmaintained, 646 entries — rejected); vanilla Vite (most code to own).

## D-006 — Linking: pnpm workspace spanning both repos (Accepted, 2026-10-03) → ADR-0006; sibling layout superseded by D-017 / ADR-0007

`WORKSPACE_DIR/pnpm-workspace.yaml`: `packages: ['extensions/*', '../tabmill/packages/*']`;
extensions depend on `@tabmill/<pkg>: workspace:*`. Verified by test install. CI checks out
tabmill beside the workspace at the ref pinned in `WORKSPACE_DIR/.tabmill-ref`.
Risks: cross-root workspace is undocumented pnpm behaviour; relative paths force an identical
sibling layout locally and in CI; installs write `node_modules` into TOOL_DIR packages
(gitignored). **Builder constraint (found 2026-10-03):** `dev_container.sh` mounts only
`${PWD}:/usr/src/app` by default, so `../tabmill` is invisible in the container — the
workspace's `Makefile.local` (ADR-0005) sets `VOLUME_MOUNT` to mount the common parent
(`droyfun/`) and works from `tabmill-extensions/` inside it. Verify in v1.B.
Templates are not linked — `tabmill new` scaffolds them into `extensions/<slug>/src`.
Alternatives: npm/GitHub Packages publish (version bump per change — slow iteration),
`link:` (no dep install), TS paths/alias (duplicated config). tabmill is private → CI uses a
read-only `TABMILL_PAT` secret.

## D-007 — Node only inside the docker builder (Accepted, 2026-10-03) → ADR-0003

Operator rule: **never install Node on the host.** Node is used only to build/test extensions
(WXT, Vite, pnpm, ESLint/Prettier for extension TS, Playwright), always via the central builder
Makefile (`~/work/projects/builder/`, docker). The CLI shells out to `make <target>` in the
workspace; it never calls `node`/`pnpm` directly. Node ≥ 22 inside the image (WXT requirement;
`Dockerfile.react` installs latest Node + pnpm). Host tools that silently bundle Node (Python
Playwright ships a Node driver) also run in the container, not on the host.
Supersedes the earlier "where does Node run" open question.

## D-008 — CLI language: Python + uv (Accepted, 2026-10-03) → ADR-0002

Operator decision. Matches the Lamill CLI convention (lamill, rankmill): Python ≥ 3.11, uv,
typer, rich, httpx. The extension.yaml schema lives once, in Python (pydantic); the CLI
validates YAML and **generates** the manifest JSON that the extension build consumes, so no
TS-side YAML parser or schema exists. Extension code and `@tabmill/*` browser packages remain
TypeScript (they run in Chrome) and are only built through the builder.
Rejected: TypeScript CLI on Node (would require Node on the host).

## D-013 — save-page-pdf-md generates PDFs locally (Accepted, 2026-10-03)

markpdf.dev has no API (it prints via `window.print()` with print CSS). The extension renders
the PDF **locally** with MarkPDF-style branded print styling; page content never leaves the
device. "Via MarkPDF" = MarkPDF's look + a CTA to markpdf.dev, not a hand-off. Operator decision.

## D-014 — Builder adapted via workspace `Makefile.local` (Accepted, 2026-10-03) → ADR-0005

No builder-repo changes. `tabmill init` generates `Makefile.local` from a TOOL_DIR template:
WXT target overrides + parent-dir `VOLUME_MOUNT`. Operator decision.

## D-015 — Placeholder CTA URLs: warn in dev, block release (Accepted, 2026-10-03)

local-seo-checker's Rankmill CTA has no real URL yet → `cta_url:
https://rankmill.example/local-seo-audit` (placeholder; operator-given). New lint rule
`cta-placeholder`: a `cta_url` / `landing_page_url` whose host is a reserved example/test name
(RFC 2606/6761: `.example`, `.test`, `.invalid`, `.localhost`, `example.com|net|org`) or a
`‹FILL›` marker → **warning** in `tabmill lint` / `dev` / `build`, **error** in
`tabmill lint --release` (used by `zip --release`, the release skill, and tag CI). Generalizes:
rules carry a separate `release_severity`. Operator decision.

## D-016 — No IndexNow for landing pages (Accepted, 2026-10-03)

lamill pings IndexNow only inside `new deploy`; operator chose to skip IndexNow rather than add
a lamill command. Landing flow = git push + `lamill settings gsc submit-sitemap --force`.

## D-017 — Workspace = `$TABMILL_WORKSPACE` in `~/.profile` (Accepted, 2026-10-03) → ADR-0007

Operator: all Chrome extensions live in `~/work/projects/plugins/chrome-extension-projects`
(existing repo `codervijo/chrome-extension-projects`, five pre-tabmill extensions at its top
level), kept in a central env var. Exported in `~/.profile` (not `~/.bashrc`, which returns
early for non-interactive shells). Cross-repo paths are computed by `tabmill init`.

## D-018 — Tool build through the builder Makefile (Accepted, 2026-10-03)

Operator: tool build controllable via a Makefile using the builder. `Makefile` includes
`~/work/projects/builder/Makefile` (Python stack auto-detected from `pyproject.toml`);
`Makefile.local` overrides `build` (`uv build`) and `run` (`uv run tabmill $(ARGS)`) — make's two
"overriding recipe" warnings are expected — reuses the builder's `test`, adds `lint` / `fmt` /
`check`, and sets `CONTAINER_NAME=tabmill-tool` + `DOCKER_CMD=docker` so `make buildsh` uses its
own container without sudo (builder defaults: `mb1`, `sudo docker`). Runs on the host via uv.

## D-019 — Extensions generated from recipes in tabmill (Accepted, 2026-10-03) → ADR-0008

Operator: "tabmill tool [does] generating of extensions — you build only tabmill"; feature code
via per-extension recipes in the tabmill repo (option 2). Phases reslotted to v1.A–v1.G.
Kickoff deviations: extension source moves from WORKSPACE_DIR to `recipes/`; "#1 built by hand,
extract later" becomes "generic code in templates from day one"; v1.I extensions are recipes,
not workspace Claude sessions.

## D-020 — `tabmill build` pulled into v1.B (Accepted, 2026-10-03)

Generation needs manifest fields from YAML before the full v1.E build; v1.B ships a minimal
`build` (required fields, length limits, permission justifications, placeholder-URL warning,
`manifest.gen.json` + `package.json` version, WXT build in docker). Typed schema + lint stay v1.E.

## D-021 — `list` + `create` as v1.D; keep `new` (Accepted, 2026-10-03)

Operator noticed no command lists extensions or starts one; asked to add both and "pick best
defaults". Slotted as v1.D, before extension #2, so #2 starts from `tabmill create` and its
time-to-first-build reflects the real workflow; later phases shift to v1.E–v1.H. `new` is not
renamed (operator). Defaults: `list` read-only with `--json`; `create` writes only a recipe
skeleton with `‹FILL›` markers, refuses duplicates/bad slugs, never touches the workspace.

## D-022 — Shared extension code lives in `templates/extension/_shared/`, not pnpm packages (Accepted, 2026-10-03)

Extraction trigger hit in v1.E (both extensions need the shell, brand, inject helper,
messaging, tokens, smoke fixtures). Because extensions are generated (ADR-0008), the generator
overlays `_shared/` under every surface template — same single source, no package build, no
cross-repo pnpm link at runtime. `packages/` (ADR-0006/0007 linking) stays available for code
that must be versioned independently; none exists yet. Also v1.E: side-panel template; typed
schema (`cli/tabmill/schema.py`, pydantic, unknown keys rejected); `lint` / `dev` / `test` / `zip`.

## D-023 — `try` as v1.F (Accepted, 2026-10-03)

Operator asked for a command that starts Chrome inside docker to test an extension by hand;
slotted as a new v1.F, done next (it makes the v1.C 10-URL check easy); later phases → v1.G–v1.I.
Named `try` because `test` runs the automated suite.

## D-024 — Store assets, listing, publish (Accepted, 2026-10-03)

- Images rendered by Playwright Chromium in docker (`_shared/scripts/assets.mjs`): icon from
  recipe `assets/icon.svg` or a generated initials tile; screenshots = real UI page framed at
  1280×800 with a caption (recipe `screenshots:` optional, ≤ 5). Default screenshots show the
  UI at rest — replace when the feature needs showing.
- `listing` writes a Markdown draft (the API can't set listing text); keyword-repeat lint counts
  only store-visible text (summary + description).
- `publish`: CWS API v2, attended only (TTY, not CI), release lint first, confirm, upload →
  publish (default / `--staged`) → fetchStatus → registry.json. Verified against mocks only.

## D-025 — API keys + preflight as new v1.H (Accepted, 2026-10-03)

Mirror lamill's `settings apikeys list|set|delete` (known keys, atomic writes, masked values,
per-provider probes) in `tabmill.env`, plus `tabmill preflight` and per-command preflights.
Operator chose a new phase after v1.G (option B).

## D-026 — Publisher slot cap tracked in registry + status (Accepted, 2026-10-03)

New publishers get 2 published-extension slots; more are earned (dashboard request is denied
when published extensions "need higher sustained engagement" — /docs/webstore/publish,
2026-10-03). `registry.json` gets `slots: {used, limit}`; `tabmill status` shows them; release
warns at the cap. Whether unlisted/private items count: **not documented** (NOTES.md).

## D-027 — Build/publish order changed (Accepted, 2026-10-03)

Slots reward sustained use, so order: 1 save-page-pdf-md · 2 pressure-wash-quote ·
3 local-seo-checker · 4 local-schema-generator · 5 jwt-inspector (never an early slot).
local-seo-checker is already built (v1.E); the order governs publishing and what's built next.

## D-028 — `tabmill hub`: registry → lamill.io extensions.json, deployed via lamill (Accepted, 2026-10-03)

Exports registry data to `extensions.json` matching a contract in the lamill.io README, then
deploys through the `lamill` CLI; runs at the end of `tabmill release`. **Blocked:** the
lamill.io README (`~/work/projects/sites/lamill.io`, HEAD f1913e5) has no extensions.json
contract yet — operator to confirm repo path + supply/locate the contract.

## D-029 — Listing URLs on the hub (Accepted, 2026-10-03)

Privacy policy = `https://lamill.io/extensions/<slug>/privacy`; support =
`https://lamill.io/extensions/support`. Lint fails (release) if either is missing from the
listing or the hub page isn't live (HTTP 200). Item 5 of the same brief (placeholder Rankmill
CTA blocks release) was already in place (D-015).

## D-030 — v1.I defaults (Accepted, 2026-10-03)

Slot usage = items the store reports PUBLISHED (unlisted/private unknown — NOTES). `hub`
validates against a pydantic mirror of lamill.io's zod schema, writes only
`src/content/extensions.json`, skips entries lacking store/tool-page URLs, leaves the file
untouched when nothing qualifies, and never commits/deploys lamill.io (its deploy path is
still open in lamill.io's PRD) — deploy is a HUMAN step. `release` keeps an existing
`listing.md`; lint blocks release on `‹FILL›` left in it.

## D-031 — pressure-wash-quote / maps-overlay defaults (Accepted, 2026-10-03)

- `maps-overlay` template: no host permissions — toolbar click injects a shadow-root panel into
  the current tab (activeTab + scripting); second click removes it; background opens extension
  pages for content scripts (`tabmill:open-page`); `overlay-preview.html` for screenshots/smoke.
- Scale by **user calibration** on the map's scale bar (no unverified URL→meters formula).
- Rates prefilled from washcalc.app `src/rates.js` MODEL tier (copied 2026-10-03, labelled
  "WashCalc model rate — estimates, not survey data"); user's own rates stored locally.
- Store title omits "Google" (trademark policy); summary/keywords mention it descriptively.
- Quote handoff via `storage.local` (content scripts can't use `storage.session` by default).

## D-032 — Hub follows lamill.io contract change (Accepted, 2026-10-03)

lamill.io made `store_url` nullish ("In development" pages) and documented deploy = Vercel
auto-deploy from `main`. `hub` now exports any extension with a real tool page; `store_url` is
null until a `store_id` exists. Still never commits lamill.io; prints HUMAN steps (commit/push,
and sitemap.xml lines for published entries, which lamill.io maintains by hand).

## D-033 — `landing`: tabmill briefs, a Claude session in the site repo writes the page (Accepted, 2026-10-05)

Operator chose option 1: tabmill has no AI and writes nothing into portfolio-site repos.
`tabmill landing <slug>` writes a self-contained brief (target URL + queries, single purpose,
permissions/privacy, store link with UTM or "coming soon", hub link, rules) to
`extensions/<slug>/.output/store/landing-brief.md`; the page is written by a Claude session in
`~/work/projects/sites/<portfolio_site>` using the user-level `write-lamill-seo-page` skill.
`--check` confirms HTTP 200, sets the recipe's `landing_page_url`, and runs
`lamill settings gsc submit-sitemap --site <site> --force` (soft-fail; no IndexNow, D-016).
URL = `https://<portfolio_site>` + recipe `landing_path` (default `/` + first keyword, slugified).

## D-034 — Lifecycle CLI slotted as v1.L (Accepted, 2026-10-10)

Operator: too many commands, unclear which to use. Six lifecycle verbs — `new`, `try`, `check`,
`ship`, `status`, `setup` — absorb the existing ~20 (mapping in `PLAN.md` § v1.L). Slotted
after v1.K; local-schema-generator + jwt-inspector move v1.L → v1.M. Remove-vs-hide for old
commands decided at v1.L start.

## D-035 — #1 tool page targets "save webpage as pdf"; hub exports `unlisted` (Accepted, 2026-10-11)

Operator picked both. (1) save-page-pdf-md's tool page is `markpdf.dev/save-webpage-as-pdf/`:
"markdown to pdf" is markpdf.dev's own home query and the opposite direction of what the
extension does. `target_keywords` reordered (primary first); `landing_path` set with the
trailing slash markpdf.dev canonicalizes to. (2) `hub` used to export pre-store entries as
`draft`, which lamill.io 404s — but the CWS privacy URL must be live before review. New status
`unlisted` (lamill.io zod + routes: pages served with noindex, hidden from `/extensions` and
the sitemap); `hub` exports every entry not yet PUBLISHED as `unlisted`. lamill.io changed in
the same session (uncommitted there); `hub` must not run against a lamill.io without it.

## D-036 — One shared privacy policy for all extensions (Accepted, 2026-10-12) — supersedes D-029's privacy URL

Operator decision (v1.G). The privacy URL is `https://lamill.io/extensions/privacy` for every
extension, not `/<slug>/privacy`: one page that is live independent of any tool page, so a
first release is no longer blocked on the portfolio-site page (hub skipped entries without
`tool_page_url`, so the per-slug privacy page couldn't go live). Source of truth is
`tabmill/privacy-policy.yaml`; `hub` exports it to lamill.io `src/content/privacy.json` and the
page renders from it. Release lint `privacy-coverage` fails when a recipe does more than the
policy covers (a permission not listed, analytics, remote code, host permissions, collected
data) — fix by updating the policy (bump `version`), `hub`, deploy lamill.io. `hub-urls` checks
the live page shows `Policy version <N>`, so an undeployed policy change blocks release.
Per-extension permission reasons stay on the extension's hub page and listing. Support URL
unchanged (D-029).

## D-037 — WordPress plugin support slotted as tier v2 (Accepted, 2026-10-12; tier renumbered v3 by D-039)

Operator: do WordPress plugins with the same tool. Same funnel in a second channel —
single-purpose free plugins generated from recipes, "Built by Lamill" + CTA, tracked in the
same registry / hub / landing flow. New tier v2 after v1 rather than a v1 phase: a second
platform, and v1.L reshapes the command surface first. Distribution: the wordpress.org plugin
directory. v2.A = planning / decisions lock; build phases v2.B–v2.E in `docs/prd.md` § 5. First
plugin not chosen yet.

## D-038 — v1.L shape: `settings` not `setup`; old commands under `advanced` (Accepted, 2026-10-12)

Amends D-034 after comparing with `lamill --help` (lessons, not a copy): a tiny top level, depth
one level down, the same verb at one-extension and all-extensions scope, setup under one word.
- Top level: `new` · `try` · `check` · `ship` · `status` · `settings` · `advanced`.
- No `setup` verb: `init`, `skills sync`, `preflight` join `apikeys` under `settings` (same
  word as lamill; one home for setup).
- `check` and `status` with no slug run across every extension.
- Old single-step commands stay, visible, under `tabmill advanced` (operator's choice over
  hidden or removed).

## D-039 — v1 closed; v2 = AI-assisted idea intake; WordPress plugins move to v3 (Accepted, 2026-10-14)

Operator, after #1 was approved and published (store, lamill.io hub page, markpdf.dev tool page
all live): "call v1 done first and plan this for v2 (make room)". The next extension starts
from a rough idea, not a slug, so tabmill needs an idea stage before `new` writes a recipe:
AI asks clarifying questions and drafts the recipe (lessons from `lamill new`: free-text topic,
research before scaffold, `claude -p` without tools, versioned prompt files, real data labelled
apart from AI guesses). Shape set by the operator's spec — D-040.
- v1 closed with leftovers carried (operator's choice): v1.C, v1.G, v1.J, v1.K, v1.L marked done
  as built. Carried into v2.A: the first real CWS API upload + publish (`tabmill ship
  save-page-pdf-md --publish` on the first update) and v1.L real-use validation. v1.C's 10-URL
  check was never run (superseded by store approval); v1.J's real-Maps try was never run;
  the v1.K analytics package is dropped until an extension needs analytics.
- v1.M dropped as a phase; local-schema-generator and jwt-inspector stay as idea candidates
  for v2. local-seo-checker and pressure-wash-quote (built, not in the store) are not being
  pursued now.
- WordPress plugins (D-037) renumbered v2 → v3 unchanged: v3.A–v3.E (then → v4 by D-040).

## D-040 — v2 shape: idea stage per the operator's spec (Accepted, 2026-10-15)

Operator spec (2026-10-15): `new` takes a rough idea or a pasted "Tabmill brief" (claude.ai
research) → stage engine clarify → shape → evidence → check → verdict → write; `approve` (human
gate) freezes the recipe and reserves a slot; today's `new <slug>` becomes `bootstrap` (alias
through v2, removed in v3.A). AI proposes, code decides (allowlist, limits, slots, verdict cap);
every fact carries provenance; synthesis-only demand/competition caps the verdict at GO-IF.
Phases v2.A–v2.H, v2.I–v2.Z reserved. Plan: `docs/prd.md` § v2. Operator resolved its Decisions
("1a, 2a, 3a, 4 ok"): v2.A stays as specified (plan + build, an explicit exception to "vN.A is
planning only"); v3 = v2 follow-ups, WordPress → v4; `ship` never uploads — the attended upload
is top-level `tabmill publish <slug>` (amends D-038), `ship --publish` errors with that hint;
`ideas/` committed except `raw/`.

## D-009 — Store API: V2 only, service-account auth (Proposed, 2026-10-03)

V1 dies 2026-10-15; V2 can't create items, so first uploads are a HUMAN step by design.
Service account preferred over OAuth refresh token (no token expiry; one SA per publisher).
Client: hand-written `httpx` client (Lamill convention); `google-auth` only for the SA JWT
token exchange if hand-rolling it isn't simpler — decide in v1.G.

## D-010 — Metrics: CSV import (Proposed, 2026-10-03)

No metrics API. `tabmill status` imports dashboard CSV exports into `registry.json`; schema
designed from a real export (none exists yet). GA4 per-item opt-in is optional extra signal.

## D-011 — Lint / format / test (Accepted, 2026-10-03 — convention reuse)

- **Tool (Python):** `uv run ruff`, `uv run mypy --strict`, `uv run pytest` (Lamill CLI convention).
- **Extensions (TS, in docker):** ESLint 9 flat + typescript-eslint, Prettier with the lamill.io
  config, Vitest — run via builder `make lint` / `make test` targets.

## D-012 — Smoke tests + assets: Playwright in the builder's playwright image (Accepted, 2026-10-03)

Only `channel: 'chromium'` can load unpacked extensions (branded Chrome ≥ 137 can't). Headless,
no Xvfb. Runs in the builder's `Dockerfile.playwright` stack — its pin (v1.46.0) predates
current Playwright 1.63.0; bump needed (builder repo change — operator's call). Same container
renders icons/screenshots for `tabmill assets`.

## Dependency register

| package | where | runtime? | justification | status |
|---|---|---|---|---|
| typer | CLI | tool runtime | Lamill CLI convention (D-008) | Accepted |
| rich | CLI | tool runtime | `✓ ↷ ✗` colored step output | Accepted |
| httpx | CLI | tool runtime | CWS API + landing/lamill probes; Lamill convention | Accepted (v1.G) |
| google-auth (+ cryptography) | CLI | tool runtime, lazy | signs the service-account JWT only (Apache-2.0, 2.59.1); HTTP stays httpx | Accepted (v1.G) |
| pydantic | CLI | tool runtime | typed extension.yaml schema + readable validation errors (goal #5) | Accepted (v1.E) |
| pyyaml | CLI | tool runtime | parse extension.yaml; stdlib has no YAML | Accepted (v1.B) |
| types-pyyaml | CLI | dev | mypy strict stubs for pyyaml | Accepted (v1.B) |
| ruff, mypy, pytest | CLI | dev | D-011 | Accepted |
| wxt ~0.21 | extensions (docker, dev) | no | D-005 / ADR-0004 | Accepted |
| vite | extensions (docker, dev; WXT peer) | no | D-005 / ADR-0004 | Accepted |
| typescript ~5.9 | extensions (docker, dev) | no | strict typing of extension code | Accepted |
| eslint, typescript-eslint, prettier, vitest | extensions (docker, dev) | no | D-011 | Accepted |
| @playwright/test | extensions (docker, dev) | no | D-012 | Accepted |
| @types/node ^24 | extensions (docker, dev) | no | types for `wxt.config.ts` / Playwright fixtures (vitest peer `^22 \|\| >=24`) | Accepted (v1.B) |
| @mozilla/readability ^0.6.0 | save-page-pdf-md | **yes** | article extraction; Apache-2.0, 0 deps, 155 kB unpacked, ships types (npm 2026-10-03) | Accepted (operator), in v1.C |
| turndown ^7.2.4 (+ @types/turndown) | save-page-pdf-md | **yes** | HTML→Markdown; MIT, published 2026-04; one dep (`@mixmark-io/domino`, Node-only — verified absent from the browser bundle 2026-10-03) | Accepted (operator), in v1.C |
| **extension bundles** | shipped | **yes** | template adds **none**; per-extension runtime deps come from the recipe's `dependencies:` and need a row above. `@tabmill/*` packages must have zero third-party runtime deps | — |

## D-041 — Work queue lives in the PRD; TODO.md retired (Accepted, 2026-10-16)

Operator: "merge TODO.md into PRD, avoid an extra file use PRD" (after D-040's plan file was
folded into the PRD the same day). Open items → `docs/prd.md` § v2 Work queue (current phase +
carried HUMAN items); completed checklists → `docs/shipping-history.md` § Archived work queue.
"Plans before patches" now means the PRD's work queue. The workspace's own `TODO.md` (HUMAN
publish lines written by tabmill) is unchanged.

## D-042 — Phase plans live in the PRD; PLAN.md retired (Accepted, 2026-10-16)

Operator: "merge PLAN.md into the PRD too". PLAN.md held only a pointer to the PRD's v2 plan,
the carried items (already in the work queue), the idea candidates and v4.A notes — all moved
to `docs/prd.md`; the "extract, don't design upfront" principle is in the PRD header. Shipped
phase plans stay in `docs/shipping-history.md`. Supersedes D-004's PLAN.md split.

## D-043 — WordPress plugins (v4): decisions locked (Accepted, 2026-10-16)

From the v4.A spikes (`NOTES.md` § v4.A spikes); operator accepted the recommendations with one
constraint: "make sure you dont install node on my host - keep it all inside a docker container."
1. Publisher: a Lamill-named wordpress.org account; 2FA, SVN password, release confirmation on.
2. Funnel: credit/CTA in the plugin's admin screen, readme and directory page; front-end credit
   opt-in, default off (guideline 10). Tabmill's "Built by Lamill everywhere" rule is
   Chrome-only.
3. License: plugin recipes and everything they ship are GPLv2-or-later.
4. Build/test: official `wordpress`, `mariadb`, `wordpress:cli`, `php:cli` + composer images via
   the workspace Makefile. Nothing on the host — no Node, PHP, composer or svn (ADR-0003 scope
   extended to every plugin tool).
5. Layout: `plugins/<slug>/` beside `extensions/<slug>/` in the same workspace repo.
6. Slots per target: chrome-mv3 limit 2; wordpress-plugin = one submission in review.
7. Release: `ship` builds zip + SVN tree; `publish` (attended) commits to SVN from a container.
8. SCM (operator, 2026-10-16: "public repo per plugin"): GitHub stays primary, SVN gets releases
   only. Each plugin has a public GPL repo under a Lamill GitHub org with its readable source
   (guideline 4), linked from `readme.txt`; tabmill creates it at first submission and syncs it
   on `publish`. Generated output, never hand-edited.
Open: which plugin is first (v4.C).
