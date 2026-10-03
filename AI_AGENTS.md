# AI Agent Context — tabmill

## What this project is
CLI + templates + shared packages + Claude Code skills that create, release, and track a
portfolio of narrowly scoped Chrome MV3 extensions for Lamill, each linked to an SEO landing
page on a portfolio site. Spec: `docs/prd.md`; rules: `CLAUDE.md`.

## Stack
- **CLI:** Python ≥ 3.11 + uv (typer, rich, httpx, pydantic) — ADR-0002.
- **Extensions:** TypeScript built with Node ≥ 22 + pnpm **only inside the builder docker** —
  never on the host (ADR-0003). WXT (ADR-0004), builder adapted via `Makefile.local` (ADR-0005); Vitest, Playwright (bundled Chromium), ESLint 9, Prettier.

## Project structure
Target layout (directories appear as phases need them):
- `cli/` — `tabmill` commands
- `packages/` — `@tabmill/*` shared code (brand, funnel, messaging, analytics, policy), extracted only when two extensions need it
- `templates/` — popup | side-panel | devtools | context-menu | maps-overlay
- `skills/` — workspace skill sources (installed by `tabmill init` / `skills sync`)
- `ci/` — GitHub Actions templates for the workspace
- `.claude/skills/tabmill-dev/` — tool-repo-only skill
- `docs/` — Lamill-standard docs; `docs/kickoff.md` is the original brief

## Versioning convention

This project uses **strict two-level `vN.X` versioning** for tiers and phases:

- Tier: `v1`, `v2`, … — a coherent body of work.
- Phase: `v1.A`, `v1.B`, … — a shippable sub-unit. **`vN.A` is always planning / decisions lock**; build work starts at `.B`.

Never three-level (`v1.A.1`). Commit messages and doc references use `vN.X` only.
Canonical statement: `~/work/projects/sites/portfolio/AI_AGENTS.md` § Versioning.

## Building info
Nothing to build yet (v1.A). Planned: `uv sync`, `uv run pytest`, `uv run ruff check`,
`uv run mypy` in TOOL_DIR; extensions build from WORKSPACE_DIR via `uv run tabmill build <slug>`,
which calls the builder Makefile (docker).

## Distribution / deployment info

- **Type**: CLI tool (+ workspace of Chrome extensions)
- **Target**: local install; extensions → Chrome Web Store (manual publish approval)
- **Live URL / install command**: not yet
- **Last released version / deployed commit**: none
- **Release / deploy trigger**: manual; workspace CI builds release zips on tag (v1.D)
- **Notes**: CWS credentials in `TOOL_DIR/.env` (never committed) — see `skills/tabmill-release/reference.md`

## How to run
Not runnable yet.

## Key conventions
- TOOL_DIR / WORKSPACE_DIR boundary is absolute (`CLAUDE.md` § Rules).
- Extract, don't design upfront.
- `✓ ↷ ✗` step markers in CLI output.

## Out of scope / don't touch
- Never edit installed skill copies in the workspace.
- Never edit portfolio site repos except via the `tabmill-landing-page` flow.
