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
uv run tabmill new <slug>           # first run: starter recipe; after filling it: generate
uv run tabmill try <slug> [--url URL] [--dev]  # build + Chromium in docker, window on your desktop
uv run tabmill check [slug]         # typecheck + unit + smoke + store-policy lint (no slug = all)
uv run tabmill ship <slug>          # assets, listing, tool page, release lint, zip, upload folder, hub
uv run tabmill ship <slug> --publish  # …then upload + submit for review (attended only)
uv run tabmill status [slug] [--refresh]  # where each extension stands + the next command
```

Setup lives under `settings`; the single steps the commands above run live under `advanced`:

```
uv run tabmill settings init | skills sync | preflight | apikeys list|set|delete
uv run tabmill advanced create|build|dev|test|lint|zip|assets|listing|landing|release|publish|hub|list
```
Anywhere: `uv tool install --editable ~/work/projects/droyfun/tabmill`, then `tabmill …`.

Planned: analytics.

## Docs

`PLAN.md` phases · `TODO.md` queue · `DECISIONS.md` decisions + dependency register ·
`NOTES.md` findings + time-to-first-build · `CLAUDE.md` rules · `docs/` Lamill-standard docs.
