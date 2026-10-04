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
uv run tabmill test <slug>          # typecheck + unit + smoke (docker)
uv run tabmill try <slug> [--url URL] [--dev]  # Chromium in docker, window on your desktop
uv run tabmill dev <slug>           # hot reload; load .output/chrome-mv3-dev in Chrome
uv run tabmill assets <slug>        # store icon, promo tile, screenshots (docker)
uv run tabmill listing <slug>       # store listing draft (.output/store/listing.md)
uv run tabmill publish <slug> [--staged|--check]  # attended only
uv run tabmill lint <slug> [--release]
uv run tabmill zip <slug> [--release]
uv run tabmill skills sync          # refresh all tabmill-managed workspace files
uv run tabmill preflight            # workspace, builder, docker, X11, credentials
uv run tabmill settings apikeys list|set|delete   # store credentials in tabmill.env
```
Anywhere: `uv tool install --editable ~/work/projects/droyfun/tabmill`, then `tabmill …`.


Shipped: `init` · `skills sync` · `create` · `new` · `build` · `list` · `test` · `try` · `dev` · `lint` · `zip` · `assets` · `listing` · `publish` · `preflight` · `settings apikeys`. Planned:

`landing` · `status`

## Docs

`PLAN.md` phases · `TODO.md` queue · `DECISIONS.md` decisions + dependency register ·
`NOTES.md` findings + time-to-first-build · `CLAUDE.md` rules · `docs/` Lamill-standard docs.
