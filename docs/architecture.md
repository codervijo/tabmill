# Architecture — tabmill

How Tabmill is built. The "HOW" companion to `docs/prd.md`. v1.A: target shape, mostly
proposed — sections marked *(proposed)* depend on decisions not yet accepted.

## 1. Project layout

Two repos, side by side (D-002, D-006):

```
droyfun/
├── tabmill/                 TOOL_DIR
│   ├── cli/  packages/  templates/  skills/  ci/  docs/
│   └── .claude/skills/tabmill-dev/
└── tabmill-extensions/      WORKSPACE_DIR
    ├── .claude/skills/      installed — never hand-edited
    ├── .github/workflows/   installed
    ├── extensions/<slug>/{extension.yaml, README.md (generated), src/}
    ├── registry.json  CLAUDE.md (generated)  TODO.md
    ├── Makefile + Makefile.local (generated; builder overrides, ADR-0005)
    ├── pnpm-workspace.yaml  (includes ../tabmill/packages/*)
    └── .tabmill-ref         (TOOL_DIR commit pinned for CI)
```

## 2. Core mechanisms

- **YAML → manifest**: the Python CLI validates extension.yaml (pydantic schema) and writes a
  generated manifest JSON into the extension; `wxt.config.ts` (ADR-0004) only reads that file.
  The CLI also writes `version` into the extension's `package.json` (WXT names the zip from it).
- **Node boundary** (ADR-0003): the CLI runs Node work as `make <target>` in WORKSPACE_DIR,
  which forwards to the builder docker. Nothing Node runs on the host.
- **Linking** *(proposed)*: pnpm workspace spanning both repos; `@tabmill/*` as `workspace:*`
  symlinks; TS source consumed directly by Vite.
- **Skill install/sync**: copy `skills/*` → `WORKSPACE_DIR/.claude/skills/`; refuse when an
  installed copy differs from the last synced version (hand edit detected).
- **Lint modes**: each policy rule has a dev severity and a release severity; `lint --release`
  (zip for release, release skill, tag CI) applies the release one. `cta-placeholder` = warn → error (D-015).
- **Release**: build → lint --release → smoke → zip → assets → listing → `HUMAN: publish` line. Publish
  (attended) = CWS API v2 upload + publish on an existing item.

## 3. Data shapes / schemas

- **extension.yaml** (kickoff field list; typed schema lands in v1.C): `name`, `slug`,
  `version`, `single_purpose`, `template`, `permissions[] {name, justification}`,
  `optional_permissions[]`, `portfolio_site`, `landing_page_url`, `target_keywords[]`,
  `cta_text`, `cta_url`, `utm_campaign`, `store_category`, `analytics` (default `false`),
  `theme` (optional). Policy spike suggests adding: `remote_code`, `privacy_policy_url`,
  `data_usage {categories, limited_use}` — decide in v1.C.
- **registry.json**: per slug — `version`, `store_id` (from dashboard "Add new item"),
  `status`, `review_state`, `metrics[] {date, report, value}` (from CSV import).
- **tabmill.config.json**: `{ "workspace": "<path>" }`; env `TABMILL_WORKSPACE` overrides.

## 4. Modules

None yet. Planned packages: brand, funnel, messaging, analytics, policy (extracted in v1.C/v1.E).

## 5. CLI / UX surface

`init`, `skills sync` (v1.B) · `new`, `dev`, `test`, `build`, `zip`, `lint` (v1.C) ·
`assets`, `listing`, `publish` (v1.D) · `landing`, `status` (v1.E). Output uses `✓ ↷ ✗`.

## 6. Integrations / external APIs

- **Chrome Web Store API v2** — `chromewebstore.googleapis.com`; service account (preferred)
  or OAuth refresh token; scope `.../auth/chromewebstore`. Cannot create items or change
  visibility. Details: `skills/tabmill-release/reference.md`.
- **lamill CLI** — `lamill settings gsc submit-sitemap --site <d>`; landing pages deploy by
  git push to the site repo. No IndexNow (D-016).
- **GitHub** — tabmill is private; workspace CI checks it out with `TABMILL_PAT` (ADR-0006).
- **Metrics** — dashboard CSV export only.

## 7. Stack baselines

- **CLI:** Python ≥ 3.11, uv; typer, rich, httpx, pydantic, pyyaml.
- **Extensions (docker only):** Node ≥ 22, pnpm (only), TypeScript ~5.9 strict, WXT 0.21.x
  (ADR-0004), Playwright with `channel: 'chromium'`.

## 8. Active implementation plans

See `PLAN.md`.

## 9. Risks

- Portfolio/duplicate-functionality policy — the largest store risk (NOTES § Spike 5).
- Cross-root pnpm workspace is undocumented behaviour (D-006).
- WXT is pre-1.0 — pin minor.
- Builder fit: handled by workspace `Makefile.local` (ADR-0005) — can drift from builder changes; Playwright image (v1.46.0) bump needs a Tabmill-owned Dockerfile.
- New-publisher cap of two published extensions.

## 10. Tracked refactors

(none)
