---
name: tabmill-dev
description: Conventions for working on Tabmill itself (the tool repo) — where code goes (CLI, packages, templates, CI templates, skill sources), the TOOL_DIR/WORKSPACE_DIR boundary, extract-don't-design, dependency justification, skill authoring and syncing, versioning, and doc updates. Use whenever changing anything in the tabmill repo — adding or changing a CLI command, package, template, CI template, or skill source — or when deciding whether something belongs in Tabmill or in an extension.
---

# Working on Tabmill (tool repo)

Not installed into the workspace. Rules are canonical in the repo-root `CLAUDE.md`; this
skill is the how-to around them.

## Where does it go?

| Thing | Location |
|---|---|
| `tabmill` command | `cli/` — top level stays the lifecycle (`new try check ship status`); a new single step goes under `advanced`, setup under `settings` (D-038) |
| code used by ≥ 2 extensions | `packages/<name>/` (`@tabmill/<name>`) |
| per-surface starter code | `templates/<popup\|side-panel\|devtools\|context-menu\|maps-overlay>/` |
| GitHub Actions for the workspace | `ci/` (installed by `tabmill settings init`) |
| workspace skills | `skills/<name>/SKILL.md` (+ reference files) |
| an extension (extension.yaml + feature code) | `recipes/<slug>/` (ADR-0008) |
| generic surface code | `templates/extension/<template>/` |
| generated extensions, registry.json, builds | WORKSPACE_DIR — tabmill output only, never hand-edited |

Used by only one extension? It stays in that recipe. Extract when the second needs
it — and say which two in the commit/PLAN entry.

## Before changing code

1. Is it in the current phase (`docs/prd.md` § 5)? If it's a new feature not in the
   PRD, stop and ask the operator where it slots.
2. Over ~20 lines? Add a planned item to the work queue in `docs/prd.md` first.
3. New dependency? Add a row to `DECISIONS.md` § Dependency register *before* installing:
   runtime vs dev, why a platform API won't do, size/maintenance.
   `@tabmill/*` packages ship in extension bundles → **zero third-party runtime deps** by default.

## Code rules

- CLI: Python + uv (ADR-0002). `uv run` for everything; typer/rich/httpx; typed (mypy strict).
- **Never install or call Node on the host** (ADR-0003). Node work = `make <target>` in the
  workspace → builder docker.
- Browser packages/templates: TypeScript `strict`, no `any` without a comment; TS source consumed
  through the cross-repo pnpm workspace (D-006, proposed), built only in docker.
- Nothing in a package may fetch or load remote code; no `eval`/`new Function`.
- Never hardcode WORKSPACE_DIR: resolve `tabmill.config.json`, then `TABMILL_WORKSPACE`, else
  fail with a message naming both.
- CLI output: one line per step, `✓` done/already-correct, `↷` skipped/warn/dry-run (yellow,
  retryable), `✗` error needing operator action (red). Steps are idempotent: probe, then act.
- Publishing code paths require an explicit interactive confirmation; never run in CI.

## Skills

- Sources only in `skills/`; installed copies in the workspace are never edited.
- Frontmatter at line 1: `name`, `description` (exact trigger conditions; ≤ 1,536 chars).
- ≤ ~150 lines; long reference material in a sibling file, linked relatively.
- Facts must be verified against official docs with a date; mark the rest UNVERIFIED.
- After changing a skill or anything in `templates/workspace/managed/` or `ci/`: `make run
  ARGS="settings skills sync"`, and note the gap that prompted it. Seed templates only affect new workspaces.

## Tests

CLI: `uv run pytest` (+ `ruff`, `mypy`). Browser packages: Vitest via the builder. Playwright smoke tests use bundled Chromium
(`channel: 'chromium'`). Report "suite green" separately from "works in real Chrome".

## Docs to update in the same change

Phase status → `docs/prd.md`; scope/done + work queue → `docs/prd.md`; mechanisms/schemas → `docs/architecture.md`;
decisions/deps → `DECISIONS.md` (+ ADR if load-bearing and accepted); findings/blockers/timings
→ `NOTES.md`; prompts → `docs/Prompts.md` (dated H2).

## Versioning and git

`vN.X` only. Commit subjects start with the phase (`v1.B: tabmill init`). Commit only when the
operator asks. Never commit `.env`.
