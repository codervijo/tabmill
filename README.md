# tabmill

CLI + templates + Claude Code skills for building, releasing, and tracking Lamill's
portfolio of single-purpose Chrome (Manifest V3) extensions, each paired with an SEO landing
page on a Lamill portfolio site.

**Status:** v1.B — generator works (`new` + `build` → loadable extension, smoke-tested). See `docs/prd.md` for phases and open questions.

## Two directories

- **tabmill** (this repo): CLI, shared packages, templates, CI templates, skill sources.
- **workspace** (`$TABMILL_WORKSPACE` = `~/work/projects/plugins/chrome-extension-projects`, separate repo): `extensions/<slug>/extension.yaml` + source,
  `registry.json`, build output. Its location comes from `tabmill.config.json` or `TABMILL_WORKSPACE`.

## Build

`make deps | test | lint | fmt | check | build | run ARGS="init"` — builder Makefile + `Makefile.local`.

## Commands

Shipped: `init` · `skills sync` · `new` · `build` (minimal). Planned:

`dev` · `test` · `zip` · `lint` · `assets` ·
`listing` · `landing` · `publish` (attended only) · `status`

## Docs

`PLAN.md` phases · `TODO.md` queue · `DECISIONS.md` decisions + dependency register ·
`NOTES.md` findings + time-to-first-build · `CLAUDE.md` rules · `docs/` Lamill-standard docs.
