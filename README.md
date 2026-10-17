# tabmill

CLI + templates + Claude Code skills for building, releasing, and tracking Lamill's
portfolio of single-purpose Chrome (Manifest V3) extensions, each paired with an SEO landing
page on a Lamill portfolio site.

**Status:** see `docs/prd.md` § 5 for phases and open questions.

## Two directories

- **tabmill** (this repo): CLI, shared packages, templates, CI templates, skill sources.
- **workspace** (`$TABMILL_WORKSPACE` = `~/work/projects/plugins/chrome-extension-projects`, separate repo): `extensions/<slug>/extension.yaml` + source,
  `registry.json`, build output. Its location comes from `tabmill.config.json` or `TABMILL_WORKSPACE`.

## Build

`make deps | test | lint | fmt | check | build | run ARGS="init"` — builder Makefile + `Makefile.local`.

## Commands

```
uv run tabmill new "<rough idea>" [--non-interactive]  # idea stage: clarify → shape → evidence → check
uv run tabmill new --brief <file> | new - | new --paste  # a Tabmill brief: gap-only questions
uv run tabmill brief check <file>                      # validate a brief (line + section)
uv run tabmill evidence add <id> <file> | new --evidence <file>  # Demand / Store competition tables
uv run tabmill new validate|trends <keyword>…          # lamill demand research, printed only
uv run tabmill new --resume <id> | new clarify|shape [id]  # continue / re-run a stage
uv run tabmill bootstrap <slug>     # first run: starter recipe; after filling it: generate
uv run tabmill try <slug> [--url URL] [--dev]  # build + Chromium in docker, window on your desktop
uv run tabmill check [slug]         # typecheck + unit + smoke + store-policy lint (no slug = all)
uv run tabmill ship <slug>          # assets, listing, tool page, release lint, zip, upload folder, hub
uv run tabmill publish <slug>       # upload + submit for review (attended only; ship never uploads)
uv run tabmill status [slug] [--refresh]  # lifecycle stage + the next command
uv run tabmill slots | templates | doctor [--fix]  # store slots · surface templates · full check
```

v2 (D-040, `docs/prd.md` § v2) puts an idea stage in front: `tabmill new "<rough idea>"` or a
pasted Tabmill brief → clarify → shape → evidence → check → verdict → `approve`. Built so far: clarify (v2.B), brief input (v2.C), shape + rules check (v2.D), evidence (v2.E);
sessions in `ideas/<id>/`. Uses `claude -p` (no tools; `ai_model` in `tabmill.config.json`).
`tabmill new <slug>` still works through v2 as a deprecated alias for `bootstrap`.

Setup lives under `settings`; the single steps the commands above run live under `advanced`:

```
uv run tabmill settings init | skills sync | preflight | apikeys list|set|delete
uv run tabmill advanced create|build|dev|test|lint|zip|assets|listing|landing|release|hub|list
```
Anywhere: `uv tool install --editable ~/work/projects/droyfun/tabmill`, then `tabmill …`.

Planned: analytics.

## Docs

`PLAN.md` phases · `TODO.md` queue · `DECISIONS.md` decisions + dependency register ·
`NOTES.md` findings + time-to-first-build · `CLAUDE.md` rules · `docs/` Lamill-standard docs.
