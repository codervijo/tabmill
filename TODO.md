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
- [ ] HUMAN: set real Rankmill CTA URL (placeholder `https://rankmill.example/local-seo-audit`; release lint blocks until replaced)
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
7. [ ] HUMAN: validate on the 10 approved URLs in real Chrome (load `.output/chrome-mv3` unpacked);
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

## v1.E — queued (extension #2)

- [ ] `recipes/local-seo-checker/extension.yaml`: `cta_url: https://rankmill.example/local-seo-audit`
      (placeholder, D-015); the HUMAN line below stays here (tabmill repo)
- [ ] `packages/policy` rule `cta-placeholder` (warn; error under `--release`) + per-rule release severity
