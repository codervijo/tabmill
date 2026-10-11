# TODO — tabmill

Work queue for the tool repo. Plans before patches: any change over ~20 lines gets a planned
item here first. When an item is done, check it off and take the next; if blocked, write the
blocker to `NOTES.md`, mark it BLOCKED, move on.

## v1.A — Kickoff / decisions lock

- [x] Initialize doc structure (project-init) + reconcile with kickoff files
- [x] Spikes 1–8 (NOTES.md)
- [x] DECISIONS.md, PLAN.md, README.md, CLAUDE.md, AI_AGENTS.md
- [x] tabmill-dev skill; drafts of five workspace skills
- [x] CLI language → Python + uv (ADR-0002); Node only in docker builder (ADR-0003)
- [x] WXT (ADR-0004), local PDF (D-013), Makefile.local overrides (ADR-0005)
- [x] Linking (ADR-0006), skip IndexNow (D-016), tabmill private, placeholder-CTA lint (D-015)
- [ ] HUMAN: set real Rankmill CTA URL + `portfolio_site` for local-seo-checker (placeholder `https://rankmill.example/local-seo-audit`; release lint blocks until replaced)
- [ ] HUMAN: `git init` TOOL_DIR (+ GitHub repo if wanted)

## v1.B — Tool + generator ✅ (2026-10-03; details in docs/shipping-history.md)

## v1.C — Extension #1 recipe: save-page-pdf-md (in progress)

Plan (all code in `recipes/save-page-pdf-md/`; workspace only via `tabmill new/build`):

1. [x] extension.yaml: permissions `activeTab` + `scripting` (inject extractor on click) +
       `storage` (session handoff popup → print page); deps readability + turndown.
2. [x] `src/entrypoints/extract.content.ts` (registration: runtime): Readability on a document
       clone → typed `Article` {title, html, byline, siteName, lang, url, fallback}; body fallback.
3. [x] `src/feature/`: popup UI (Save as Markdown / Save as PDF, status line), `?tabId=` override
       for tests, readable errors for restricted pages; Markdown via turndown (scripts/styles
       removed, title + source header) → Blob download; PDF → `storage.session` handoff → print tab.
4. [x] `src/entrypoints/print/`: allowlist sanitizer (no innerHTML into the extension page),
       MarkPDF-style print CSS (system font stacks, no remote fonts), auto `window.print()`.
5. [x] Tests: unit (filename, markdown header, sanitizer allowlist via a minimal DOM if needed);
       smoke: print page renders a seeded article and strips `<script>`/`on*` attrs.
6. [x] Build + typecheck + test + smoke in docker; confirm turndown's browser build excludes domino.
7. [ ] ⏸ ON HOLD (operator, 2026-10-03) — HUMAN: validate on the 10 approved URLs in real Chrome (load `.output/chrome-mv3` unpacked);
       record results in NOTES.md. Zip via `make in-docker-zip EXT=save-page-pdf-md`.

- [ ] HUMAN (when the workspace repo exists): create a fine-grained PAT, repo access = tabmill only,
      permission Contents: read-only — https://github.com/settings/personal-access-tokens/new — and save
      it as secret `TABMILL_PAT` in the `codervijo/chrome-extension-projects` repo (Settings → Secrets and variables → Actions)

## v1.D — CLI `list` + `create` ✅ (2026-10-03)

1. [x] `cli/tabmill/catalog.py`: rows from `recipes/*/` ∪ workspace `registry.json` — slug,
       version, template, status (`recipe` / `generated` / `built` / `✗ orphan` = registered
       but no recipe), store ID, placeholder fields (any `‹FILL›` value; placeholder CTA /
       landing URLs, D-015). Recipe that fails to parse → row with the error, not a crash.
2. [x] `tabmill list [--json]`: rich table (✓ built / ↷ placeholders / ✗ orphan or invalid);
       `--json` = list of row dicts, stable keys. Works without a workspace (recipes only, ↷).
3. [x] `templates/recipe/extension.yaml.tmpl` + `tabmill create <slug> [--template popup]`:
       slug = lowercase kebab-case ≤ 40 chars; refuse existing recipe / registry slug /
       unimplemented template; writes the starter with `‹FILL›` for name, summary,
       single_purpose, cta_text, cta_url, portfolio_site, target_keywords, store_category;
       `utm_campaign` defaults to the slug; `activeTab` with its standard justification.
       Prints next step. Never touches the workspace.
4. [x] `new` / `build` refuse `‹FILL›` in name / summary / single_purpose (manifest-facing).
5. [x] Tests: create (ok, bad slug, duplicate recipe, duplicate registry, bad template),
       list (recipe-only, generated, built, orphan, placeholders, invalid recipe, json),
       placeholder refusal in `new`.
6. [x] `tabmill-new-extension` skill step 7 → start from `tabmill create`; README, architecture,
       NOTES; sync workspace skills (stale phase refs); fix `tabmill-store-listing` input path.
7. [x] Verified on a throwaway slug in a scratch workspace: create (+ 3 refusals) → `new` refused
       while ‹FILL› → filled → `new` generated → `list` shows it; removed afterwards. WXT `build`
       of a created recipe not re-run (same path as #1, verified in v1.B/v1.C).

## v1.K — Landing + analytics (in progress)

1. [x] Schema `landing_path` (optional); `cli/tabmill/landing.py`: URL, brief, recipe update.
2. [x] `tabmill landing <slug> [--check]`: brief → print next steps; `--check` probe → set
       `landing_page_url` in the recipe → `lamill settings gsc submit-sitemap` (soft-fail).
3. [x] Rewrite `tabmill-landing-page` skill around the brief; tests; docs.
4. [ ] Analytics package (opt-in) — plan separately before code.
5. [ ] HUMAN: write the save-page-pdf-md tool page from its brief (session in sites/markpdf.dev),
       deploy, then `tabmill landing save-page-pdf-md --check` → `tabmill hub`.

## v1.I — Slots, status, release, hub, listing URLs ✅ (2026-10-03)

1. [x] registry `slots {used, limit}` (limit 2; used = store `published_state == PUBLISHED`);
       `tabmill status [--refresh]` table + slots line (`--refresh` = fetchStatus per store_id).
2. [x] Recipe `changelog: [{version, date, notes}]` (schema); listing.md gets privacy policy
       + support URLs (D-029).
3. [x] `cli/tabmill/hub.py`: entries per lamill.io zod contract (pydantic mirror); skip (↷)
       extensions lacking store_url / tool_page_url; write `<hub_repo>/src/content/extensions.json`
       (`hub_repo` in tabmill.config.json, default ~/work/projects/sites/lamill.io); never commits;
       deploy = printed HUMAN step until lamill.io settles its deploy path.
4. [x] Lint `hub-urls` (warn dev / error release): listing has both URLs; `--release` also
       requires HTTP 200 on both.
5. [x] `tabmill release <slug>`: test → assets → listing → zip --release → slot-cap warning →
       `HUMAN: publish <slug> <version>` in workspace TODO.md → `hub`. Never publishes.
6. [x] Tests; docs; tabmill-release skill uses `tabmill release`.

7. [ ] HUMAN: lamill.io — publish /extensions/<slug>/privacy + /extensions/support pages
       (release lint probes them), choose its deploy path; then `tabmill hub` output can ship.

## Slotted 2026-10-03 (v1.H–v1.M after D-034, see PLAN.md) — operator brief items

- [x] **v1.H** API keys + preflight (D-025): `settings apikeys list|set|delete` in `tabmill.env`
      (known CWS_* keys, atomic write, masked, probes: token exchange, SA key parse, publisher
      access via fetchStatus); `tabmill preflight`; per-command preflights.
- [x] **v1.I** Slots (D-026): `registry.json` `slots: {used, limit}` (limit 2 default); `tabmill status`
      shows used/limit; `tabmill release` warns at the cap.
- [x] **v1.I** `tabmill release` command (today a skill): runs the release steps, then `tabmill hub`.
- [x] **v1.I** `tabmill hub` (D-028): registry → `extensions.json` per the lamill.io contract →
      deploy via `lamill`. Contract found 2026-10-03 in lamill.io (uncommitted there): zod schema
      `src/lib/extensions.ts`, README § Extensions data contract.
- [x] **v1.I** Listing URLs (D-029): `privacy_policy_url` = lamill.io/extensions/<slug>/privacy,
      `support_url` = lamill.io/extensions/support in listing.md; release lint fails if missing
      or the hub page isn't live.
- [x] **v1.J** pressure-wash-quote recipe + maps-overlay template (D-031): unit 6, smoke 2,
      lint dev clean except store_category; first build 1 min 34 s.
- [ ] **v1.J** HUMAN: try it on real Google Maps satellite view —
      `uv run tabmill try pressure-wash-quote --url https://www.google.com/maps` → click the
      toolbar icon → calibrate on the scale bar → trace a driveway → Save estimate as PDF.
- [x] Rankmill CTA placeholder blocks release (D-015); HUMAN line below.

## v1.G — Assets, listing, publish (in progress)

1. [x] `templates/extension/_shared/scripts/assets.mjs` (Playwright, docker): icon SVG →
       PNG 16/32/48/128 (+ store icon 128 = 96 art + 16 px transparent pad); promo tile
       440×280; screenshots 1280×800 = extension UI page captured, framed on a Lamill stage
       with a caption. Output `extensions/<slug>/.output/store/`.
2. [x] Icon source: recipe `assets/icon.svg` if present, else generated (initials on accent
       tile). Icons copied into `public/icon/` so the manifest gets them. Recipe
       `screenshots: [{page, caption}]` optional; default one = UI + single_purpose.
3. [x] `tabmill assets <slug>`; lint: icon-128 / screenshot-size / promo-small rules on
       `.output/store/`.
4. [x] `tabmill listing <slug>` → `extensions/<slug>/.output/store/listing.md` (title, summary,
       description skeleton from recipe, captions, permission justifications, privacy answers);
       keyword-repeat (> 5) lint on it. Copy is a draft — `tabmill-store-listing` skill refines it.
5. [x] `cli/tabmill/cws.py`: CWS API v2 client (httpx; service account via google-auth, or
       OAuth refresh token) — upload (raw zip), publish (DEFAULT / STAGED), fetchStatus; error
       bodies → specific remediations. Mock-transport tests.
6. [x] `tabmill publish <slug> [--staged]`: refuses without a TTY / in CI, without `store_id`
       (prints first-publish dashboard steps), on `lint --release` errors; confirm prompt;
       upload → publish → status → registry.json. `tabmill status`-style read via `--check`.
7. [x] CI template: upload-artifact v7. Release lint stays local (`zip --release`, `publish`) —
       store images are rendered in docker and not committed.
8. [x] Skills: tabmill-release + tabmill-store-listing finalized; docs.
       Verified against mocks only — real publish needs operator credentials (HUMAN).

9. [ ] HUMAN: CWS credentials in `tabmill/.env` (see `.env.example`) + first dashboard upload →
       then a real `tabmill publish --check` to verify the client against the live API.

## v1.F — CLI `try` ✅ (2026-10-03)

1. [x] Chromium launcher `templates/extension/_shared/scripts/try.mjs`:
       Playwright `launchPersistentContext(profile, {headless:false, channel:'chromium', args:
       --load-extension})`, open `--url`, keep running until the window closes / SIGINT.
2. [x] Workspace Makefile.local `try` target: install chromium (as smoke), check DISPLAY, run it.
3. [x] `tabmill try <slug> [--url] [--dev]`: sync, build (or dev server in background), `make in-docker-try`.
4. [x] HUMAN: confirmed the window appears on your desktop (`uv run tabmill try save-page-pdf-md`) — launch verified from the container, window not seen by Claude. Docs done.

## v1.E — Extension #2 + extraction ✅ (2026-10-03)

1. [x] `templates/extension/side-panel/`: side panel entry (`side_panel` + `sidePanel` perm),
       action click opens panel (background), shared shell CSS/brand; smoke test.
2. [x] Extract shared template code (packages/ not needed — D-022) (both templates use it): `templates/extension/_shared/`
       (brand shell, messaging, tokens, smoke fixtures, inject helper) overlaid before the
       surface template — no third-party code, no pnpm package needed yet.
3. [x] `tabmill create local-seo-checker -t side-panel`; recipe: activeTab + scripting; checks
       on the current page, all local: LocalBusiness JSON-LD (presence + key fields), NAP
       (name/address/phone) found + consistent with JSON-LD, service-area/location links,
       conversion elements (tel:, forms, booking/CTA buttons). Score + fix hints.
4. [x] Typed extension.yaml schema (pydantic) replaces `extension.validate`.
5. [x] `tabmill lint <slug> [--release]`: rules from `skills/chrome-store-policy/reference.md`
       that are mechanical now (perm-justification, perm-broad-host, names/lengths,
       mv3-no-eval/remote-script on the built bundle, cta-placeholder, fill-placeholder,
       portfolio-similarity heuristic) with dev vs release severity.
6. [x] `tabmill dev|test|zip <slug>` wrapping `make in-docker-*`.
7. [x] `docs/creating-an-extension.md`; NOTES time-to-first-build for #2.

- [x] `recipes/local-seo-checker/extension.yaml` with placeholder `cta_url` (D-015)
- [x] `cta-placeholder` rule (warn; error under `--release`) + per-rule release severity (`cli/tabmill/lint.py`)
