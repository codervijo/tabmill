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

```
uv run tabmill list                 # every extension: status, version, what still needs filling
uv run tabmill create <slug>        # starter recipe in recipes/<slug>/extension.yaml
uv run tabmill new <slug>           # generate it into the workspace
uv run tabmill build <slug>         # regenerate + WXT build in docker
uv run tabmill skills sync          # refresh all tabmill-managed workspace files
```
Anywhere: `uv tool install --editable ~/work/projects/droyfun/tabmill`, then `tabmill …`.


Shipped: `init` · `skills sync` · `create` · `new` · `build` (minimal) · `list`. Planned:

`dev` · `test` · `zip` · `lint` · `assets` ·
`listing` · `landing` · `publish` (attended only) · `status`

## Docs

`PLAN.md` phases · `TODO.md` queue · `DECISIONS.md` decisions + dependency register ·
`NOTES.md` findings + time-to-first-build · `CLAUDE.md` rules · `docs/` Lamill-standard docs.
