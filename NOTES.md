# NOTES — tabmill

Spike findings, blockers, and the time-to-first-build log. Facts here were verified on the
date shown against the cited source; anything not verified is marked UNVERIFIED.

## Time-to-first-build log

Measured from "extension.yaml agreed" to "unpacked build loads in Chrome".

| # | slug | phase | start | first build | elapsed | notes |
|---|---|---|---|---|---|---|
| 1 | save-page-pdf-md | v1.C | — | — | — | generator stub built in v1.B (build 4.7 s incl. install) |
| 2 | local-seo-checker | v1.E | — | — | — | target: far below #1 |

## Blockers

(none)

## v1.C test URLs (approved 2026-10-03)

| # | URL | covers | Markdown | PDF |
|---|---|---|---|---|
| 1 | https://en.wikipedia.org/wiki/Markdown | images, references | — | — |
| 2 | https://daringfireball.net/projects/markdown/syntax | long single doc | — | — |
| 3 | https://www.paulgraham.com/greatwork.html | plain essay | — | — |
| 4 | https://martinfowler.com/articles/microservices.html | figures, sidebars | — | — |
| 5 | https://docs.python.org/3/tutorial/introduction.html | code blocks | — | — |
| 6 | https://developer.mozilla.org/en-US/docs/Web/HTML/Element/table | tables | — | — |
| 7 | https://github.com/mozilla/readability | README in app chrome | — | — |
| 8 | https://developer.chrome.com/docs/extensions/develop/concepts/activeTab | docs site | — | — |
| 9 | https://react.dev/learn | JS-rendered page | — | — |
| 10 | https://news.ycombinator.com/ | non-article fallback | — | — |

## Observations

- 2026-10-03 (v1.C, automated, in docker): save-page-pdf-md builds to 61 kB (extractor 37.6 kB,
  popup 14.3 kB, print 2.7 kB); zip 23.5 kB. Manifest permissions = activeTab, scripting,
  storage; no host permissions. turndown's browser build excludes `@mixmark-io/domino`
  (absent from bundle). No `eval` / `new Function` / remote `.js` URLs in output.
  Unit 6/6, typecheck clean, smoke 3/3 (shell; print page sanitizes `<script>`, `on*`,
  `javascript:`; handoff consumed). **Not automated:** toolbar click → activeTab →
  extraction on real pages, Markdown download, print dialog → operator's 10-URL run.

- 2026-10-03: Chrome Web Store category names are not listed on developer.chrome.com
  (best-listing, discovery, cws-dashboard-listing checked) → `store_category` stays ‹FILL›,
  picked in the dashboard at "Add new item".
- 2026-10-03 (v1.B docker verification): builder react image ships pnpm 12.8.1; WXT 0.21.4 +
  Vite 8.3.2 build in the container (popup bundle 1.9 kB; prod manifest = declared permissions
  + action only). Container runs as root → `in-docker-*` chowns created files back; pnpm store
  pinned to `/root/.pnpm-store` (it had landed at the mount root `~/work/projects/.pnpm-store`,
  removed). Playwright 1.63 Chrome for Testing 153 installed inside the container; smoke 1.2 s.

- 2026-10-03: in `chrome-extension-projects`, pre-existing legacy changes went from unstaged to
  staged while tabmill init ran; tabmill never runs git in the workspace — staged by someone else.

---

## v1.A spikes (2026-10-03)

### Environment

- Host: Node **v12.22.9**, no npm/pnpm/bun. Lamill Node work runs inside the docker builder
  (`~/work/projects/builder/`, `Dockerfile.react` = latest Node + pnpm; `Dockerfile.playwright`
  = `mcr.microsoft.com/playwright:v1.46.0-noble` + pnpm, X11-forwarded headed mode).
- WXT needs Node ≥ 22; Vite 8 needs Node ^20.19 or ≥ 22.12.
- **Rule since 2026-10-03 (ADR-0003): never run Node on the host.** The v1.A spike builds below
  were run with a portable Node 22 in the session scratchpad, before the rule was stated; that
  copy and all spike artifacts were deleted. Re-verify the build results inside the builder
  docker in v1.B.

### Spike 1 — Framework

Install weight measured in an empty project (`npm install --ignore-scripts`; lock entries
include platform-optional binaries):

| | WXT | Plasmo | crxjs + Vite | Vite only |
|---|---|---|---|---|
| latest | 0.21.4 (2026-08-11) | 0.90.5 (2025-05-17) | 3.0.0 (2026-09-24) | 8.3.2 (2026-10-01) |
| activity | daily commits | none on default branch since 2025-05-17 | active | — |
| open issues / PRs | 165 / 60 | 346 / 24 | 14 / 4 | — |
| lock entries / size | 176 / 90 MB | 646 / 509 MB | 91 / 87 MB | 61 / 64 MB |

- **WXT:** manifest can be a function in `wxt.config.ts` (+ `build:manifestGenerated` hook);
  entrypoints for popup, background, content scripts, devtools, side panel; HMR for pages,
  per-part reload for content/background; `wxt:locationchange` for SPAs like Google Maps;
  `createShadowRootUi`; `wxt zip`. Vanilla TS works (content/background runtime code must sit
  inside `main()`). Sources: wxt.dev/guide/essentials/{config/manifest,config/hooks,entrypoints,content-scripts,publishing}, wxt.dev/guide/development.
- **Verified by real build** (WXT 0.21.4, Vite 8.3.2, pnpm): extension.yaml parsed in
  `wxt.config.ts` became the manifest; vanilla side panel + background importing a TS-source
  package from another directory tree built with no extra config; prod manifest held only the
  declared permissions — dev-time `scripting` permission and reload code did not leak.
  Gotcha: zip name took `version` from `package.json` → the CLI must write it there.
- **Plasmo:** effectively unmaintained, Parcel-based, heaviest. Rejected.
- **crxjs:** healthy again (v3.0.0); dynamic `defineManifest`; no built-in zip; side panel /
  devtools undocumented (UNVERIFIED). Fallback if WXT gets in the way.
- Not yet verified: hot reload and side-panel/devtools behaviour in a real Chrome.

### Spike 2 — Cross-directory linking

- **Tested:** a pnpm workspace in WORKSPACE_DIR listing `'../tabmill/packages/*'` resolves
  `workspace:*` to symlinks, installs tool packages' deps in place, lockfile records
  `link:../../../tabmill/packages/<pkg>`. This cross-root case is **not explicitly documented**
  by pnpm. Side effect: `node_modules/` appears inside TOOL_DIR packages (gitignored).
- `link:` doesn't install the target's deps; `file:` is a snapshot copy; publishing to a
  registry forces a version bump per shared change; TS paths / `resolve.alias` duplicate
  config and skip deps. Git-subdirectory deps UNVERIFIED.
- Vite's fs allow-list uses the workspace root from `pnpm-workspace.yaml`, so linked sources load.
- **CI** must check out tabmill beside the workspace at a pinned ref (`actions/checkout`
  with `path:`; a private tabmill repo needs a PAT secret). Current: checkout v7.0.1,
  setup-node v7.0.0, pnpm/action-setup v6.1.0.

### Spike 3 — Chrome Web Store API

Source: developer.chrome.com/docs/webstore/{api/v1,using-api,service-accounts,publish,api/reference/rest}, /blog/cws-api-v2.

- **V1 deprecated, supported only until 2026-10-15.** V2 (released 2025-10-15) at
  `https://chromewebstore.googleapis.com`.
- **V2 cannot create new items.** First upload of every extension = dashboard "Add new item";
  Store listing + Privacy tabs filled in the dashboard. Visibility is dashboard-only.
- Methods: `upload`, `publish` (`DEFAULT_PUBLISH` / `STAGED_PUBLISH`, `deployInfos`,
  `skipReview`, `blockOnWarnings`), `fetchStatus`, `setPublishedDeployPercentage`
  (>10k 7-day users only), `cancelSubmission`.
- Auth: OAuth client + refresh token, **or service account** (one per publisher, linked in
  Dashboard → Account). Scope `https://www.googleapis.com/auth/chromewebstore`.
- **New publishers are limited to two published extensions**; more can be requested in the
  dashboard ("in most cases" decided immediately).
- Rate limits: undocumented (UNVERIFIED).

### Spike 4 — Metrics

- No API for installs / users / impressions (V2 has only the five methods above).
  Dashboard-only, CSV export per report with date range; **CSV columns undocumented** —
  importer design needs a real export.
- Dashboard "Users" counts installations, not activity.
- Optional per-item GA4 opt-in: listing page views, `install` event, UTM attribution;
  2-month retention; Marketer role only. GA4 Data API access to that property UNVERIFIED.
- Design (v1.G): `tabmill status --import <csv>` → `registry.json` `metrics[]`
  `{date, report, value}` per extension, idempotent by (date, report).

### Spike 5 — Policy

Full rule table + sources: `skills/chrome-store-policy/reference.md`. Headlines:
- **Portfolio risk is the biggest risk:** spam policy forbids duplicate functionality across
  one publisher's extensions; minimum functionality bans near-identical template extensions.
  No numeric threshold → `portfolio-similarity` lint is a heuristic; human review decides.
- Analytics: opt-in satisfies consent but **does not exempt disclosure**; in-UI prominent
  disclosure required (not only in a privacy policy); privacy policy required if any user
  data is handled; Limited Use certifications.
- CTA: no rule specifically about links to the publisher's own sites; ads rules apply
  (attributed, removable, never required); an extension whose purpose is opening a site is banned.
- Limits: `name` ≤ 75, `description` ≤ 132; icon 128 (96 art + 16 pad); screenshots 1–5 at
  1280×800 or 640×400; small promo tile 440×280 mandatory; marquee 1400×560 optional.

### Spike 6 — Playwright

Source: playwright.dev/docs/chrome-extensions, Chromium PSA (Chrome 137).
- Playwright 1.63.0. Extensions load only via `launchPersistentContext` with
  `--disable-extensions-except` / `--load-extension`, and **only with `channel: 'chromium'`**
  — branded Chrome removed `--load-extension` in Chrome 137.
- Headless works (new headless); no Xvfb needed in CI. Extension ID from the service-worker URL.
- Toolbar click and `activeTab` grant can't be simulated → open `popup.html?tabId=N` directly,
  or add a fixture-origin host permission **in the test build only**.
- CI: `playwright install --with-deps --no-shell chromium`; don't cache browsers.
- Builder's `Dockerfile.playwright` pins v1.46.0 — older than current; check before reuse.

### Spike 7 — lamill landing integration

Read from `~/work/projects/sites/portfolio` (lamill CLI) on 2026-10-03:
- Target portfolio sites are **not uniform**: `markpdf.dev` cf-pages/Astro; `calcengine.site`
  vercel/Astro; `washcalc.app` vercel/Vite-React; `lamill.io` vercel/TanStack Start.
  All have GitHub remotes and deploy git-integrated (push to `main`).
- No Rankmill public site found (`sites/rankmill` is a Python tool) → CTA target is an open question.
- Reusable: `lamill settings gsc submit-sitemap --site <d> [--force]` (idempotent).
  IndexNow ping exists only as step 10 of `lamill new deploy`; **no standalone command** for an
  already-live site.
- Write surface: landing pages land in the site repo (`sites/<domain>/`), not in Tabmill's dirs.
- MarkPDF has no API: markpdf.dev produces PDFs via `window.print()` with print CSS.

### Spike 8 — Claude Code skills

Source: https://code.claude.com/docs/en/skills.md
- `SKILL.md` with YAML frontmatter at line 1: `name`, `description` (truncated at 1,536 chars;
  drives auto-invocation), optional `when_to_use`, `allowed-tools`, `disable-model-invocation`,
  `user-invocable`, `context: fork`, `model`, etc.
- Project skills: `.claude/skills/<name>/SKILL.md`; loaded from the start dir and every
  parent up to the repo root; nested dirs load on first edit there.
- Supporting files beside SKILL.md, linked relatively. Docs suggest ≤ ~500 lines; Tabmill's
  own rule is ≤ ~150.
