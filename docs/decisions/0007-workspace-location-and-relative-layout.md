---
ID: ADR-0007
Title: workspace-location-and-relative-layout
Status: Accepted
Date: 2026-10-03
Supersedes: ADR-0006
---

## Context

ADR-0006 linked `@tabmill/*` packages through a pnpm workspace assuming the workspace sat
**beside** tabmill (`../tabmill/packages/*`). The operator then placed all Chrome extensions in
the existing repo `~/work/projects/plugins/chrome-extension-projects` (which also holds five
pre-tabmill extensions at its top level), named via a centrally set env var.

## Decision

- WORKSPACE_DIR = `$TABMILL_WORKSPACE`, exported once in `~/.profile` (read at login, so every
  shell, IDE, and tool inherits it) = `~/work/projects/plugins/chrome-extension-projects`.
  `tabmill.config.json` no longer names a workspace (it may, as a fallback; env wins).
- Linking mechanism from ADR-0006 is unchanged (pnpm workspace, `workspace:*`), but every
  cross-repo path is **computed by `tabmill init`** instead of assumed: pnpm-workspace.yaml gets
  `<relpath workspace→tabmill>/packages/*` (today `../../droyfun/tabmill/packages/*`);
  `Makefile.local` mounts the common parent of workspace, tabmill, and builder
  (today `~/work/projects`) into the container; CI checks both repos out at the same relative
  paths (`plugins/chrome-extension-projects`, `droyfun/tabmill`) using `TABMILL_PAT`.
- tabmill only adds files to the workspace repo; pre-existing top-level projects are untouched.

## Consequences

**Good:** extensions live with the operator's other Chrome work; one env var to move them.
**Bad:** the relative layout is still load-bearing — moving either repo means re-running
`tabmill init` (paths regenerate only into files that don't exist yet; delete the generated
`pnpm-workspace.yaml`, `Makefile.local`, CI workflow first). The container mount is broad
(all of `~/work/projects`).

## Alternatives considered

- **Keep `../tabmill-extensions`** — rejected by the operator.
- **Absolute paths in pnpm-workspace.yaml** — break in CI. Rejected.
